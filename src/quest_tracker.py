"""
RPG-10-15: Quest Tracker
Terminal-based quest tracker and objective progress UI.
Displays active, completed, and failed quests with progress bars,
objective breakdowns, and reward summaries.

Integrates with QuestJournalManager and AdvancedQuestManager.
"""

from __future__ import annotations

import os
from typing import Any

from accessibility import AccessibilityHelper
from quest_journal import QuestEntry, QuestJournalManager, QuestObjective, QuestReward

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

def _red(text: str) -> str:
    return f"{_RED}{text}{_RESET}"

def _green(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}"

def _yellow(text: str) -> str:
    return f"{_YELLOW}{text}{_RESET}"

def _blue(text: str) -> str:
    return f"{_BLUE}{text}{_RESET}"

def _magenta(text: str) -> str:
    return f"{_MAGENTA}{text}{_RESET}"

def _cyan(text: str) -> str:
    return f"{_CYAN}{text}{_RESET}"

def _white(text: str) -> str:
    return f"{_WHITE}{text}{_RESET}"

_STATUS_COLORS: dict[str, str] = {
    "active": _CYAN,
    "completed": _GREEN,
    "failed": _RED,
}


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return f"{_BOLD}{text}{_RESET}"


def _dim(text: str) -> str:
    return f"{_DIM}{text}{_RESET}"


