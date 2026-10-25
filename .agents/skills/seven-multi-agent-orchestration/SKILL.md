---
name: seven-multi-agent-orchestration
description: Delegate independent Seven RPG work safely across specialist agents.
---
# Seven Multi-Agent Orchestration
1. Assign one owner per file/domain; define inputs, outputs, paths, acceptance criteria, and prohibited edits.
2. Parallelize only tasks with low overlapping write sets. Keep shared interfaces owned by an integrator.
3. Require agents to return changed paths, commit/diff identifiers, tests run, results, and unresolved risks.
4. Treat agent output as untrusted until inspected; independently verify code and test evidence.
5. Integrate sequentially, resolve contract conflicts centrally, and run cross-domain tests.
6. Cap retries and parallelism; on repeated failure, isolate the cause and ask for a decision instead of spinning.
7. No agent merges to main, deletes user data, or changes secrets without explicit approval.
