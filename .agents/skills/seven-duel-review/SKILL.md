---
name: seven-duel-review
description: Adversarial independent review of a proposed plan, diff, or release claim.
---
# Seven Duel Review
Use after planning or implementation and before high-risk integration.
1. Review as a skeptical independent engineer; do not simply affirm the author.
2. Search for contract violations, hidden assumptions, regression paths, data loss, missing tests, accessibility and mobile failures.
3. Separate confirmed defects, plausible risks, and preferences.
4. Give each finding severity, evidence/path, reproduction or reasoning, and a minimal fix.
5. The implementer must respond to each finding with evidence; unresolved high-severity findings block completion.
6. Avoid changing files during review unless explicitly assigned to fix them.
