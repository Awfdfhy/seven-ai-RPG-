#!/usr/bin/env python
"""
QA automation runner for Seven RPG.

Usage:
    python run_qa.py              # Full suite with coverage
    python run_qa.py --fast       # Skip slow / integration tests
    python run_qa.py --no-cov     # Run without coverage
    python run_qa.py --data       # Data integrity only
    python run_qa.py --unit       # Unit tests only
    python run_qa.py --integration # Integration tests only
"""

from __future__ import annotations

import subprocess
import sys
import os

PYTHON = sys.executable
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(REPO_ROOT, "tests")


def run(cmd: list[str]) -> int:
    print(f"\n{'='*60}")
    print(f"$ {' '.join(cmd)}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


def main() -> int:
    args = sys.argv[1:]

    if "--data" in args:
        cmd = [
            PYTHON, "-m", "pytest", TEST_DIR,
            "-v", "--tb=short", "-m", "data",
        ]
        if "--no-cov" not in args:
            cmd += ["--cov=src", "--cov-report=term-missing"]
        return run(cmd)

    if "--unit" in args:
        cmd = [
            PYTHON, "-m", "pytest", TEST_DIR,
            "-v", "--tb=short", "-m", "not integration and not slow",
        ]
        if "--no-cov" not in args:
            cmd += ["--cov=src", "--cov-report=term-missing"]
        return run(cmd)

    if "--integration" in args:
        cmd = [
            PYTHON, "-m", "pytest", TEST_DIR,
            "-v", "--tb=short", "-m", "integration",
        ]
        return run(cmd)

    # Full suite (default)
    cmd = [
        PYTHON, "-m", "pytest", TEST_DIR,
        "-v", "--tb=short",
    ]
    if "--fast" in args:
        cmd += ["-m", "not slow and not integration"]
    if "--no-cov" not in args:
        cmd += ["--cov=src", "--cov-report=term-missing", "--cov-report=html"]
    return run(cmd)


if __name__ == "__main__":
    sys.exit(main())
