"""
RPG-12-04: Combat UI and Battle Interface
Terminal-based combat interface rendering with battle grid,
health bars, status effects, turn order, combat log, and ability panel.
"""

from __future__ import annotations

from typing import Any

from ability import Ability
from accessibility import AccessibilityHelper
from combat import (
    ActionResultType,
    Combatant,
    CombatantTeam,
    CombatEncounter,
    CombatPosition,
    StatusConditionType,
)

# ---------------------------------------------------------------------------
# Color helpers
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

_TEAM_COLORS: dict[CombatantTeam, str] = {
    CombatantTeam.PLAYER: _BLUE,
    CombatantTeam.ENEMY: _RED,
    CombatantTeam.ALLY: _GREEN,
}

_TEAM_LABELS: dict[CombatantTeam, str] = {
    CombatantTeam.PLAYER: "Player",
    CombatantTeam.ENEMY: "Enemy",
    CombatantTeam.ALLY: "Ally",
}


def _team_color(team: CombatantTeam) -> str:
    return _TEAM_COLORS.get(team, _WHITE)


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


# ---------------------------------------------------------------------------
# Health bar
# ---------------------------------------------------------------------------

def _render_health_bar(
    current: int,
    maximum: int,
    width: int = 20,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    if maximum <= 0:
        pct = 0.0
    else:
        pct = max(0.0, min(1.0, current / maximum))
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    if accessibility is not None:
        color = accessibility.color_text(bar, "green" if pct > 0.5 else "yellow" if pct > 0.25 else "red")
    else:
        if pct > 0.5:
            color = _color(bar, _GREEN)
        elif pct > 0.25:
            color = _color(bar, _YELLOW)
        else:
            color = _color(bar, _RED)
    pct_text = f" {int(pct * 100)}%"
    return f"{color}{pct_text}{_RESET}"


# ---------------------------------------------------------------------------
# Status effects
# ---------------------------------------------------------------------------

_STATUS_ICONS: dict[StatusConditionType, str] = {
    StatusConditionType.BURN: "🔥",
    StatusConditionType.STUN: "⚡",
    StatusConditionType.POISON: "☠",
    StatusConditionType.FREEZE: "❄",
    StatusConditionType.PARALYZE: "😵",
    StatusConditionType.BUFF: "↑",
    StatusConditionType.DEBUFF: "↓",
    StatusConditionType.SHIELD: "🛡",
    StatusConditionType.ROOT: "🌿",
    StatusConditionType.BLIND: "👁",
    StatusConditionType.SILENCE: "🔇",
    StatusConditionType.INVISIBLE: "👻",
}


def _render_status_effects(
    combatant: Combatant,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    icons: list[str] = []
    for (cid, _), active in combatant.status_manager.active.items():
        if cid != combatant.combatant_id:
            continue
        cond_type = getattr(active, "condition_type", None)
        if cond_type is None:
            continue
        icon = _STATUS_ICONS.get(cond_type, "●")
        if accessibility is not None:
            icon = f"{accessibility.get_color('yellow')}{icon}{accessibility.get_color('reset')}"
        else:
            icon = _color(icon, _YELLOW)
        icons.append(icon)
    return " ".join(icons)


# ---------------------------------------------------------------------------
# Combatant card
# ---------------------------------------------------------------------------

def render_combatant_card(
    combatant: Combatant,
    *,
    is_current_turn: bool = False,
    accessibility: AccessibilityHelper | None = None,
    width: int = 36,
) -> str:
    team = combatant.team
    team_color = _team_color(team)
    name = combatant.name
    if accessibility is not None:
        name = accessibility.color_text(name, "cyan" if team == CombatantTeam.PLAYER else "red")
    else:
        name = _color(name, team_color)

    stats = combatant.stats
    hp_bar = _render_health_bar(stats.health, stats.max_health, width=14, accessibility=accessibility)
    status = _render_status_effects(combatant, accessibility=accessibility)
    pos_label = combatant.position.value.upper()[:4]

    turn_marker = ""
    if is_current_turn:
        if accessibility is not None:
            turn_marker = f"{accessibility.get_color('bold')}{accessibility.get_color('inverse')} ◀ TURN ◀ {accessibility.get_color('reset')}"
        else:
            turn_marker = f"{_BOLD}{_INVERSE} ◀ TURN ◀ {_RESET}"

    border_top = "┌" + "─" * (width - 2) + "┐"
    border_bottom = "└" + "─" * (width - 2) + "┘"

    lines = [
        border_top,
        f"│ {_bold(name)} {turn_marker}".ljust(width - 1) + "│",
        f"│   HP: {hp_bar}  POS: {pos_label}".ljust(width - 1) + "│",
        f"│   ATK: {stats.attack_power}  DEF: {stats.defense}".ljust(width - 1) + "│",
    ]
    if status:
        lines.append(f"│   Status: {status}".ljust(width - 1) + "│")
    lines.append(border_bottom)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Battle grid
# ---------------------------------------------------------------------------

_GRID_COLS = 12
_GRID_ROWS = 8

_POSITION_COORDS: dict[CombatPosition, tuple[int, int]] = {
    CombatPosition.BACKLINE: (2, 1),
    CombatPosition.FLANK: (5, 3),  # will be fixed below
    CombatPosition.FRONTLINE: (8, 5),
    CombatPosition.ELEVATED: (4, 1),
    CombatPosition.GROUNDED: (6, 6),
    CombatPosition.COVER: (9, 1),
}


def _get_position_coords(position: CombatPosition) -> tuple[int, int]:
    """Return (col, row) on the terminal battle grid."""
    mapping = {
        CombatPosition.BACKLINE: (1, 1),
        CombatPosition.ELEVATED: (3, 0),
        CombatPosition.COVER: (9, 1),
        CombatPosition.FLANK: (5, 3),
        CombatPosition.FRONTLINE: (7, 5),
        CombatPosition.GROUNDED: (5, 7),
    }
    return mapping.get(position, (6, 4))


def render_battle_grid(
    encounter: CombatEncounter,
    *,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    grid = [[" " for _ in range(_GRID_COLS)] for _ in range(_GRID_ROWS)]

    # Draw grid lines
    for r in range(_GRID_ROWS):
        for c in range(_GRID_COLS):
            if r == 0 or r == _GRID_ROWS - 1 or c == 0 or c == _GRID_COLS - 1:
                grid[r][c] = "·"
            elif r == _GRID_ROWS // 2:
                grid[r][c] = "─"

    # Place combatants
    occupied: dict[tuple[int, int], Combatant] = {}
    for combatant in encounter.combatants:
        if not combatant.is_alive():
            continue
        cx, cy = _get_position_coords(combatant.position)
        # offset slightly if same cell occupied
        key = (cx, cy)
        if key in occupied:
            cx = (cx + 1) % (_GRID_COLS - 2)
            cy = (cy + 1) % (_GRID_ROWS - 2)
            key = (cx, cy)
        occupied[key] = combatant
        if 1 <= cx < _GRID_COLS - 1 and 1 <= cy < _GRID_ROWS - 1:
            icon = "P" if combatant.team == CombatantTeam.PLAYER else "E" if combatant.team == CombatantTeam.ENEMY else "A"
            color_fn = (lambda t, c: accessibility.color_text(t, "cyan" if c == CombatantTeam.PLAYER else "red")) if accessibility else (lambda t, c: _color(t, _team_color(c)))
            grid[cy][cx] = color_fn(icon, combatant.team)

    lines = []
    for row in grid:
        lines.append("│" + "".join(row) + "│")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Turn order
# ---------------------------------------------------------------------------

def render_turn_order(
    encounter: CombatEncounter,
    *,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    if not encounter.turn_order:
        return "Turn order: —"
    names: list[str] = []
    for cid in encounter.turn_order:
        c = encounter.get_combatant(cid)
        if c is None:
            continue
        marker = ""
        if encounter.current_turn_index < len(encounter.turn_order):
            current_id = encounter.turn_order[encounter.current_turn_index]
            if cid == current_id:
                marker = " ◀"
        color_fn = (lambda t, c: accessibility.color_text(t, "cyan" if c == CombatantTeam.PLAYER else "red")) if accessibility else (lambda t, c: _color(t, _team_color(c)))
        names.append(f"{color_fn(c.name, c.team)}{marker}")
    return "Turn order: " + " → ".join(names)


# ---------------------------------------------------------------------------
# Combat log
# ---------------------------------------------------------------------------

def render_combat_log(
    encounter: CombatEncounter,
    *,
    max_lines: int = 6,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    entries = encounter.encounter_log[-max_lines:]
    if not entries:
        return "Combat log: —"
    lines = ["Combat log:"]
    for entry in entries:
        lines.append(f"  - {entry}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Ability panel
# ---------------------------------------------------------------------------

def render_ability_panel(
    combatant: Combatant,
    abilities: list[Ability] | None = None,
    *,
    selected_index: int | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    if abilities is None:
        if combatant.ability_manager is not None:
            abilities = list(combatant.ability_manager.abilities.values())
        else:
            abilities = []
    if not abilities:
        return "Abilities: None"

    lines = ["Abilities:"]
    for idx, ability in enumerate(abilities[:6]):
        marker = ">" if idx == selected_index else " "
        cost = f"{ability.mana_cost} MP" if ability.mana_cost else "Free"
        cd = f"CD {ability.cooldown_seconds}s" if ability.cooldown_seconds else ""
        info = f"{cost} {cd}".strip()
        line = f"  {marker} {idx+1}. {ability.name} ({info})"
        if idx == selected_index and accessibility is not None:
            line = accessibility.emphasize(line)
        elif idx == selected_index:
            line = f"{_BOLD}{line}{_RESET}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main battle interface
# ---------------------------------------------------------------------------

def render_battle_interface(
    encounter: CombatEncounter,
    *,
    current_combatant: Combatant | None = None,
    abilities: list[Ability] | None = None,
    selected_ability_index: int | None = None,
    selected_target_id: str | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the full terminal battle interface for `encounter`.

    Layout:
      - Top bar: round + turn info
      - Left: battle grid with combatant positions
      - Right: turn order + combat log
      - Bottom: current combatant's abilities + target info
    """
    round_info = f"Round {encounter.round_number}"
    turn_info = "Combat active" if encounter.is_active else "Combat ended"
    winner = ""
    if not encounter.is_active and encounter.winner_team is not None:
        winner = f" — {_TEAM_LABELS.get(encounter.winner_team, encounter.winner_team.value)} wins!"
        if accessibility is not None:
            winner = accessibility.color_text(winner, "green")
        else:
            winner = _color(winner, _GREEN)
    header = _bold(f"{round_info} | {turn_info}{winner}")

    grid = render_battle_grid(encounter, accessibility=accessibility)
    turn_order = render_turn_order(encounter, accessibility=accessibility)
    combat_log = render_combat_log(encounter, accessibility=accessibility)

    # Combatant cards
    players = [c for c in encounter.combatants if c.team == CombatantTeam.PLAYER and c.is_alive()]
    enemies = [c for c in encounter.combatants if c.team == CombatantTeam.ENEMY and c.is_alive()]
    allies = [c for c in encounter.combatants if c.team == CombatantTeam.ALLY and c.is_alive()]
    current_id = current_combatant.combatant_id if current_combatant else None

    def _card(c: Combatant) -> str:
        return render_combatant_card(c, is_current_turn=(c.combatant_id == current_id), accessibility=accessibility)

    party_cards = "\n".join(_card(c) for c in players)
    enemy_cards = "\n".join(_card(c) for c in enemies)
    ally_cards = "\n".join(_card(c) for c in allies) if allies else ""

    # Ability panel
    ability_panel = render_ability_panel(
        current_combatant or Combatant(combatant_id="", name="—", team=CombatantTeam.PLAYER),
        abilities=abilities,
        selected_index=selected_ability_index,
        accessibility=accessibility,
    )

    # Target info
    target_info = ""
    if selected_target_id:
        t = encounter.get_combatant(selected_target_id)
        if t:
            target_info = f"Target: {t.name} — HP: {t.stats.health}/{t.stats.max_health}"

    # Assemble panels
    left_panel = f"{party_cards}\n\n{grid}\n\n{enemy_cards}\n\n{ally_cards}"
    right_panel = f"{turn_order}\n\n{combat_log}\n\n{target_info}"

    # Simple side-by-side via line interleave is complex; instead stack vertically with clear separators
    # for a terminal-friendly interface.
    separator = _dim("─" * 60)
    return "\n".join([
        header,
        separator,
        left_panel,
        separator,
        right_panel,
        separator,
        ability_panel,
    ])


def render_action_result(
    result: Any,  # CombatActionResult-like
    *,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a single action result into a short terminal message.
    Expects attributes: result_type, damage, healing, attacker_name, target_name, narration, triggered_finisher.
    """
    attacker = getattr(result, "attacker_name", "?")
    target = getattr(result, "target_name", "?")
    rtype = getattr(result, "result_type", ActionResultType.HIT).value
    damage = getattr(result, "damage", 0)
    healing = getattr(result, "healing", 0)
    narration = getattr(result, "narration", "")
    finisher = getattr(result, "triggered_finisher", None)

    color_fn = (lambda t, c: accessibility.color_text(t, "cyan" if c == "player" else "red")) if accessibility else (lambda t, _: _color(t, _CYAN))

    prefix = f"{attacker} → {target}: "
    if rtype == "critical":
        msg = f"{prefix}CRITICAL HIT for {damage:.1f} dmg!"
        if accessibility is not None:
            msg = accessibility.color_text(msg, "red")
        else:
            msg = _color(msg, _RED)
    elif rtype == "miss":
        msg = prefix + "MISSED"
        if accessibility is not None:
            msg = accessibility.color_text(msg, "dim")
        else:
            msg = _dim(msg)
    elif rtype == "dodged":
        msg = prefix + "DODGED"
        msg = _dim(msg)
    elif rtype == "blocked":
        msg = prefix + "BLOCKED"
        msg = _dim(msg)
    elif rtype == "resisted":
        msg = prefix + "RESISTED"
        msg = _dim(msg)
    else:
        parts = []
        if damage:
            parts.append(f"{damage:.1f} dmg")
        if healing:
            parts.append(f"{healing:.1f} heal")
        msg = prefix + ", ".join(parts) if parts else prefix + "HIT"
        if damage:
            if accessibility is not None:
                msg = accessibility.color_text(msg, "red")
            else:
                msg = _color(msg, _RED)
        elif healing:
            if accessibility is not None:
                msg = accessibility.color_text(msg, "green")
            else:
                msg = _color(msg, _GREEN)

    if finisher:
        msg += f" [FINISHER: {finisher}]"
        if accessibility is not None:
            msg = f"{accessibility.get_color('bold')}{msg}{accessibility.get_color('reset')}"
        else:
            msg = f"{_BOLD}{msg}{_RESET}"
    if narration:
        msg += f" — {narration}"
    return msg
