# Agent Duel and Fable-style Skills — Source Notes

## Fable 5 community skills
Source: https://github.com/kpab/claude-fable-5-skills
The upstream project declares an MIT license. These are unofficial community skills, not official Anthropic products. Model-specific behavior claims may not apply to other models.

Intended skills: skill-refactorer, act-when-ready, effort-calibrator, no-gold-plating, grounded-progress, scope-guard, subagent-orchestration, markdown-memory, autonomous-continuation, regrounding-summary.

## Seven Agent Duel
`.agents/skills/seven-agent-duel/SKILL.md` is a Seven RPG-specific agent-versus-agent adaptation. It replaces the original Duel skill's OpenAI API critic with a separate host-provided agent/subagent. It does not include the upstream Duel code and does not make an agent available when the host has no multi-agent capability. This skill itself does not require an OpenAI API key.

## Safety and verification
Files in the repository do not prove the host has discovered or activated them. Do not install global hooks, change host configuration, or invoke paid APIs as part of this change. Validate using the target host's documented skill discovery and a non-destructive smoke test. Record host, versions, agent selection, test output, and limitations in `docs/SEVEN_RPG_SKILL_INSTALLATION_REPORT.md`.
