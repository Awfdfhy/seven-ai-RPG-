"""
RPG-09-02: Interactive World Map UI

Terminal-based interactive world map renderer with clickable (selectable)
destinations and a travel panel.  Uses ANSI escape codes for colors and
a numbered-selection interaction model that works in any terminal.

Rendering:
  - Regions are drawn as colored blobs using block characters.
  - Locations appear as numbered markers (1–9, then a–z).
  - The current location is highlighted with a bold marker.
  - Travel routes are drawn as directional lines.

Interaction:
  - Numbers/letters select a destination to travel to.
  - 'l' opens the location info panel.
  - 'q' quits the map view.
"""

from __future__ import annotations

import os
from typing import Any

from accessibility import AccessibilityHelper
from world_map import (
    Location,
    WorldMap,
    WorldMapManager,
    load_world_map_from_data_dir,
)

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_INVERSE = "\033[7m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

# Map coordinate bounds (from data files)
_MAP_MIN_X = 0
_MAP_MAX_X = 800
_MAP_MIN_Y = 0
_MAP_MAX_Y = 400

# Terminal map dimensions
_MAP_COLS = 60
_MAP_ROWS = 20


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Map coordinate normalization
# ---------------------------------------------------------------------------


def _world_to_term(x: int, y: int) -> tuple[int, int]:
    """Convert world pixel coordinates to terminal grid coordinates."""
    tx = int((x - _MAP_MIN_X) / (_MAP_MAX_X - _MAP_MIN_X) * (_MAP_COLS - 1))
    ty = int((y - _MAP_MIN_Y) / (_MAP_MAX_Y - _MAP_MIN_Y) * (_MAP_ROWS - 1))
    return max(0, min(_MAP_COLS - 1, tx)), max(0, min(_MAP_ROWS - 1, ty))


# ---------------------------------------------------------------------------
# ASCII map renderer
# ---------------------------------------------------------------------------


def render_ascii_map(
    world_map: WorldMap,
    current_location_id: str | None = None,
    discovered_locations: set[str] | None = None,
) -> str:
    """
    Render the world map as a 60×20 ASCII grid.

    Cells:
      ' '  empty
      '·'  region interior
      '■'  region center / landmark
      '●'  undiscovered location
      '◉'  discovered location
      '★'  current location
      '─' '│' '╱' '╲'  route segments
    """
    discovered = discovered_locations or set()
    grid = [[" " for _ in range(_MAP_COLS)] for _ in range(_MAP_ROWS)]

    # Draw regions as blobs
    for region in world_map._regions.values():
        cx, cy = _world_to_term(region.x, region.y)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                x = cx + dx
                y = cy + dy
                if 0 <= x < _MAP_COLS and 0 <= y < _MAP_ROWS:
                    if abs(dx) == 2 or abs(dy) == 2:
                        if grid[y][x] == " ":
                            grid[y][x] = "·"
                    else:
                        grid[y][x] = "·"
        grid[cy][cx] = "■"

    # Collect all routes and draw them
    routes_by_cell: dict[tuple[int, int], list[str]] = {}
    for route in world_map._routes:
        fl = world_map.get_location(route.from_location_id)
        tl = world_map.get_location(route.to_location_id)
        if not fl or not tl:
            continue
        fx, fy = _world_to_term(fl.x, fl.y)
        tx, ty = _world_to_term(tl.x, tl.y)
        _draw_line(routes_by_cell, fx, fy, tx, ty)

    for (x, y), chars in routes_by_cell.items():
        if 0 <= x < _MAP_COLS and 0 <= y < _MAP_ROWS:
            if grid[y][x] == " ":
                grid[y][x] = chars[0]

    # Draw locations
    for loc in world_map._locations.values():
        lx, ly = _world_to_term(loc.x, loc.y)
        if loc.id == current_location_id:
            grid[ly][lx] = "★"
        elif loc.id in discovered:
            grid[ly][lx] = "◉"
        else:
            grid[ly][lx] = "●"

    # Assemble lines
    lines = []
    for row in grid:
        lines.append("".join(row))
    return "\n".join(lines)


