# User Guide

## What Is Seven RPG?

Seven RPG is a modular, data-driven text/mechanical role-playing game framework written in Python. It is designed for players, game masters, and modders who want structured RPG mechanics — combat, crafting, skill trees, world simulation — without a heavy graphical engine.

All gameplay content lives in JSON data files. The engine is pure Python with one runtime dependency (`websockets`) for online features.

---

## Core Concepts

### Worlds and Sessions

- **World:** A persistent RPG world. Each world has its own character, progress, and data.
- **Session:** An active play period within a world. Sessions track when you played, settings used, and snapshots of game state.

```python
from world_session import WorldSessionManager

mgr = WorldSessionManager()
session = mgr.create_session("my_first_world")
print(session.session_id)  # UUID identifying this session
```

### Characters

Characters aggregate stats, skill trees, and titles into a single sheet.

```python
from character_sheet import CharacterSheet

sheet = CharacterSheet()
data = sheet.render_sheet(character_id="hero_01", base_name="Aldric")
print(data["formatted_titles"])  # e.g. "Sir Aldric [Champion of Light]"
```

### Settings

Two layers control how the game behaves:

- **Difficulty Preset:** `NARRATIVE`, `EASY`, `NORMAL`, `HARD`, or `NIGHTMARE`
- **Accessibility Options:** Text size, high contrast, simplified combat, screen reader mode, reduce flashes, colorblind support

```python
from difficulty_settings import GameSettings, DifficultyPreset

settings = GameSettings(difficulty=DifficultyPreset.EASY)
print(settings.difficulty)
```

---

## Main Menu

The built-in terminal UI provides:

| Option | Description |
|--------|-------------|
| **New Game** | Start a fresh adventure |
| **Continue** | Resume the last saved session (requires save support) |
| **Settings** | Adjust difficulty and accessibility options |
| **Credits** | View contributors |
| **Quit** | Exit the application |

```python
from main_menu_ui import MainMenuUISession

session = MainMenuUISession()
action = session.run()  # "new_game", "settings", "credits", "quit", ...
```

---

## Gameplay Systems

### Skill Trees and Progression

Characters earn XP and unlock abilities through skill trees. Abilities are organized by category (e.g. fire magic, stealth) and require stat investment.

- **Progression:** `progression.py`, `progression_manager.py`
- **Skill Trees:** `skill_tree.py`, `skill_tree_builder.py`, `skill_tree_manager.py`
- **Abilities:** `ability.py`, `ability_manager.py`
- **Titles:** `title_system.py`

```python
from skill_tree_manager import SkillTreeManager
from progression import ProgressionSystem

# Load skill trees from JSON data
skill_mgr = SkillTreeManager()
skill_mgr.load_from_json()  # reads data/abilities.json

# Grant XP and check level-ups
prog = ProgressionSystem()
xp_result = prog.apply_xp(character_id="hero_01", amount=250)
print(xp_result.unlocked_levels)
```

### Combat

Turn-based and mechanical combat with status conditions, cooldowns, and difficulty-aware resolution.

```python
from combat import CombatResolver
from status_manager import StatusManager

resolver = CombatResolver()
status_mgr = StatusManager()

# Apply a burn effect (damage over time)
condition = status_mgr.apply_status(
    target_id="goblin_01",
    status_id="burn",
    source_id="hero_01",
    duration=3,
)
```

### Inventory and Equipment

Items have rarity, categories, and equipment slots. Equipment panels and tooltips are rendered by dedicated UI helpers.

```python
from inventory import InventoryManager, Item

inv = InventoryManager()
inv.add_item(Item(id="potion_heal", name="Healing Potion", rarity="common"))
inv.equip("potion_heal", slot="accessory")
```

### Crafting

Combine materials at stations to create items. Recipes are defined in JSON.

```python
from crafting import CraftingManager

craft = CraftingManager()
craft.load_recipes("data/crafting_recipes.json")
can_craft = craft.can_craft("iron_sword", inventory=inv)
```

### Economy and Merchants

Dynamic market state, merchant stock, and price rules.

```python
from economy import EconomyManager

eco = EconomyManager()
merchant = eco.get_merchant("blacksmith")
price = eco.get_price("iron_sword", merchant_id="blacksmith")
```

### World Map and Travel

Travel between locations with a ledger of journey events and day/night simulation.

```python
from travel_ledger import TravelLedgerManager

travel = TravelLedgerManager()
entry = travel.begin_journey(
    character_id="hero_01",
    from_location="village",
    to_location="castle",
)
```

### NPCs and Dialogue

Branching dialogue with player choices and NPC reactions.

```python
from npc_dialogue import DialogueManager

dlg = DialogueManager()
dlg.load_from_json("data/npc_dialogues.json")
session = dlg.start_dialogue("npc_elder")
for choice in session.choices:
    print(choice.text)
```

### Party and Companions

Recruit companions with AI-driven behavior and stances.

```python
from party import PartyManager

party = PartyManager()
party.add_companion(companion_id="fairy_tink", archetype="support")
```

