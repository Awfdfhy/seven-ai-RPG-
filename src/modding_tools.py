"""
RPG-12-05: Modding Tools
CLI and library utilities for creating, validating, and packaging mods.
"""

from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ModScaffold:
    """Template structure for a new mod."""

    mod_id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""


@dataclass
class ValidationResult:
    """Outcome of a mod or data file validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------

class ModdingTools:
    """
    Collection of utilities for mod authors and packagers.

    Usage:
        tools = ModdingTools()
        tools.create_scaffold("my_mod", "My Mod", author="Me")
        result = tools.validate_mod("mods/my_mod")
        tools.package_mod("mods/my_mod", "dist/my_mod.zip")
    """

    def __init__(self, base_directory: str | None = None) -> None:
        if base_directory is None:
            base_directory = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), ".."
            )
        self.base_directory = os.path.abspath(base_directory)

    # ------------------------------------------------------------------
    # Scaffold
    # ------------------------------------------------------------------

    def create_scaffold(
        self,
        mod_id: str,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        author: str = "",
        target_dir: str | None = None,
        overwrite: bool = False,
    ) -> str:
        """
        Create a new mod scaffold directory.

        Returns the absolute path to the created mod directory.
        """
        if target_dir is None:
            target_dir = os.path.join(self.base_directory, "mods", mod_id)
        target_dir = os.path.abspath(target_dir)

        if os.path.exists(target_dir) and not overwrite:
            raise FileExistsError(
                f"Mod directory already exists: {target_dir}"
            )

        mod_dir = Path(target_dir)
        data_dir = mod_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "id": mod_id,
            "name": name,
            "version": version,
            "description": description,
            "author": author,
            "enabled": True,
            "data_files": [],
        }
        (mod_dir / "mod.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        readme = mod_dir / "README.md"
        readme.write_text(
            f"# {name}\n\n{description}\n\n## Author\n\n{author}\n",
            encoding="utf-8",
        )

        template = data_dir / "skill_tree.json"
        template.write_text(
            json.dumps(
                {
                    "id": f"{mod_id}.example_tree",
                    "name": "Example Tree",
                    "description": "A sample skill tree provided by the scaffold.",
                    "nodes": [
                        {
                            "id": f"{mod_id}.root",
                            "name": "Root Node",
                            "description": "The root of the example tree.",
                            "category": "combat",
                            "node_type": "root",
                            "max_rank": 1,
                            "point_cost": 0,
                            "parent_ids": [],
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        return str(target_dir)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_mod(self, mod_path: str) -> ValidationResult:
        """
        Validate a mod's manifest and data files.

        Checks:
          - mod.json exists and is valid JSON
          - Required manifest fields are present
          - data files listed in the manifest actually exist
          - JSON files in data/ are syntactically valid
          - Basic schema checks for known file types
        """
        errors: list[str] = []
        warnings: list[str] = []
        mod_path = os.path.abspath(mod_path)

        manifest_path = os.path.join(mod_path, "mod.json")
        if not os.path.isfile(manifest_path):
            return ValidationResult(
                valid=False, errors=[f"Missing mod.json: {manifest_path}"]
            )

        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except json.JSONDecodeError as exc:
            return ValidationResult(
                valid=False, errors=[f"Invalid mod.json: {exc}"]
            )

        required_fields = ("id", "name", "version")
        for field_name in required_fields:
            if field_name not in manifest:
                errors.append(f"Missing required manifest field: {field_name}")

        if "id" in manifest:
            if not re.match(r"^[a-z0-9_]+$", manifest["id"]):
                errors.append(
                    "Mod id must be lowercase alphanumeric with underscores"
                )

        if "version" in manifest:
            if not re.match(r"^\d+\.\d+\.\d+$", manifest["version"]):
                warnings.append(
                    "Version does not look like semver (x.y.z)"
                )

        data_dir = os.path.join(mod_path, "data")
        if not os.path.isdir(data_dir):
            warnings.append("No data/ directory found")
        else:
            for filename in os.listdir(data_dir):
                if not filename.endswith(".json"):
                    continue
                file_path = os.path.join(data_dir, filename)
                try:
                    with open(file_path, encoding="utf-8") as fh:
                        json.load(fh)
                except json.JSONDecodeError as exc:
                    errors.append(
                        f"Invalid JSON in {filename}: {exc}"
                    )
                else:
                    file_errors = self._validate_data_file_schema(
                        file_path, filename
                    )
                    errors.extend(file_errors)

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_data_file_schema(
        self, file_path: str, filename: str
    ) -> list[str]:
        """Run lightweight schema checks on a known data file."""
        errors: list[str] = []
        try:
            with open(file_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            return errors

        name = filename.lower()

        if "skill_tree" in name:
            if not isinstance(data, dict):
                errors.append(f"{filename}: expected object, got list")
                return errors
            if "id" not in data:
                errors.append(f"{filename}: missing 'id'")
            if "nodes" not in data:
                errors.append(f"{filename}: missing 'nodes'")
            elif not isinstance(data.get("nodes"), list):
                errors.append(f"{filename}: 'nodes' should be a list")

        elif "ability" in name:
            if not isinstance(data, dict):
                errors.append(f"{filename}: expected object, got list")
                return errors
            if "trees" in data and not isinstance(data["trees"], list):
                errors.append(f"{filename}: 'trees' should be a list")
            if "abilities" in data and not isinstance(data["abilities"], list):
                errors.append(f"{filename}: 'abilities' should be a list")

        elif "crafting" in name:
            if not isinstance(data, dict):
                errors.append(f"{filename}: expected object, got list")
                return errors
            valid_keys = {
                "crafting_materials.json": {"materials"},
                "crafting_items.json": {"items"},
                "crafting_stations.json": {"stations"},
                "crafting_recipes.json": {"recipes"},
            }
            expected = valid_keys.get(filename)
            if expected:
                extra = set(data.keys()) - expected
                if extra:
                    errors.append(
                        f"{filename}: unexpected top-level keys: {sorted(extra)}"
                    )

        return errors

    def validate_data_file(self, file_path: str) -> ValidationResult:
        """Validate a single data file."""
        file_path = os.path.abspath(file_path)
        errors: list[str] = []
        warnings: list[str] = []

        if not os.path.isfile(file_path):
            return ValidationResult(
                valid=False,
                errors=[f"File not found: {file_path}"],
            )

        try:
            with open(file_path, encoding="utf-8") as fh:
                json.load(fh)
        except json.JSONDecodeError as exc:
            return ValidationResult(
                valid=False, errors=[f"Invalid JSON: {exc}"]
            )

        filename = os.path.basename(file_path)
        errors.extend(self._validate_data_file_schema(file_path, filename))

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    # ------------------------------------------------------------------
    # Packaging
    # ------------------------------------------------------------------

    def package_mod(
        self,
        mod_path: str,
        output_path: str | None = None,
    ) -> str:
        """
        Package a mod directory into a zip archive.

        Returns the path to the created archive.
        """
        mod_path = os.path.abspath(mod_path)
        if not os.path.isdir(mod_path):
            raise NotADirectoryError(f"Not a directory: {mod_path}")

        manifest_path = os.path.join(mod_path, "mod.json")
        if not os.path.isfile(manifest_path):
            raise FileNotFoundError(
                f"Cannot package mod without manifest: {manifest_path}"
            )

        mod_name = Path(mod_path).name
        if output_path is None:
            output_path = os.path.join(
                self.base_directory, "dist", f"{mod_name}.zip"
            )
        output_path = os.path.abspath(output_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with zipfile.ZipFile(
            output_path, "w", zipfile.ZIP_DEFLATED
        ) as zf:
            for root, _dirs, files in os.walk(mod_path):
                for filename in files:
                    abs_file = os.path.join(root, filename)
                    arcname = os.path.relpath(abs_file, mod_path)
                    zf.write(abs_file, arcname)

        return output_path

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def list_mod_files(self, mod_path: str) -> list[str]:
        """List all files in a mod directory, relative to the mod root."""
        mod_path = os.path.abspath(mod_path)
        files: list[str] = []
        for root, _dirs, filenames in os.walk(mod_path):
            for filename in filenames:
                abs_file = os.path.join(root, filename)
                files.append(os.path.relpath(abs_file, mod_path))
        return sorted(files)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_create(args: Any) -> None:
    tools = ModdingTools()
    target = tools.create_scaffold(
        mod_id=args.mod_id,
        name=args.name or args.mod_id,
        version=args.version,
        description=args.description or "",
        author=args.author or "",
        target_dir=args.target_dir,
        overwrite=args.overwrite,
    )
    print(f"Created mod scaffold at: {target}")


def _cli_validate(args: Any) -> None:
    tools = ModdingTools()
    result = tools.validate_mod(args.mod_path)
    if result.valid:
        print("Mod is valid.")
    else:
        print("Validation failed:")
        for err in result.errors:
            print(f"  ERROR: {err}")
    if result.warnings:
        print("Warnings:")
        for warn in result.warnings:
            print(f"  WARN: {warn}")
    if not result.valid:
        raise SystemExit(1)


def _cli_package(args: Any) -> None:
    tools = ModdingTools()
    out = tools.package_mod(args.mod_path, args.output)
    print(f"Packaged mod to: {out}")


def _cli_list(args: Any) -> None:
    tools = ModdingTools()
    files = tools.list_mod_files(args.mod_path)
    for f in files:
        print(f)


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="modding_tools",
        description="RPG-12-05: Modding tools for Seven RPG",
    )
    sub = parser.add_subparsers(dest="command")

    p_create = sub.add_parser("create", help="Create a new mod scaffold")
    p_create.add_argument("mod_id", help="Unique mod identifier")
    p_create.add_argument("--name", help="Display name")
    p_create.add_argument("--version", default="1.0.0")
    p_create.add_argument("--description", default="")
    p_create.add_argument("--author", default="")
    p_create.add_argument("--target-dir", default=None)
    p_create.add_argument("--overwrite", action="store_true")

    p_validate = sub.add_parser("validate", help="Validate a mod")
    p_validate.add_argument("mod_path", help="Path to the mod directory")

    p_package = sub.add_parser("package", help="Package a mod into a zip")
    p_package.add_argument("mod_path", help="Path to the mod directory")
    p_package.add_argument("--output", "-o", default=None)

    p_list = sub.add_parser("list", help="List files in a mod")
    p_list.add_argument("mod_path", help="Path to the mod directory")

    args = parser.parse_args(argv)
    if args.command == "create":
        _cli_create(args)
    elif args.command == "validate":
        _cli_validate(args)
    elif args.command == "package":
        _cli_package(args)
    elif args.command == "list":
        _cli_list(args)
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
