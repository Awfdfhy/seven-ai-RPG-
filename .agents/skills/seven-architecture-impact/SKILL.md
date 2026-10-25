---
name: seven-architecture-impact
description: Analyze architecture boundaries and change blast radius before editing.
---
# Seven Architecture Impact
1. Trace callers, data contracts, module loading, persistence and tests before changing a shared module.
2. Identify invariants and ownership boundaries; update the canonical interface rather than adding ad hoc parallel paths.
3. Prefer minimal reversible changes and explicit adapters over framework rewrites.
4. Check compatibility across duplicated or legacy entry points before assuming one file is authoritative.
5. Update docs only when behavior/interface truly changes; avoid reports that claim unverified implementation.
6. Include blast radius, migration needs and rollback strategy in the plan.
