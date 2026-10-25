---
name: seven-autonomous-repair
description: Run bounded autonomous bug-fix loops without destructive shortcuts.
---
# Seven Autonomous Repair
1. Reproduce the defect and save the exact failure evidence.
2. Identify root cause before editing; do not hide errors or weaken assertions.
3. Make a minimal patch and add a regression test.
4. Run the failing test, relevant suite, and a final diff/status review.
5. Retry only with a changed hypothesis. Maximum three materially different repair attempts before reporting a blocker.
6. Never delete databases, user data, lockfiles, or tests to make a run pass; never use destructive cleanup as a default.
7. Stop on credential exposure, production-data risk, unclear destructive impact, or need for user approval.
