# Seven RPG — Release Notes v0.1.0

**Release Date:** 2026-10-26
**Codename:** First Light

Seven RPG is a data-driven, text/stat RPG framework written in Python. It ships with a full suite of interlocking systems for world simulation, character progression, combat, crafting, economy, storytelling, and post-game content. All gameplay content lives in JSON data files; the engine is pure Python with no external runtime dependencies.

---

## What's Included

- **81 source modules** (~28,500 LOC) in `src/`
- **33 JSON data files** in `data/`
- **62 test modules** covering the majority of systems

---

## Getting Started

```bash
# Clone / enter the project
cd C:\Users\seven\seven-rpg

# Run the test suite (no virtualenv required — stdlib only)
python tests/test_abilities.py
python tests/test_economy.py
# ... or run any individual test file
```

No `pip install` step is required; the project runs on the bundled Python standard library.

---

## Architecture at a Glance

```
seven-rpg/
  src/            Engine modules (dataclasses, managers, UI renderers)
  data/           JSON content definitions
  tests/          Unit / integration tests per system
```

---

## System Overview

| System | Source Module(s) | Data File(s) | Status |
|--------|------------------|--------------|--------|
| World Library & Persistence | `world_library.py`, `world_persistence.py` | — | ✅ Stable |
| World Session & Bridge | `world_session.py`, `world_bridge.py` | — | ✅ Stable |
| Character Sheet | `character_sheet.py` | — | ✅ Stable |
| Title System | `title_system.py` | `data/titles.json` | ✅ Stable |
| Travel Ledger | `travel_ledger.py` | — | ✅ Stable |
| Progression & XP | `progression.py`, `progression_manager.py` | — | ✅ Stable |
| Skill Tree | `skill_tree.py`, `skill_tree_builder.py`, `skill_tree_manager.py` | `data/abilities.json` | ✅ Stable |
| Ability System | `ability.py`, `ability_manager.py` | `data/abilities.json` | ✅ Stable |
| Combat | `combat.py` | — | ✅ Stable |
| Status Conditions | `status_conditions.py`, `status_manager.py` | `data/status_conditions.json` | ✅ Stable |
| Inventory & Equipment | `inventory.py`, `inventory_ui.py`, `loot.py` | `data/loot_tables.json`, `data/equipment*.json` | ✅ Stable |
| Crafting | `crafting.py`, `crafting_manager.py` | `data/crafting_*.json` | ✅ Stable |
| Economy & Merchants | `economy.py` | — | ✅ Stable |
| Party & Companions | `party.py` | `data/companions.json` | ✅ Stable |
| NPC Dialogue | `npc_dialogue.py`, `npc_reaction.py` | `data/npc_dialogues.json` | ✅ Stable |
| Milestones | `milestone.py` | `data/milestones.json` | ✅ Stable |
| Mini-Games | `mini_games.py` | — | ✅ Stable |
| Tutorials & Onboarding | `tutorial.py`, `tutorial_manager.py`, `onboarding.py` | `data/tutorials.json`, `data/onboarding.json` | ✅ Stable |
| Difficulty & Accessibility | `difficulty_settings.py`, `difficulty_integration.py`, `accessibility.py` | — | ✅ Stable |
| Soundtrack | `soundtrack.py` | — | ✅ Stable |
| AI Narration | `ai_narration.py` | — | ✅ Stable |
| Weather & Fiction | `weather_fiction.py` | `data/world_map.json` | ✅ Stable |
| World Map | `world_map.py`, `world_map_ui.py` | `data/world_locations.json`, `data/world_map.json` | ⚠️ Minor issues |
| Skill Check | `skill_check.py` | — | ⚠️ Minor issues |
| Session Branching | `session_branch.py` | — | ✅ Stable |
| Advanced Quest System | `advanced_quest_system.py`, `quest_journal.py` | `data/quests.json` | ⚠️ Needs polish |
| Dynamic World Events | `world_events.py` | `data/world_events.json` | ✅ Stable |
| Procedural Generation | `procedural_generation.py` | — | ⚠️ Needs polish |
| Advanced AI | `advanced_ai.py` | — | 🚧 Scaffolded |
| Endgame & NG+ | `endgame.py`, `new_game_plus.py` | — | ⚠️ Needs polish |
| Performance Optimizer | `performance_optimizer.py` | — | ⚠️ Needs polish |
| Update System | `update_system.py` | — | ⚠️ Needs polish |
| Cloud Sync | `cloud_sync.py` | — | ⚠️ Needs polish |
| Analytics | `analytics.py` | — | 🚧 Scaffolded |
| Community | `community.py` | — | 🚧 Scaffolded |
| Mod Support | `mod_manager.py`, `mod_integration.py` | — | 🚧 Scaffolded |

---

## Test Results Summary

| Category | Result |
|----------|--------|
| Passing test files | 31 of 62 |
| Failing test files | 8 |
| No tests ran | 4 (scaffolded modules) |

Known failing areas:
- `test_advanced_quest_system` — 3 failures
- `test_cloud_sync` — 1 failure
- `test_endgame` — 6 failures
- `test_mod_support` — 2 failures
- `test_performance_optimizer` — 4 failures
- `test_procedural_generation` — 1 failure
- `test_skill_check` — 1 failure
- `test_update_system` — 1 failure
- `test_world_map` — 2 failures

---

## Known Issues

- **No pytest dependency**: `test_data_integrity.py` requires `pytest` which is not bundled.
- **Performance optimizer type bug**: `AssetType` is referenced before definition in some test paths.
- **World map travel validation**: Invalid route assertions need tightening.
- **Cloud sync conflict resolution**: Edge cases in conflict detection still pending.
- **Endgame balance**: NG+ carry-over multipliers and scaling need tuning.

---

## Roadmap

- v1.1.x — Polish failing tests, bundle pytest, fix optimizer type bug
- v1.2.x — Endgame & procedural content polish
- v1.3.x — Cloud sync conflict UX & analytics telemetry
- v2.0.0 — First-party content pack (full campaign module)