def _status_color(status: str) -> str:
    return _STATUS_COLORS.get(status, _WHITE)


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def render_progress_bar(
    current: int,
    required: int,
    width: int = 20,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a textual progress bar for an objective.

    Returns a string like: [████████████░░░░░░░] 3/5
    """
    if required <= 0:
        pct = 1.0
        filled = width
    else:
        pct = max(0.0, min(1.0, current / required))
        filled = int(width * pct)
    empty = width - filled
    bar = "█" * filled + "░" * empty

    if accessibility is not None:
        color_name = "green" if pct >= 1.0 else "yellow" if pct >= 0.5 else "red"
        bar = accessibility.color_text(bar, color_name)
        reset = accessibility.get_color("reset")
        count_text = f" {current}/{required}"
        return f"[{bar}{reset}]{count_text}"

    code = _GREEN if pct >= 1.0 else _YELLOW if pct >= 0.5 else _RED
    return f"[{_color(bar, code)}] {current}/{required}"


# ---------------------------------------------------------------------------
# Objective rendering
# ---------------------------------------------------------------------------

def render_objective(
    objective: QuestObjective,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a single quest objective line with progress bar.
    """
    completed = objective.current_count >= objective.required_count
    if accessibility is not None:
        if completed:
            prefix = accessibility.color_text("✔", "green")
            desc = accessibility.color_text(objective.description, "green")
        else:
            prefix = accessibility.color_text("○", "dim")
            desc = accessibility.color_text(objective.description, "dim")
        bar = render_progress_bar(
            objective.current_count, objective.required_count, accessibility=accessibility
        )
        return f"  {prefix} {desc} {bar}"
    else:
        if completed:
            prefix = _color("✔", _GREEN)
            desc = _color(objective.description, _GREEN)
        else:
            prefix = _color("○", _DIM)
            desc = _color(objective.description, _DIM)
        bar = render_progress_bar(
            objective.current_count, objective.required_count, accessibility=accessibility
        )
        return f"  {prefix} {desc} {bar}"


# ---------------------------------------------------------------------------
# Reward rendering
# ---------------------------------------------------------------------------

def render_rewards(
    rewards: list[dict[str, Any] | QuestReward],
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a compact rewards summary for a quest.
    """
    if not rewards:
        return ""
    lines: list[str] = []
    label = "Rewards:" if accessibility is None else _bold("Rewards:")
    for r in rewards:
        if isinstance(r, QuestReward):
            rtype = r.type
            amount = r.amount
            item_id = r.item_id
        else:
            rtype = r.get("type", "?")
            amount = r.get("amount", 0)
            item_id = r.get("item_id")
        if item_id:
            text = f"  • {item_id} ({rtype}: {amount})"
        else:
            text = f"  • {amount} {rtype}"
        if accessibility is not None:
            text = accessibility.color_text(text, "cyan")
        else:
            text = _color(text, _CYAN)
        lines.append(text)
    return label + "\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Quest detail / card rendering
# ---------------------------------------------------------------------------

def render_quest_card(
    entry: QuestEntry,
    show_rewards: bool = True,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render a full quest card with name, description, objectives,
    and optional rewards.
    """
    status = entry.status
    if accessibility is not None:
        status_label = accessibility.color_text(status.upper(), status)
        name = accessibility.color_text(entry.name, "bold")
    else:
        status_label = _color(status.upper(), _status_color(status))
        name = _bold(entry.name)

    width = 58
    lines = [
        _bold("╔" + "═" * width + "╗") if accessibility is None else "═" * (width + 2),
        f"  {name} — {status_label}",
        _bold("╚" + "═" * width + "╝") if accessibility is None else "═" * (width + 2),
        "",
        f"  {entry.description}",
        "",
    ]

    if entry.objectives:
        lines.append(_bold("Objectives:"))
        for obj in entry.objectives:
            lines.append(render_objective(obj, accessibility=accessibility))
        lines.append("")

    if show_rewards and entry.status == "completed":
        reward_text = render_rewards(entry.rewards, accessibility=accessibility)
        if reward_text:
            lines.append(reward_text)
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tracker panel rendering
# ---------------------------------------------------------------------------

def render_quest_tracker(
    manager: QuestJournalManager,
    *,
    world_id: str | None = None,
    session_id: str | None = None,
    status: str | None = None,
    show_rewards: bool = True,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    Render the full quest tracker panel.

    Shows all quests matching the given filters, grouped by status.
    """
    all_quests = manager.list_quests(
        world_id=world_id, session_id=session_id, status=status
    )
    # Convert dicts back to QuestEntry for rendering
    entries: list[QuestEntry] = []
    for q in all_quests:
        if isinstance(q, QuestEntry):
            entries.append(q)
        else:
            # list_quests returns dicts; build minimal entries
            entries.append(QuestEntry(
                quest_id=q["quest_id"],
                name=q["name"],
                description=q["description"],
                status=q["status"],
                started_at=q.get("started_at", ""),
                completed_at=q.get("completed_at"),
                failed_at=q.get("failed_at"),
                objectives=[
                    QuestObjective(
                        id=o["id"],
                        description=o.get("description", ""),
                        required_count=o.get("required_count", 1),
                        current_count=o.get("current_count", 0),
                        metadata=o.get("metadata", {}),
                    )
                    for o in q.get("objectives", [])
                ],
                rewards=[
                    {"type": r.get("type"), "amount": r.get("amount", 0), "item_id": r.get("item_id")}
                    for r in q.get("rewards", [])
                ],
                world_id=q.get("world_id"),
                session_id=q.get("session_id"),
                metadata=q.get("metadata", {}),
            ))

    active = [e for e in entries if e.status == "active"]
    completed = [e for e in entries if e.status == "completed"]
    failed = [e for e in entries if e.status == "failed"]

    title = "QUEST TRACKER"
    if world_id:
        title += f" — {world_id}"
    if session_id:
        title += f" ({session_id})"

    lines = [
        _bold("╔" + "═" * 58 + "╗"),
        _bold("║" + title.center(58) + "║"),
        _bold("╚" + "═" * 58 + "╝"),
        "",
    ]

    # Active first, then completed, then failed
    sections = [
        ("active", active),
        ("completed", completed),
        ("failed", failed),
    ]

    any_rendered = False
    for section_status, section_entries in sections:
        if not section_entries:
            continue
        any_rendered = True
        header = _color(f"── {section_status.upper()} ({len(section_entries)}) ", _status_color(section_status))
        if accessibility is not None:
            header = accessibility.color_text(f"── {section_status.upper()} ({len(section_entries)}) ", status)
        lines.append(header)
        for entry in section_entries:
            lines.append(render_quest_card(entry, show_rewards=show_rewards, accessibility=accessibility))
            lines.append("")

    if not any_rendered:
        lines.append(_dim("  No quests found."))
        lines.append("")

    return "\n".join(lines)


def render_quest_summary(
    manager: QuestJournalManager,
    *,
    world_id: str | None = None,
    session_id: str | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> str:
    """
    One-line summary of quest statuses.
    E.g. "Active: 2 | Completed: 1 | Failed: 0"
    """
    active = len(manager.list_quests(world_id=world_id, session_id=session_id, status="active"))
    completed = len(manager.list_quests(world_id=world_id, session_id=session_id, status="completed"))
    failed = len(manager.list_quests(world_id=world_id, session_id=session_id, status="failed"))

    if accessibility is not None:
        parts = [
            f"Active: {active}",
            f"Completed: {completed}",
            f"Failed: {failed}",
        ]
        return " | ".join(parts)

    parts = [
        _color(f"Active: {active}", _CYAN),
        _color(f"Completed: {completed}", _GREEN),
        _color(f"Failed: {failed}", _RED),
    ]
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------

class QuestTracker:
    """
    High-level quest tracker UI facade.
    Composes rendering functions around a QuestJournalManager.
    """

    def __init__(
        self,
        manager: QuestJournalManager | None = None,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager or QuestJournalManager()
        self.accessibility = accessibility

    def show_full_tracker(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        Render the full quest tracker panel.
        """
        return render_quest_tracker(
            self.manager,
            world_id=world_id,
            session_id=session_id,
            accessibility=self.accessibility,
        )

    def show_active_quests(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        Render only active quests.
        """
        return render_quest_tracker(
            self.manager,
            world_id=world_id,
            session_id=session_id,
            status="active",
            accessibility=self.accessibility,
        )

    def show_completed_quests(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        Render only completed quests.
        """
        return render_quest_tracker(
            self.manager,
            world_id=world_id,
            session_id=session_id,
            status="completed",
            accessibility=self.accessibility,
        )

    def show_failed_quests(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        Render only failed quests.
        """
        return render_quest_tracker(
            self.manager,
            world_id=world_id,
            session_id=session_id,
            status="failed",
            accessibility=self.accessibility,
        )

    def show_quest_detail(self, quest_id: str) -> str:
        """
        Render detailed view of a single quest.
        """
        entry = self.manager.get_quest(quest_id)
        if entry is None:
            return "Quest not found."
        return render_quest_card(
            entry,
            show_rewards=True,
            accessibility=self.accessibility,
        )

    def show_summary(
        self,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """
        One-line status summary.
        """
        return render_quest_summary(
            self.manager,
            world_id=world_id,
            session_id=session_id,
            accessibility=self.accessibility,
        )

    def show_objective_progress(self, quest_id: str) -> dict[str, Any]:
        """
        Return structured objective progress for a quest.
        """
        return self.manager.get_progress(quest_id)


# ---------------------------------------------------------------------------
# Interactive session
# ---------------------------------------------------------------------------

class QuestTrackerSession:
    """
    Interactive quest tracker loop in the terminal.

    Usage:
        session = QuestTrackerSession(manager, "hero")
        session.run()
    """

    def __init__(
        self,
        manager: QuestJournalManager,
        world_id: str,
        session_id: str | None = None,
        accessibility: AccessibilityHelper | None = None,
    ) -> None:
        self.manager = manager
        self.world_id = world_id
        self.session_id = session_id
        self.accessibility = accessibility
        self._running = True

    def _clear_screen(self) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _render_frame(self, message: str = "") -> None:
        tracker = QuestTracker(manager=self.manager, accessibility=self.accessibility)
        panel = tracker.show_full_tracker(world_id=self.world_id, session_id=self.session_id)
        summary = tracker.show_summary(world_id=self.world_id, session_id=self.session_id)

        output: list[str] = [
            _bold("╔" + "═" * 58 + "╗"),
            _bold("║" + "QUEST TRACKER".center(58) + "║"),
            _bold("╚" + "═" * 58 + "╝"),
            "",
            panel,
            "",
            _bold("Summary:") + _RESET,
            f"  {summary}",
            "",
        ]
        if message:
            output.append(message)

        self._clear_screen()
        print("\n".join(output))

    def run(self) -> None:
        """
        Run the interactive tracker loop.
        """
        self._render_frame()

        while self._running:
            try:
                prompt = "Command [a=active, c=completed, f=failed, d=detail, q=quit]: "
                if self.accessibility:
                    prompt = self.accessibility.simplify_command_prompt(prompt)
                choice = input(_bold(prompt) + _RESET).strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if choice == "q":
                self._running = False
                break

            tracker = QuestTracker(manager=self.manager, accessibility=self.accessibility)
            world_id = self.world_id
            session_id = self.session_id

            if choice == "a":
                self._render_frame(tracker.show_active_quests(world_id=world_id, session_id=session_id))
                input(_dim("Press Enter to continue...") + _RESET)
                self._render_frame()
            elif choice == "c":
                self._render_frame(tracker.show_completed_quests(world_id=world_id, session_id=session_id))
                input(_dim("Press Enter to continue...") + _RESET)
                self._render_frame()
            elif choice == "f":
                self._render_frame(tracker.show_failed_quests(world_id=world_id, session_id=session_id))
                input(_dim("Press Enter to continue...") + _RESET)
                self._render_frame()
            elif choice == "d":
                quests = self.manager.list_quests(world_id=world_id, session_id=session_id, status="active")
                if not quests:
                    print(_red("No active quests to show.") + _RESET)
                    input(_dim("Press Enter to continue...") + _RESET)
                    self._render_frame()
                else:
                    for i, q in enumerate(quests, 1):
                        print(f"  {i}. {q['name']} ({q['quest_id']})")
                    try:
                        idx = input("Enter quest number: ").strip()
                        if idx.isdigit():
                            idx = int(idx) - 1
                            if 0 <= idx < len(quests):
                                qid = quests[idx]["quest_id"]
                                self._render_frame(tracker.show_quest_detail(qid))
                                input(_dim("Press Enter to continue...") + _RESET)
                                self._render_frame()
                            else:
                                print(_red("Invalid number.") + _RESET)
                                input(_dim("Press Enter to continue...") + _RESET)
                                self._render_frame()
                        else:
                            self._render_frame()
                    except (EOFError, KeyboardInterrupt):
                        self._render_frame()
            else:
                self._render_frame(_red(f"Unknown command: {choice}") + _RESET)


def create_tracker_session(
    manager: QuestJournalManager,
    world_id: str,
    session_id: str | None = None,
    accessibility: AccessibilityHelper | None = None,
) -> QuestTrackerSession:
    """
    Convenience factory for a quest tracker session.
    """
    return QuestTrackerSession(manager, world_id, session_id, accessibility)
