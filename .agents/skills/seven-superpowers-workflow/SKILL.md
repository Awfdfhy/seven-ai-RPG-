---
name: seven-superpowers-workflow
description: Apply a disciplined design-first implementation, test, review, and completion loop.
---
# Seven Superpowers Workflow
1. Understand the request and inspect existing code/tests before proposing edits.
2. For non-trivial work, state the design and edge cases before implementation.
3. Implement the smallest change that satisfies the acceptance criteria.
4. Write or update a failing regression test first when practical; verify it fails for the expected reason.
5. Run focused tests, then relevant integration/full checks.
6. Review the diff for accidental scope expansion, compatibility breaks, security issues, and dead code.
7. Report exact commands/results and unresolved risks. Never invent output or imply a test ran when it did not.