### Tutorials and Onboarding

New players are guided through tutorial steps with hints and skip options.

```python
from onboarding import OnboardingManager

onboard = OnboardingManager()
state = onboard.start_onboarding("my_first_world", session_id="s1")
hint = onboard.get_hint("my_first_world")
```

### Weather, Time, and World Simulation

Day/night cycles, seasons, ecosystems, and resource nodes simulate a living world.

```python
from world_simulation import WorldSimulationManager

sim = WorldSimulationManager()
print(sim.current_phase())   # "day", "dusk", "night", ...
print(sim.current_season())  # "spring", "summer", ...
```

---

## Online Features

### Multiplayer

Host or join shared-state rooms over WebSocket.

```python
from multiplayer import MultiplayerServer, MultiplayerClient

# Server
server = MultiplayerServer(host="0.0.0.0", port=8765)
server.start()

# Client
client = MultiplayerClient("ws://localhost:8765")
client.connect()
client.send_chat(ChatMessage(author="hero_01", text="Hello!"))
```

### Cloud Sync

Sync save data to the cloud. Conflict resolution and offline queuing are built in.

```python
from cloud_sync import CloudSyncManager

sync = CloudSyncManager()
sync.upload_world_state("my_first_world", state_data)
```

### Community

Leaderboards and shared build uploads.

```python
from community import LeaderboardManager

lb = LeaderboardManager()
entries = lb.get_leaderboard(LeaderboardCategory.FASTEST_CLEAR)
```

---

## Modding

Create mods by providing JSON data files and a `mod.json` manifest.

### Example Mod Structure

```
mods/example_mod/
  mod.json
  data/
    skill_tree.json
```

`mod.json`:

```json
{
  "id": "example_mod",
  "name": "Example Mod",
  "version": "1.0.0",
  "description": "A demonstration mod.",
  "author": "SevenRPG",
  "enabled": true,
  "data_files": ["data/skill_tree.json"]
}
```

### Loading Mods

```python
from mod_manager import ModManager
from mod_integration import apply_mods_to_manager

mod_mgr = ModManager()
mod_mgr.load_mods("mods/")
apply_mods_to_manager(mod_mgr, skill_manager=skill_mgr, economy_manager=eco)
```

---

## Analytics

Opt-in telemetry tracks gameplay events for debugging and balance.

```python
from analytics import AnalyticsManager

analytics = AnalyticsManager()
analytics.record_event(GameplayEvent(event_type="combat_victory", details={...}))
```

---

## Accessibility and Difficulty Integration

Difficulty-aware resolvers automatically scale XP, loot, and status effects.

```python
from difficulty_integration import (
    adjusted_xp_for_level,
    roll_loot_with_difficulty,
    apply_status_with_difficulty,
)

xp = adjusted_xp_for_level(base_xp=100, level=5, settings=settings)
item = roll_loot_with_difficulty(loot_table, settings=settings)
```

---

## Virtual and Augmented Reality

Optional VR/AR sessions with comfort settings and device profiles.

```python
from vr_ar import VRARManager

vr = VRARManager()
session = vr.start_session(VRMode.IMMERSIVE, comfort=ComfortLevel.COMFORTABLE)
```

---

## Soundtrack

Dynamic soundtrack layers change with context.

```python
from soundtrack import SoundtrackManager

music = SoundtrackManager()
music.play(SoundtrackCategory.EXPLORATION)
```

---

## Endgame and New Game Plus

Post-game content and NG+ carry-over logic.

```python
from endgame import EndgameManager
from new_game_plus import NewGamePlusManager

endgame = EndgameManager()
ng = NewGamePlusManager()
ng.start_new_game_plus(character_id="hero_01", carry_over={"titles": True})
```

---

## Performance

Asset streaming and memory budgets for large worlds.

```python
from performance_optimizer import PerformanceOptimizer, MemoryBudget

opt = PerformanceOptimizer()
budget = MemoryBudget(max_mb=256)
opt.set_budget(budget)
```

---

## Troubleshooting

### Import Errors

Always add `src/` to your path when running scripts outside the package:

```bash
export PYTHONPATH=$PYTHONPATH:/path/to/seven-rpg/src
```

### WebSocket Connection Refused

- Confirm the multiplayer server is running and reachable.
- Check firewall rules on port `8765` (default).
- Use `host="0.0.0.0"` on the server to accept external connections.

### Slow Performance

- Reduce world size or active NPC count.
- Lower graphics effect quality (`QualityLevel.LOW`).
- Use the performance optimizer's streaming zones to load only nearby content.

### Cloud Sync Conflicts

- If a conflict is detected, the sync manager will report the conflict ID.
- Resolve by merging locally or force-pushing the remote state.

---

## Next Steps

- Read the [Installation Guide](INSTALLATION.md) if you have not yet set up the project.
- Explore `data/` to see how content is defined.
- Read `tests/` for detailed examples of every system.
- Try the example mod in `mods/example_mod/` to learn modding.
