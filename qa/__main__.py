"""
Seven RPG QA Automation Suite

Usage:
    python -m qa run [--fast]        # Run full QA suite
    python -m qa lint                 # Lint only
    python -m qa type                 # Type check only
    python -m qa coverage             # Coverage report only
    python -m qa data                 # Data integrity only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable


def _run(cmd: list[str]) -> int:
    print(f"\n{'='*60}")
    print(f"$ {' '.join(cmd)}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return result.returncode


def cmd_lint(_args: argparse.Namespace) -> int:
    return _run([PYTHON, "-m", "ruff", "check", "src/", "tests/"])


def cmd_type(_args: argparse.Namespace) -> int:
    return _run([PYTHON, "-m", "mypy", "src/", "--ignore-missing-imports"])


def cmd_coverage(_args: argparse.Namespace) -> int:
    cmd = [PYTHON, "-m", "pytest", "tests/", "--cov=src",
           "--cov-report=term-missing", "--cov-report=html"]
    return _run(cmd)


def cmd_data(_args: argparse.Namespace) -> int:
    return _run([PYTHON, "run_qa.py", "--data"])


def cmd_run(args: argparse.Namespace) -> int:
    results = []
    results.append(("lint", cmd_lint(args)))
    if args.fast:
        results.append(("unit", _run([PYTHON, "run_qa.py", "--unit", "--no-cov"])))
    else:
        results.append(("unit", _run([PYTHON, "run_qa.py", "--unit", "--no-cov"])))
        results.append(("data", cmd_data(args)))
        results.append(("type", cmd_type(args)))

    print(f"\n{'='*60}")
    print("QA SUMMARY")
    print(f"{'='*60}")
    failed = []
    for name, rc in results:
        status = "PASS" if rc == 0 else "FAIL"
        print(f"  {name:20s} {status}")
        if rc != 0:
            failed.append(name)

    if failed:
        print(f"\nFAILED: {', '.join(failed)}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seven RPG QA automation")
    sub = parser.add_subparsers(dest="command", default="run")

    p_run = sub.add_parser("run", help="Run full QA suite")
    p_run.add_argument("--fast", action="store_true", help="Skip slow checks")

    sub.add_parser("lint", help="Lint source and tests")
    sub.add_parser("type", help="Type check source")
    sub.add_parser("coverage", help="Coverage report")
    sub.add_parser("data", help="Data integrity tests")

    args = parser.parse_args()
    handler = {
        "run": cmd_run,
        "lint": cmd_lint,
        "type": cmd_type,
        "coverage": cmd_coverage,
        "data": cmd_data,
    }.get(args.command)

    if not handler:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
