"""
Seven RPG Test Configuration
Shared fixtures, helpers, and project-wide test setup.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

# Ensure src/ is importable without per-file sys.path hacks
_SRC = os.path.join(os.path.dirname(__file__), "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> str:
    """Absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def src_path(project_root: str) -> str:
    """Absolute path to the src directory."""
    return os.path.join(project_root, "src")


@pytest.fixture(scope="session")
def data_path(project_root: str) -> str:
    """Absolute path to the data directory."""
    return os.path.join(project_root, "data")


@pytest.fixture(scope="session")
def data_files(data_path: str) -> list[str]:
    """List of all JSON data files in data/."""
    result = []
    for name in os.listdir(data_path):
        if name.endswith(".json"):
            result.append(os.path.join(data_path, name))
    return sorted(result)


# ---------------------------------------------------------------------------
# Temp file fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_json_path(tmp_path: str):
    """Return a factory that creates temporary JSON file paths."""
    def _factory(suffix=".json") -> str:
        fd, path = tempfile.mkstemp(suffix=suffix, dir=tmp_path)
        os.close(fd)
        return path
    return _factory


# ---------------------------------------------------------------------------
# JSON data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def abilities_data(data_path: str) -> dict:
    with open(os.path.join(data_path, "abilities.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def world_map_data(data_path: str) -> dict:
    with open(os.path.join(data_path, "world_map.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def quests_data(data_path: str) -> dict:
    with open(os.path.join(data_path, "quests.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def loot_tables_data(data_path: str) -> dict:
    with open(os.path.join(data_path, "loot_tables.json"), encoding="utf-8") as f:
        return json.load(f)
