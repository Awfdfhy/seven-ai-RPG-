"""
RPG-10-12: Tutorial Manager
Convenience wrapper around TutorialManager that loads definitions from
the bundled data/tutorials.json file on first use.
"""

from __future__ import annotations

import json
import os

from tutorial import TutorialDefinition, TutorialManager


class TutorialSystem:
    """
    High-level facade for the tutorial system.

    Loads built-in tutorial definitions from data/tutorials.json and
    exposes a TutorialManager for runtime use.
    """

    def __init__(self, data_path: str | None = None) -> None:
        self.manager = TutorialManager()
        self._data_path = data_path or os.path.join(
            os.path.dirname(__file__), "..", "data", "tutorials.json"
        )
        self._load_definitions()

    def _load_definitions(self) -> None:
        if not os.path.exists(self._data_path):
            return
        with open(self._data_path, encoding="utf-8") as fh:
            raw = json.load(fh)
        definitions = [TutorialDefinition.from_dict(d) for d in raw]
        self.manager.load_definitions(definitions)

    def get_manager(self) -> TutorialManager:
        return self.manager

    def reload(self) -> None:
        self._load_definitions()
