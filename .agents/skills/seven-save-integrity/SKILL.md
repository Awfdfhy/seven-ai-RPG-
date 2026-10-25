---
name: seven-save-integrity
description: Protect local saves, world state, chat history and backward compatibility.
---
# Seven Save Integrity
1. Inventory existing storage keys, schema versions, readers/writers, and migration behavior before changing persistence.
2. Keep old saves readable; use explicit versioned migrations with backups or rollback where appropriate.
3. Validate imports and size limits before mutation; require confirmation before replacing user worlds.
4. Make writes atomic where feasible; reject corrupt/partial payloads rather than silently replacing them with empty state.
5. Preserve provenance and enough diagnostics to investigate persisted mutations without leaking private content.
6. Test save, force-stop/reopen, reload, duplicate IDs, malformed input, quota/full-storage, and rollback.
7. Never clear storage or migrate destructively just to simplify implementation.
