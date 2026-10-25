---
name: seven-agent-duel
description: Run an evidence-led adversarial review between the primary coding agent and a separately invoked available agent/subagent. Use for high-risk Seven RPG changes, architecture decisions, data migrations, security-sensitive work, and release gates.
---

# Seven Agent Duel — Agent vs Agent

## Purpose
Challenge the primary agent's proposed change using a genuinely separate agent invocation when the current harness supports one. Do not call OpenAI API or assume any specific vendor/model. Select an available reviewer agent/model through the host's documented agent or subagent mechanism.

## Protocol
1. Prepare a compact review packet: user goal, relevant plan/acceptance criteria, changed files or proposed design, test evidence, and constraints.
2. Ask the independent reviewer to look for concrete counterexamples, contract violations, regressions, security/privacy issues, data-loss risks, Android/mobile/RTL problems, and missing tests. Give it the specification and diff, not the primary agent's private reasoning.
3. Require each finding to include severity (critical/high/medium/low), exact file/line or reproducible scenario, evidence, impact, and a minimal fix. The reviewer must distinguish verified defects from hypotheses.
4. The primary agent must address each finding: fix it, rebut it with evidence, or mark it unresolved. Never dismiss a finding solely because the primary agent disagrees.
5. For critical/high findings, request a second independent review after fixes when available. Stop release recommendations while critical/high findings remain unresolved.
6. Report review rounds, agent/model identity only when actually known, findings and disposition, tests actually run, skipped checks, and unresolved uncertainty.

## Fallbacks
- If the host cannot launch a separate agent, say that a true agent-vs-agent duel was not run. Offer a clearly labeled single-agent adversarial review or manual review packet; never pretend it was an independent agent.
- If no reviewer model is configured, ask the host to select an available agent/model rather than silently switching to a paid API.
- Do not send secrets or unnecessary private project data to an external provider. Respect the host's permissions and repository policy.

## Seven RPG guardrails
- Read `docs/SEVEN_RPG_MASTER_PLAN_AR.md` and relevant acceptance criteria first.
- Preserve Seven RPG as an independent RPG application; do not broaden it into a general assistant/productivity suite.
- Do not delete user data, change persistent data formats, alter credentials, force-push, or merge into `main` without explicit authorization.
- Do not claim tests, builds, screenshots, or runtime checks passed unless the current session has direct evidence.
