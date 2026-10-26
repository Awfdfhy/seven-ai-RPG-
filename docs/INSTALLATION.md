# Installation Guide

## System Requirements

- **Python:** 3.14 or newer (3.15 also supported)
- **Operating System:** Windows, macOS, or Linux
- **Memory:** 512 MB minimum (depends on world size and active systems)
- **Network:** Required for multiplayer rooms, cloud sync, and community features

No C/C++ compiler or external runtime dependencies are needed. All required libraries are pure Python.

---

## Quick Install (End Users)

The fastest way to get Seven RPG:

```bash
git clone https://github.com/seven-rpg/seven-rpg.git
cd seven-rpg
pip install -e .
```

The runtime dependency `websockets` is installed automatically.

### Verify Installation

```bash
python -c "import seven_rpg; print(seven_rpg.__version__)"
```

Expected output:

```
0.1.0
```

---

## Developer / Contributor Setup

To run tests, linters, and type checks:

```bash
# Clone the repository
git clone https://github.com/seven-rpg/seven-rpg.git
cd seven-rpg

# Install with development extras
pip install -e ".[dev]"

# Verify everything works
python run_qa.py --fast
```

### What `.[dev]` Installs

| Package | Purpose |
|---------|---------|
| `pytest` | Test runner |
| `pytest-cov` | Coverage reporting |
| `coverage` | Coverage measurement |
| `ruff` | Linting and import sorting |
| `mypy` | Static type checking |
| `pre-commit` | Git hook automation |

### Make Targets

```bash
make help         # Show all available targets
make test         # Run unit tests
make lint         # Run ruff
make type         # Run mypy
make coverage     # Run tests with HTML coverage report
make qa-fast      # Fast QA (skip slow / integration)
make qa-full      # Full QA suite with coverage
make clean        # Remove cache / coverage artifacts
make install      # Install dev dependencies
make pre-commit   # Install pre-commit hooks
```

### Tox (Multi-Environment Testing)

```bash
# Run tests on Python 3.14 and 3.15
tox

# Run lint only
tox -e lint

# Run type checks only
tox -e type

# Run coverage only
tox -e coverage
```

### Running Tests Directly

```bash
# Full suite
python -m pytest tests/ -v --tb=short

# Single test file
python tests/test_abilities.py

# Skip slow/integration tests
python -m pytest tests/ -m "not slow and not integration"

# Data-integrity checks only
python run_qa.py --data
```

---

## Platform-Specific Notes

### Windows

- Use `python` (not `python3`) in Command Prompt / PowerShell.
- The `make` commands above require Git Bash, MSYS2, or WSL. Alternatively, use the equivalent `python run_qa.py` commands.

### macOS / Linux

- Use `python3` and `pip3` if your system Python points to 2.x.
- Ensure `python3.14` or `python3.15` is available via `pyenv`, `brew`, or your package manager.

---

## Offline / No-Install Mode

Seven RPG runs on the standard library only for core gameplay. If you have the source tree:

```bash
# No pip install needed for basic usage
python src/__main__.py
```

Individual modules can be imported directly by adding `src/` to `PYTHONPATH`:

```bash
PYTHONPATH=src python -c "from ability import Ability; print('OK')"
```

---

## Troubleshooting

### `ImportError` when importing `seven_rpg`

- Confirm the package is installed in editable mode: `pip show seven-rpg`
- If using `PYTHONPATH`, point it at the `src/` directory, not the repo root.

### `websockets` not found

```bash
pip install websockets
# or
pip install -e .
```

### `pytest` not found

```bash
pip install pytest
# or install the dev extras
pip install -e ".[dev]"
```

### Tests fail with `ModuleNotFoundError`

Tests prepend `src/` to `sys.path` automatically. If running outside the repo, set:

```bash
export PYTHONPATH=/path/to/seven-rpg/src
```

### Permission errors on Windows

Run Command Prompt or PowerShell as Administrator, or use the `--user` flag:

```bash
pip install --user -e ".[dev]"
```

---

## Upgrading

```bash
git pull
pip install --upgrade -e ".[dev]"
```
