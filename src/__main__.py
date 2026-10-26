"""Seven RPG - main entry point."""

from __future__ import annotations

import sys


def main() -> int:
    """Launch the Seven RPG package."""
    from seven_rpg import __version__

    print(f"Seven RPG v{__version__}")
    print("A Python-based RPG framework.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
