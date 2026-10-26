# Seven RPG — User Guide

A modular, text-based role-playing game framework built in Python. This guide covers installation, running the game, the terminal user interfaces, the character system, combat, quests, and save/cloud storage.

---

## Table of Contents

1. [Installation](#1-installation)
2. [Running the Game](#2-running-the-game)
3. [User Interfaces](#3-user-interfaces)
4. [Character System](#4-character-system)
5. [Combat](#5-combat)
6. [Quests](#6-quests)
7. [Storage and Save System](#7-storage-and-save-system)

---

## 1. Installation

### System Requirements

- **Python:** 3.14 or newer (3.15 also supported)
- **Operating System:** Windows, macOS, or Linux
- **Memory:** ~512 MB minimum (varies with world size)
- **Network:** Required only for multiplayer, cloud sync, and community features

No C/C++ compiler is required. The runtime dependency is `websockets` (installed automatically).

### Quick Install (End Users)

```bash
git clone https://github.com/seven-rpg/seven-rpg.git
cd seven-rpg
pip install -e .
```

### Verify Installation

```bash
python -c "import seven_rpg; print(seven_rpg.__version__)"
# Expected: 0.1.0
```

### Offline / No-Install Mode

If you have the source tree, you can run without `pip install`:

```bash
PYTHONPATH=src python src/__main__.py
```

Individual modules can be imported by adding `src/` to your path:

```bash
PYTHONPATH=src python -c "from ability import Ability; print('OK')"
```

### Upgrading

```bash
git pull
pip install --upgrade -e .
```

---

## 2. Running the Game

### Launch

Start the main menu:

```python
from main_menu_ui import MainMenuUISession

session = MainMenuUISession()
action = session.run()
# Returns: "new_game", "settings", "credits", or "quit"
```

### Main Menu Options

| Option | Description |
|--------|-------------|
| **New Game** | Start a fresh adventure in a new world |
| **Continue** | Resume the last saved session (when saves are available) |
| **Settings** | Adjust difficulty and accessibility options |
| **Credits** | View contributors |
| **Quit** | Exit to the operating system |

Navigation uses the keyboard. Select an option by typing its number or letter and pressing Enter. Press `q` at any time to quit.

---

## 3. User Interfaces

### 3.1 Main Menu

The main menu renders an ASCII title screen and a boxed menu. It supports:

- **Title screen** with version info
- **Selectable menu items** with hints
- **Settings panel** for difficulty and accessibility
- **Credits screen**

Colors are handled via ANSI escape codes. An `AccessibilityHelper` can override colors for colorblind-safe or high-contrast output.

### 3.2 Settings

Accessible from the main menu. Two layers control gameplay:

**Difficulty Presets**
- `NARRATIVE` — Story-focused; minimal challenge
- `EASY` — Relaxed combat; forgiving
- `NORMAL` — Balanced standard play
- `HARD` — Tough fights; careful planning required
- `NIGHTMARE` — Brutal; every fight is a life-or-death struggle

**Accessibility Options**
- Text size (`normal`, `large`, `extra_large`)
- High contrast mode
- Simplified combat
- Auto-advance dialogue
- Screen reader mode
- Reduce flashes
- Colorblind support (`none`, `protanopia`, `deuteranopia`, `tritanopia`)

### 3.3 Quest Tracker

An interactive terminal panel that shows quest progress.

```python
from quest_tracker import QuestTrackerSession, QuestTracker
from quest_journal import QuestJournalManager

manager = QuestJournalManager()
tracker = QuestTracker(manager=manager)
print(tracker.show_full_tracker(world_id="my_world", session_id="s1"))
```

**Interactive commands:**
- `a` — Show active quests
- `c` — Show completed quests
- `f` — Show failed quests
- `d` — View detail for an active quest
- `q` — Quit tracker

### 3.4 UI Helpers

All terminal UIs support:
- **AccessibilityHelper** for colorblind-safe output, simplified prompts, and screen-reader-friendly formatting
- **ANSI colors** for status indication (cyan = active, green = completed, red = failed)

---

## 4. Character System

### 4.1 Core Concepts

A character is defined by:

- **Base Stats** — Six primary attributes that determine combat effectiveness
- **Derived Stats** — Computed values (HP, MP, defense, etc.) based on formulas
- **Skill Trees** — Abilities organized by category (e.g., fire magic, stealth)
- **Titles** — Honorifics and prestige titles that customize the character's display name

### 4.2 Base Stats

| Stat | ID | Description |
|------|----|-------------|
| Strength | `strength` | Physical power |
| Dexterity | `dexterity` | Agility and accuracy |
| Intelligence | `intelligence` | Magical and mental power |
| Vitality | `vitality` | Endurance and health |
| Charisma | `charisma` | Social influence |
| Luck | `luck` | Fortune and critical chance |

Each stat has a minimum of 1 and a default of 10. Values are clamped to `[1, 100]` by default.

### 4.3 Derived Stats

Derived stats are calculated from base stats using formulas defined in `data/character_stats.json`. Examples include:

- **Health / Max Health**
- **Mana / Max Mana**
- **Stamina**
- **Physical Defense**
- **Magic Resistance**
- **Critical Chance**
- **Dodge Chance**

### 4.4 Stat Point Allocation

As you level up, you gain unspent stat points. Spend them to increase base attributes:

```python
from character_stats import StatsManager

stats = StatsManager()
stats.load_from_json()
success, message = stats.allocate_stat_point(
    character_id="hero_01",
    attribute="strength",
    unspent_points=3
)
```

### 4.5 Temporary Modifiers

Buffs, debuffs, and equipment can add temporary modifiers that stack with base stats:

```python
stats.add_temp_modifier(character_id="hero_01", stat="strength", amount=5)
stats.remove_temp_modifier(character_id="hero_01", stat="strength", amount=5)
stats.clear_temp_modifiers(character_id="hero_01")
```

### 4.6 Character Sheet

View a full summary of your character:

```python
from character_sheet import CharacterSheet

sheet = CharacterSheet()
data = sheet.render_sheet(character_id="hero_01", base_name="Aldric")
print(data["display_name"])        # e.g., "Sir Aldric [Champion of Light]"
print(data["stats_summary"])       # Base, effective, and derived stats
print(data["skill_summaries"])     # Progress in each skill tree
print(data["title_summary"])       # Active honorifics and earned titles
```

### 4.7 Titles

Titles are earned through progression and milestones. They modify the character's display name:

- **Honorifics** — Prefixes (e.g., "Sir", "Dame")
- **Prestige Titles** — Bracketed suffixes (e.g., "[Champion of Light]")

```python
from title_system import TitleManager

title_mgr = TitleManager()
formatted = title_mgr.format_character_name(character_id="hero_01", base_name="Aldric")
```

### 4.8 Skill Trees and Progression

Characters earn XP and unlock abilities through skill trees. Abilities are grouped by category and require stat investment.

```python
from progression import ProgressionSystem
from skill_tree_manager import SkillTreeManager

skill_mgr = SkillTreeManager()
skill_mgr.load_from_json()  # reads data/abilities.json

prog = ProgressionSystem()
xp_result = prog.apply_xp(character_id="hero_01", amount=250)
print(xp_result.unlocked_levels)
```

---

## 5. Combat

Combat is turn-based and mechanical, with tactical positioning, combo chains, finishers, and status effects.

### 5.1 Positions

Combatants can occupy different battlefield positions:

| Position | Effect |
|----------|--------|
| **Frontline** | +10% defense, +10% damage taken |
| **Flank** | +15% attack, +5% crit, +5% dodge |
| **Backline** | -10% defense, +8% crit, +10% dodge, -10% damage taken |
| **Elevated** | +20% attack, +10% crit, -15% damage taken, +2 range |
| **Grounded** | -10% attack, -5% defense, -5% crit, -10% dodge, +15% damage taken |
| **Cover** | +25% defense, +15% dodge, -60% damage taken, -15% attack |

Relative advantages apply: flanking a backline attacker gains +15% hit chance; elevated vs grounded grants +20%.

### 5.2 Combo System

Chain abilities together to build combo points and unlock finishers.

**Combo Tiers:** `NONE` → `BASIC` → `ADVANCED` → `EXPERT` → `MASTER`

Each step in a combo chain has a time window (default 3 seconds). Failing to continue the chain resets it.

### 5.3 Finishers

Finishers are powerful abilities unlocked by meeting conditions:

| Trigger | Description |
|---------|-------------|
| `LOW_HEALTH` | Target is below 25% HP |
| `HIGH_COMBO` | You have 5+ combo points |
| `BEHIND_TARGET` | You are flanking a backline target |
| `TARGET_STUNNED` | Target is stunned |
| `TARGET_BURNING` | Target is burning |
| `SELF_LOW_HEALTH` | You are below 30% HP |
| `POSITION_ADVANTAGE` | You hold a positional advantage |

Finishers cost combo points and deal 1.5× damage.

### 5.4 Status Conditions

Status effects are applied during combat and persist for a duration:

- **Damage Over Time (DOT)** — e.g., Burn
- **Heal Over Time (HOT)**
- **Stun** — Prevents actions
- **Shield** — Reduces incoming damage by 50%
- **Blind** — Increases attacker accuracy against you by 15%
- **Paralyze** — Reduces dodge chance by 25%
- **Root** — Forces grounded position

```python
from status_manager import StatusManager

status_mgr = StatusManager()
condition = status_mgr.apply_status(
    target_id="goblin_01",
    status_id="burn",
    source_id="hero_01",
    duration=3,
)
```

### 5.5 Combat Resolution Flow

1. Turn order is built by speed (highest first)
2. On your turn, select an ability
3. Resolution checks: hit chance → dodge → critical → damage calculation
4. Damage = `max(1, attack - defense × 0.5) × multipliers × position modifiers`
5. Status effects are ticked each round
6. Combat ends when one team is eliminated

### 5.6 Difficulty Integration

Combat values scale with difficulty:

- `damage_dealt_multiplier`
- `damage_taken_multiplier`
- `xp_multiplier`
- `status_duration_multiplier`
- `healing_effectiveness_multiplier`
- `loot_rarity_boost`
- `dc_modifier` (for skill checks)

```python
from difficulty_integration import adjusted_xp_for_level, roll_loot_with_difficulty

xp = adjusted_xp_for_level(base_xp=100, level=5, settings=settings)
item = roll_loot_with_difficulty(loot_table, settings=settings)
```

---

## 6. Quests

### 6.1 Quest Journal

All quests are tracked in a journal bound to a world and session. Each quest has:

- **Objectives** — Tasks with required and current counts
- **Rewards** — XP, gold, items
- **Status** — `active`, `completed`, or `failed`

```python
from quest_journal import QuestJournalManager

journal = QuestJournalManager()
entry = journal.start_quest(quest_id="quest_01", world_id="my_world", session_id="s1")
journal.update_objective(quest_id="quest_01", objective_id="obj_1", delta=1)
journal.complete_quest(quest_id="quest_01")
```

### 6.2 Quest Tracker UI

```python
from quest_tracker import QuestTracker

tracker = QuestTracker(manager=journal)
print(tracker.show_active_quests(world_id="my_world"))
print(tracker.show_quest_detail(quest_id="quest_01"))
```

The tracker renders progress bars:

```
✔ Kill 5 goblins [████████████░░░░░░░] 3/5
○ Collect herbs   [███░░░░░░░░░░░░░░░] 1/4
```

### 6.3 Quest Chains

Quests can be linked into chains with branching paths:

```python
from advanced_quest_system import AdvancedQuestManager

adv = AdvancedQuestManager()
adv.start_chain(chain_id="main_story", world_id="my_world", session_id="s1")
# When a quest completes, auto-progression triggers the next:
adv.on_quest_completed(quest_id="quest_01")
```

### 6.4 Procedural Quests

Templates generate quests dynamically from context:

```python
adv.generate_quest(
    template_id="fetch_quest",
    world_id="my_world",
    session_id="s1",
    seed=42,
    context={"player_level": 5, "target_npc": "blacksmith"},
)
```

### 6.5 Dynamic Objectives

Objectives can scale with level and difficulty:

```python
adv.build_dynamic_objective(
    template_id="kill_bandits",
    context={
        "player_level": 8,
        "difficulty": "hard",
        "world_state": {"bandit_camp_active": True},
    },
)
```

---

## 7. Storage and Save System

### 7.1 Local Persistence

The `WorldPersistence` class serializes the complete game state to a JSON file on disk:

```python
from world_persistence import WorldPersistence

persistence = WorldPersistence()
persistence.save("save/my_world.json")
persistence.load("save/my_world.json")
```

A full save contains:
- **World library** — All worlds, characters, and progress
- **Sessions** — Active play sessions with settings and snapshots
- **Milestones** — Completed achievements
- **Tutorials** — Onboarding state
- **World events** — Active and completed world events
- **World simulation** — Day/night cycles, seasons, weather

### 7.2 World Sessions

A session represents one play period within a world:

```python
from world_session import WorldSessionManager

mgr = WorldSessionManager()
session = mgr.create_session("my_world")
print(session.session_id)  # UUID
mgr.end_session(session.session_id)
```

Sessions track:
- `session_id` — Unique identifier
- `world_id` — Bound world
- `started_at` — ISO timestamp
- `status` — `active`, `paused`, or `ended`
- `snapshot` — Engine-specific state snapshot
- `settings` — Difficulty and accessibility preferences

### 7.3 Cloud Sync

File-based cloud sync via a configurable sync directory (e.g., OneDrive, Dropbox, Google Drive).

```python
from cloud_sync import CloudSyncManager
from world_persistence import WorldPersistence

sync = CloudSyncManager(cloud_dir="~/seven-rpg-cloud")
persistence = WorldPersistence()

# Push local state to cloud
result = sync.push(persistence)
print(result["backup"])  # Path to versioned backup

# Pull cloud state to local
result = sync.pull(persistence)

# Check status and conflicts
status = sync.sync_status(persistence)
print(status["conflict_detected"])  # True / False
```

**Cloud directory layout:**
```
~/seven-rpg-cloud/
  latest.json         — Last synced full state
  local_mirror.json   — Last known local state (conflict detection)
  backups/            — Timestamped snapshot backups (max 20)
  sync_meta.json      — Sync timestamps and counts
```

**Features:**
- **Versioned backups** — Every push creates a timestamped backup; oldest are pruned
- **Conflict detection** — Compares local and cloud modification times against the last mirror
- **Pull / Push** — Explicit two-way sync operations
- **Restore** — Roll back to any backup file

### 7.4 Inventory Storage

Inventory and equipment are persisted as part of the world state:

```python
from inventory import InventoryManager

inv = InventoryManager()
state = inv.get_inventory(character_id="hero_01")
# State includes:
# - capacity (default 24)
# - slots (list of ItemSlot with item + quantity)
# - equipment (dict of EquipmentSlot with durability)
# - gold
```

Each item tracks:
- `id`, `name`, `description`
- `item_type` and `rarity`
- `stackable` and `max_stack`
- `stats` and `effects`
- `durability` / `max_durability`
- `set_id` / `set_piece` for equipment set bonuses

### 7.5 Export / Import State

Quest and world state can be exported and imported programmatically:

```python
# Export quest state
quest_state = journal.export_state()

# Import quest state
journal.import_state(quest_state)

# Export full world state
world_state = persistence.library.export_state()
```

---

## Quick Reference

| Task | Code |
|------|------|
| Start game | `MainMenuUISession().run()` |
| View character | `CharacterSheet().render_sheet(id, name)` |
| Start combat | `CombatEncounter(...).start_encounter()` |
| Track quests | `QuestTracker(manager).show_full_tracker()` |
| Save game | `WorldPersistence().save("path.json")` |
| Cloud push | `CloudSyncManager().push(persistence)` |
| Cloud pull | `CloudSyncManager().pull(persistence)` |
| Check conflicts | `CloudSyncManager().sync_status(persistence)` |

---

For deeper technical details, see the source modules under `src/` and data definitions under `data/`.
