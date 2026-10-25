---
name: seven-context-engineering
description: Keep agent context small, grounded, and traceable to project sources.
---
# Seven Context Engineering
1. Establish source-of-truth order: user instruction; product contract; current source/tests; architecture/ownership docs; status reports; assumptions.
2. Retrieve only files relevant to the task and follow references when needed.
3. Preserve exact identifiers, data formats, API contracts, and constraints.
4. Summarize long investigations as facts, evidence paths, decisions, open questions, and next actions.
5. Never treat generated summaries or stale reports as proof of current implementation.
6. Do not expose secrets or copy sensitive user data into logs or prompts.
