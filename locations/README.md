# Locations Catalog

This directory contains the Seven RPG world location catalog with descriptions and connections.

## Files

- `world_locations.json` — Master list of all locations with metadata, descriptions, and connection maps.
- `by_region/` — Location lists grouped by region for easier maintenance.

## Schema

Each location entry includes:
- `id` — Unique slug identifier.
- `name` — Display name.
- `region_id` — Region grouping key.
- `description` — Short lore description.
- `location_type` — town, wilderness, dungeon, pass, outpost, etc.
- `x`, `y` — Map coordinates.
- `danger_level` — Integer 1–10.
- `connections` — Array of `{to, distance, travel_time_hours}`.
