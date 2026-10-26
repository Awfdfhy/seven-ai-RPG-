"""
RPG-11-03: Cross-platform compatibility utilities.

Provides helpers for:
- OS detection
- Windows ANSI escape code handling (via colorama when available)
- Cross-platform path resolution relative to the package
- Home directory expansion
"""

from __future__ import annotations

import os
import platform
import re
import sys

# ---------------------------------------------------------------------------
# OS detection
# ---------------------------------------------------------------------------

def is_windows() -> bool:
    """Return True if running on Windows."""
    return sys.platform.startswith("win") or platform.system() == "Windows"

def is_mac() -> bool:
    """Return True if running on macOS."""
    return sys.platform == "darwin" or platform.system() == "Darwin"

def is_linux() -> bool:
    """Return True if running on Linux."""
    return sys.platform.startswith("linux") or platform.system() == "Linux"

# ---------------------------------------------------------------------------
# ANSI handling
# ---------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[^[]*")

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from a string."""
    return _ANSI_RE.sub("", text)

def enable_ansi() -> None:
    """
    Enable ANSI escape code processing on Windows if possible.

    Uses colorama when available; falls back to ctypes/VT100 on Win 10+.
    No-op on non-Windows platforms.
    """
    if not is_windows():
        return

    try:
        import colorama  # type: ignore
        if not getattr(enable_ansi, "_initialized", False):
            colorama.init()
            enable_ansi._initialized = True  # type: ignore
        return
    except ImportError:
        pass

    # Fallback: try enabling VT100 mode on Windows 10+
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        ENABLE_VT100 = 0x0004
        hOut = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(hOut, ctypes.byref(mode)):
            kernel32.SetConsoleMode(hOut, mode.value | ENABLE_VT100)
    except Exception:
        pass


def colorize(text: str, ansi_code: str, fallback: str | None = None) -> str:
    """
    Wrap `text` in `ansi_code` + reset, but only if ANSI is supported.

    On Windows without ANSI support, returns `fallback` (defaults to plain text).
    """
    reset = "\033[0m"
    if is_windows() and not _windows_ansi_supported():
        return fallback if fallback is not None else text
    return f"{ansi_code}{text}{reset}"


def _windows_ansi_supported() -> bool:
    """Return True if the Windows console supports ANSI codes."""
    if not is_windows():
        return True

    # If colorama initialized successfully, it's supported
    if getattr(enable_ansi, "_initialized", False):
        return True

    # Check if running in a known ANSI-capable terminal
    term = os.environ.get("TERM_PROGRAM", "").lower()
    if term in ("vscode", "windows terminal"):
        return True

    # Check ConEmu / ANSICON
    if os.environ.get("ConEmuANSI") == "ON" or os.environ.get("ANSICON") is not None:
        return True

    return False


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_data_path(caller_file: str, *parts: str) -> str:
    """
    Resolve a path relative to the package's ``data/`` directory.

    Example::

        resolve_data_path(__file__, "abilities.json")
        # -> /path/to/project/src/../data/abilities.json

    The caller_file should be ``__file__`` from the calling module.
    """
    src_dir = os.path.dirname(os.path.abspath(caller_file))
    base = os.path.join(src_dir, "..", "data")
    return os.path.normpath(os.path.join(base, *parts))


def get_home_dir() -> str:
    """
    Return the current user's home directory in a cross-platform way.

    Falls back to ``os.path.expanduser("~")`` which works on Windows, macOS,
    and Linux.
    """
    return os.path.expanduser("~")


def ensure_dir(path: str) -> None:
    """Create directory ``path`` (and parents) if it does not exist."""
    os.makedirs(path, exist_ok=True)
