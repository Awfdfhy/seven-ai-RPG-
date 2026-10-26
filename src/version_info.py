"""Seven RPG — version information and build metadata."""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VersionInfo:
    """Centralized version metadata for Seven RPG."""

    version: str = "0.1.0"
    codename: str = "First Light"
    release_date: str = "2026-10-26"
    description: str = "Early-access pre-release build"
    author: str = "Seven RPG Team"
    license: str = "MIT"
    python_requires: str = ">=3.14"

    # Populated at runtime when available
    build_timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat(timespec="seconds")
    )
    git_commit: Optional[str] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.git_commit is None:
            self.git_commit = self._detect_git_commit()

    @staticmethod
    def _detect_git_commit() -> Optional[str]:
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "codename": self.codename,
            "release_date": self.release_date,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "python_requires": self.python_requires,
            "build_timestamp": self.build_timestamp,
            "git_commit": self.git_commit,
        }

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), indent=2, **kwargs)

    def __str__(self) -> str:
        base = f"Seven RPG v{self.version} ({self.codename})"
        if self.git_commit:
            return f"{base} [{self.git_commit}]"
        return base


# Canonical version info object
info = VersionInfo()


def get_version() -> str:
    """Return the current version string."""
    return info.version


def get_version_info() -> VersionInfo:
    """Return the VersionInfo dataclass instance."""
    return info


def print_version() -> None:
    """Print version info to stdout."""
    print(info)
