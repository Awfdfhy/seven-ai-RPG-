"""
RPG-09-03: Locations Directory UI

Terminal-based interactive locations directory for browsing world locations.
Supports filtering by region, type, search, and viewing full details.

Interaction:
  - Numbers/letters select a location or action.
  - 'r' filter by region.
  - 't' filter by type.
  - '/' search.
  - 'l' view location details.
  - 'q' quit.
"""

from __future__ import annotations

import os
from typing import Any

from accessibility import AccessibilityHelper
from locations import (
    LocationDirectory,
    LocationDirectoryEntry,
    load_locations_from_data_dir,
)

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_UNDERLINE = "\033[4m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

_TYPE_COLORS: dict[str, str] = {
    "town": _GREEN,
    "wilderness": _YELLOW,
    "dungeon": _RED,
    "pass": _CYAN,
    "outpost": _MAGENTA,
    "generic": _WHITE,
}

_DANGER_COLORS: dict[int, str] = {
    1: _GREEN,
    2: _GREEN,
    3: _YELLOW,
    4: _YELLOW,
    5: _RED,
    6: _RED,
    7: _RED,
    8: _MAGENTA,
    9: _MAGENTA,
    10: _MAGENTA,
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _type_color(location_type: str) -> str:
    return _TYPE_COLORS.get(location_type.lower(), _WHITE)


def _danger_color(level: int) -> str:
    return _DANGER_COLORS.get(max(1, min(10, level)), _WHITE)


def _accessible_color(text: str, role: str, accessibility: AccessibilityHelper | None) -> str:
    if accessibility is not None:
        color_map = {
            "title": "cyan",
            "header": "blue",
            "option": "white",
            "selected": "yellow",
            "accent": "magenta",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "dim": "dim",
        }
        return accessibility.color_text(text, color_map.get(role, "white"))
    return text


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _render_header(title: str, accessibility: AccessibilityHelper | None = None) -> str:
    width = 60
    border = _bold("═" * width)
    if accessibility:
        title = _accessible_color(title, "title", accessibility)
    else:
        title = _color(title, _CYAN)
    return f"{_bold('╔' + '═' * width + '╗')}\n{_bold('║')} {title:^{width - 2}} {_bold('║')}\n{border}"


def _render_footer(actions: dict[str, str], accessibility: AccessibilityHelper | None = None) -> str:
    parts = []
    for key, label in actions.items():
        if accessibility:
            parts.append(_accessible_color(f"{key}:{label}", "option", accessibility))
        else:
            parts.append(f"{_bold(key)} {label}")
    return " | ".join(parts)


def _render_location_row(
    index: int,
    loc: dict[str, Any],
    accessibility: AccessibilityHelper | None = None,
) -> str:
    marker = f"{_bold(str(index))}."
    name = loc["name"]
    loc_type = loc["location_type"]
    danger = loc["danger_level"]

    if accessibility:
        name = _accessible_color(name, "option", accessibility)
        loc_type = _accessible_color(f"[{loc_type}]", "dim", accessibility)
        danger = _accessible_color(f"D:{danger}", "warning", accessibility)
    else:
        name = _color(name, _WHITE)
        loc_type = _color(f"[{loc_type}]", _DIM)
        danger = _color(f"D:{danger}", _danger_color(danger))

    return f"  {marker} {name} {loc_type} {danger}"


def _render_location_detail(loc: dict[str, Any], accessibility: AccessibilityHelper | None = None) -> str:
    lines: list[str] = []
    lines.append(_render_header(f"LOCATION: {loc['name']}", accessibility))

    region = loc.get("region_id", "unknown")
    loc_type = loc["location_type"]
    danger = loc["danger_level"]
    desc = loc.get("description", "No description.")

    if accessibility:
        lines.append(_accessible_color(f"Region : {region}", "option", accessibility))
        lines.append(_accessible_color(f"Type   : {loc_type}", "option", accessibility))
        lines.append(_accessible_color(f"Danger : {danger}/10", "warning", accessibility))
    else:
        lines.append(f"Region : {_color(region, _BLUE)}")
        lines.append(f"Type   : {_color(loc_type, _type_color(loc_type))}")
        lines.append(f"Danger : {_color(str(danger), _danger_color(danger))}/10")

    lines.append("")
    lines.append(_dim(desc) if not accessibility else _accessible_color(desc, "dim", accessibility))

    connections = loc.get("connections", [])
    if connections:
        lines.append("")
        if accessibility:
            lines.append(_accessible_color("Connections:", "header", accessibility))
        else:
            lines.append(_bold(_color("Connections:", _BLUE)))
        for conn in connections:
            to_name = conn.get("to_name", conn.get("to", "???"))
            dist = conn.get("distance", "?")
            hours = conn.get("travel_time_hours", "?")
            lines.append(f"  -> {to_name} (dist: {dist}, {hours}h)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

class LocationDirectoryUI:
    """
    Interactive terminal UI for browsing the LocationDirectory.
    """

    def __init__(
        self,
        directory: LocationDirectory | None = None,
        accessibility: AccessibilityHelper | None = None,
        page_size: int = 20,
    ) -> None:
        self.accessibility = accessibility
        self.page_size = page_size
        self.directory = directory or load_locations_from_data_dir()
        self._current_filter_type: str | None = None
        self._current_filter_region: str | None = None
        self._search_query: str = ""
        self._selected_index: int = 0
        self._running: bool = True

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def _visible_locations(self) -> list[dict[str, Any]]:
        locs = self.directory.list_locations()

        if self._search_query:
            q = self._search_query.lower()
            locs = [l for l in locs if q in l["name"].lower() or q in l["description"].lower()]

        if self._current_filter_type:
            locs = [l for l in locs if l["location_type"] == self._current_filter_type]

        if self._current_filter_region:
            locs = [l for l in locs if l["region_id"] == self._current_filter_region]

        return locs

    def _active_filter_label(self) -> str:
        parts = []
        if self._current_filter_region:
            parts.append(f"region={self._current_filter_region}")
        if self._current_filter_type:
            parts.append(f"type={self._current_filter_type}")
        if self._search_query:
            parts.append(f"search={self._search_query!r}")
        return ", ".join(parts) if parts else "All"

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_browse_view(self, locs: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        lines.append(_render_header("LOCATIONS DIRECTORY", self.accessibility))
        lines.append("")
        lines.append(f"  Filter: {self._active_filter_label()}")
        lines.append("")

        if not locs:
            lines.append(_dim("  No locations match the current filters."))
        else:
            page = locs[self._selected_index : self._selected_index + self.page_size]
            for offset, loc in enumerate(page):
                idx = self._selected_index + offset
                lines.append(_render_location_row(idx + 1, loc, self.accessibility))

        lines.append("")
        lines.append(_render_footer({
            "↑/k": "up",
            "↓/j": "down",
            "l": "details",
            "r": "region filter",
            "t": "type filter",
            "/": "search",
            "c": "clear filters",
            "q": "quit",
        }, self.accessibility))

        return "\n".join(lines)

    def _render_detail_view(self, loc: dict[str, Any]) -> str:
        return _render_location_detail(loc, self.accessibility)

    # ------------------------------------------------------------------
    # Input handling (simple string-based, for non-interactive testability)
    # ------------------------------------------------------------------

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _prompt(self, message: str) -> str:
        try:
            return input(message)
        except EOFError:
            return "q"

    def run(self) -> None:
        """
        Run the interactive locations directory loop.

        Returns when the user quits.
        """
        locs = self._visible_locations()
        in_detail = False
        detail_loc: dict[str, Any] | None = None

        while self._running:
            self._clear_screen()

            if in_detail and detail_loc:
                print(self._render_detail_view(detail_loc))
                print("")
                print(self._render_footer({
                    "b": "back",
                    "q": "quit",
                }, self.accessibility))
            else:
                print(self._render_browse_view(locs))
                locs = self._visible_locations()

            cmd = self._prompt("\nCommand: ").strip().lower()

            if cmd == "q":
                self._running = False
                break

            if in_detail:
                if cmd == "b":
                    in_detail = False
                    detail_loc = None
                continue

            # Navigation
            if cmd in ("k", "up"):
                if self._selected_index > 0:
                    self._selected_index -= 1
            elif cmd in ("j", "down"):
                max_index = max(0, len(locs) - 1)
                if self._selected_index < max_index:
                    self._selected_index += 1
            elif cmd == "l":
                locs = self._visible_locations()
                if locs and 0 <= self._selected_index < len(locs):
                    detail_loc = locs[self._selected_index]
                    in_detail = True
            elif cmd == "r":
                self._current_filter_type = None
                self._current_filter_region = self._prompt_region()
                self._selected_index = 0
            elif cmd == "t":
                self._current_filter_region = None
                self._current_filter_type = self._prompt_type()
                self._selected_index = 0
            elif cmd == "/":
                self._search_query = self._prompt("Search: ")
                self._selected_index = 0
            elif cmd == "c":
                self._current_filter_region = None
                self._current_filter_type = None
                self._search_query = ""
                self._selected_index = 0

        self._clear_screen()

    # ------------------------------------------------------------------
    # Prompts
    # ------------------------------------------------------------------

    def _prompt_region(self) -> str | None:
        regions = sorted({l["region_id"] for l in self.directory.list_locations()})
        print("\nAvailable regions:")
        for i, r in enumerate(regions, 1):
            print(f"  {i}. {r}")
        choice = self._prompt("Select region number (or Enter for all): ").strip()
        if not choice:
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(regions):
                return regions[idx]
        except ValueError:
            pass
        return None

    def _prompt_type(self) -> str | None:
        types = sorted({l["location_type"] for l in self.directory.list_locations()})
        print("\nAvailable types:")
        for i, t in enumerate(types, 1):
            print(f"  {i}. {t}")
        choice = self._prompt("Select type number (or Enter for all): ").strip()
        if not choice:
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(types):
                return types[idx]
        except ValueError:
            pass
        return None

    # ------------------------------------------------------------------
    # Static convenience entry points
    # ------------------------------------------------------------------

    @staticmethod
    def launch(
        data_path: str | None = None,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        """
        Launch the locations directory UI from a data directory path.
        """
        if data_path:
            directory = load_locations_from_data_dir(data_path)
        else:
            directory = load_locations_from_data_dir()
        ui = LocationDirectoryUI(directory=directory, accessibility=accessibility)
        ui.run()


def render_locations_list(
    directory: LocationDirectory | None = None,
    *,
    region: str | None = None,
    location_type: str | None = None,
    query: str = "",
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Return a rendered string of locations matching optional filters.

    This is the non-interactive rendering API, useful for embedding in
    other UIs or for testing.
    """
    directory = directory or load_locations_from_data_dir()
    locs = directory.list_locations()

    if query:
        q = query.lower()
        locs = [l for l in locs if q in l["name"].lower() or q in l["description"].lower()]
    if region:
        locs = [l for l in locs if l["region_id"] == region]
    if location_type:
        locs = [l for l in locs if l["location_type"] == location_type]

    if not locs:
        return "No locations found."

    lines = [_render_header("LOCATIONS DIRECTORY", accessibility), ""]
    for i, loc in enumerate(locs, 1):
        lines.append(_render_location_row(i, loc, accessibility))
    return "\n".join(lines)