def _draw_line(cells: dict[tuple[int, int], list[str]], x0: int, y0: int, x1: int, y1: int) -> None:
    """Bresenham-ish line drawing for route visualization."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if (x0, y0) != (x1, y1):
            key = (x0, y0)
            if key not in cells:
                cells[key] = []
            if dx > dy:
                cells[key].append("─")
            else:
                cells[key].append("│")
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


# ---------------------------------------------------------------------------
# Location marker assignment (1–9, a–z)
# ---------------------------------------------------------------------------


def _assign_markers(locations: list[Location]) -> dict[str, str]:
    """Return a mapping of location_id -> display marker (1-9, a-z)."""
    markers = {}
    digits = "123456789"
    letters = "abcdefghijklmnopqrstuvwxyz"
    pool = list(digits + letters)
    for loc in locations:
        if pool:
            markers[loc.id] = pool.pop(0)
        else:
            markers[loc.id] = "?"
    return markers


# ---------------------------------------------------------------------------
# Travel panel renderer
# ---------------------------------------------------------------------------


def render_travel_panel(
    world_map: WorldMap,
    world_id: str,
    manager: WorldMapManager,
) -> str:
    """Render the travel destination panel below the map."""
    state = manager.get_world_state(world_id)
    if not state:
        return _dim("No active world state.") + _RESET

    current = state["current_location"]
    if not current:
        return _dim("Unknown current location.") + _RESET

    lines = []
    lines.append("")
    lines.append(_bold("═" * 60))
    lines.append(
        _bold(f"Current Location: {current['name']}").ljust(60)
    )
    lines.append(f"  Region : {state['current_region']['name'] if state['current_region'] else 'Unknown'}")
    lines.append(f"  Type   : {current.get('location_type', 'generic')}")
    lines.append(f"  Danger : {'🔴' * current.get('danger_level', 1)}")
    lines.append(f"  Clock  : Day {state['clock']['day']}, {state['clock']['hour']:02d}:00")
    lines.append(_bold("═" * 60))

    # Available travel
    available = manager.get_available_travel(world_id)
    if available:
        lines.append(_bold("Available Travel:"))
        lines.append("")
        markers = _assign_markers([world_map.get_location(r["to_location_id"]) for r in available if world_map.get_location(r["to_location_id"])])
        for idx, route in enumerate(available, 1):
            to_loc = world_map.get_location(route["to_location_id"])
            if not to_loc:
                continue
            marker = markers.get(to_loc.id, str(idx))
            discovered = to_loc.id in state["discovered_locations"]
            prefix = "  " if discovered else _dim("? ")
            name = to_loc.name if discovered else _dim("???")
            time_str = f"{route['travel_time_hours']}h"
            danger = "🔴" * to_loc.danger_level
            lines.append(
                f"  {_bold(marker)}. {prefix}{name:20s} {time_str:>4s}  {danger}"
            )
        lines.append("")
        lines.append(_dim("Enter a number/letter to travel, or 'l' for location info.") + _RESET)
    else:
        lines.append(_dim("No outgoing routes from here.") + _RESET)
        lines.append("")

    return "\n".join(lines)


def render_location_info(
    world_map: WorldMap,
    location_id: str,
    discovered: bool = True,
) -> str:
    """Render detailed info for a single location."""
    loc = world_map.get_location(location_id)
    if not loc:
        return _dim("Location not found.") + _RESET

    region = world_map.get_region(loc.region_id)
    lines = []
    lines.append("")
    lines.append(_bold("─" * 60))
    lines.append(_bold(loc.name if discovered else "???"))
    lines.append(_bold("─" * 60))
    lines.append(f"  Region    : {region.name if region else 'Unknown'}")
    lines.append(f"  Type      : {loc.location_type}")
    lines.append(f"  Danger    : {'🔴' * loc.danger_level}")
    lines.append("")
    if discovered:
        lines.append(f"  {loc.description}")
    else:
        lines.append(_dim("  This location has not been discovered yet.") + _RESET)
    lines.append("")

    # Connections
    routes = world_map.get_routes_from(location_id)
    if routes:
        lines.append(_bold("Routes:"))
        for r in routes:
            to_loc = world_map.get_location(r["to_location_id"])
            to_name = to_loc.name if to_loc and to_loc.id in set() else "???"
            lines.append(
                f"  → {to_name:20s}  {r['travel_time_hours']}h  dist {r['distance']}"
            )
    lines.append(_bold("─" * 60))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive map session
# ---------------------------------------------------------------------------


class InteractiveMapSession:
    """
    Drives an interactive map loop in the terminal.

    Usage:
        session = InteractiveMapSession(world_map, world_id, manager)
        session.run()
    """

    def __init__(
        self,
        world_map: WorldMap,
        world_id: str,
        manager: WorldMapManager,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.world_map = world_map
        self.world_id = world_id
        self.manager = manager
        self.accessibility = accessibility
        self._running = True

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _render_frame(self, highlight_marker: str | None = None) -> None:
        state = self.manager.get_world_state(self.world_id)
        current_id = state["current_location"]["id"] if state and state["current_location"] else None
        discovered = set(state["discovered_locations"]) if state else set()

        map_str = render_ascii_map(
            self.world_map,
            current_location_id=current_id,
            discovered_locations=discovered,
        )
        panel_str = render_travel_panel(self.world_map, self.world_id, self.manager)

        # Assemble
        output = []
        output.append(_bold("╔" + "═" * 58 + "╗"))
        output.append(_bold("║" + "WORLD MAP".center(58) + "║"))
        output.append(_bold("╚" + "═" * 58 + "╝"))
        output.append("")
        output.append(map_str)
        output.append(panel_str)

        if highlight_marker:
            output.append("")
            output.append(_bold(f"Selected: {highlight_marker}"))

        self._clear_screen()
        print("\n".join(output))

    def run(self) -> dict[str, Any]:
        """
        Run the interactive loop. Returns the final world state dict.
        """
        self._render_frame()

        while self._running:
            try:
                prompt = "Command [number=travel, l=info, q=quit]: "
                if self.accessibility:
                    prompt = self.accessibility.simplify_command_prompt(prompt)
                choice = input(_bold(prompt) + _RESET).strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "q":
                self._running = False
                break

            if choice == "l":
                self._show_location_info()
                continue

            # Try numeric/alpha selection
            dest = self._resolve_selection(choice)
            if dest:
                result = self.manager.travel(self.world_id, dest)
                if result.get("success"):
                    self._render_frame()
                    print(_GREEN + f"Traveled to {result['world_state']['current_location']['name']}." + _RESET)
                else:
                    self._render_frame()
                    print(_RED + f"Travel failed: {result.get('reason', 'unknown')}" + _RESET)
                cont_prompt = "Press Enter to continue..."
                if self.accessibility:
                    cont_prompt = self.accessibility.simplify_command_prompt(cont_prompt)
                input(_dim(cont_prompt) + _RESET)

        return self.manager.get_world_state(self.world_id)

    def _resolve_selection(self, marker: str) -> str | None:
        """Convert a number/letter marker to a location_id for travel."""
        state = self.manager.get_world_state(self.world_id)
        if not state:
            return None

        available = self.manager.get_available_travel(self.world_id)
        locs = [self.world_map.get_location(r["to_location_id"]) for r in available if self.world_map.get_location(r["to_location_id"])]
        markers = _assign_markers(locs)

        # Reverse lookup
        rev = {v: k.id for k, v in zip(locs, markers.values()) if k}
        return rev.get(marker)

    def _show_location_info(self) -> None:
        state = self.manager.get_world_state(self.world_id)
        if not state or not state["current_location"]:
            return
        loc_id = state["current_location"]["id"]
        info = render_location_info(self.world_map, loc_id, discovered=True)
        self._clear_screen()
        print(info)
        cont_prompt = "Press Enter to return to map..."
        if self.accessibility:
            cont_prompt = self.accessibility.simplify_command_prompt(cont_prompt)
        input(_dim(cont_prompt) + _RESET)


# ---------------------------------------------------------------------------
# Convenience loader
# ---------------------------------------------------------------------------


def create_interactive_map(
    world_id: str = "default",
    base_path: str | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> InteractiveMapSession:
    """
    Load map data from the default data directory and return a ready session.
    """
    world_map = load_world_map_from_data_dir(base_path)
    manager = WorldMapManager(world_map)
    manager.ensure_world(world_id)
    return InteractiveMapSession(world_map, world_id, manager, accessibility)
