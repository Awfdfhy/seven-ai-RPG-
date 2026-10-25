# Seven RPG Agent Skills

## Canonical project plan
Read [`docs/SEVEN_RPG_MASTER_PLAN_AR.md`](../../docs/SEVEN_RPG_MASTER_PLAN_AR.md) before planning or executing work. It is the full development blueprint, not this skill index.

## Two separate layers
1. **Project-specific workflows:** the local `seven-*` skills below and `.agents/skills/SEVEN_RPG_SKILL_PACK.md`. These are authored for Seven RPG and are not claimed to be upstream copies.
2. **Real upstream skills:** use `docs/SEVEN_RPG_AGENT_SKILLS_SOURCES.md` for canonical repositories, compatibility notes and install status. Run `scripts/install-agreed-agent-skills.sh` from the project root on a feature branch to request selected upstream installs. Inspect the resulting diff and host discovery; do not claim installation until verified.

## Local project-specific workflows
- `seven-planning`: planning, task decomposition and acceptance criteria.
- `seven-superpowers-workflow`: disciplined design-first implementation, tests and review.
- `seven-duel-review`: adversarial independent review.
- `seven-context-engineering`: source hierarchy and bounded context.
- `seven-multi-agent-orchestration`: safe delegation and integration.
- `seven-autonomous-repair`: bounded bug-fix loops.
- `seven-testing-qa`: regression, integration and CI validation.
- `seven-rpg-canon-integrity`: canon, character knowledge, agency and continuity.
- `seven-save-integrity`: persistence, migrations and corruption prevention.
- `seven-ui-ux-pro-max`: mobile-first design quality.
- `seven-rtl-arabic-qa`: Arabic RTL and bidirectional layout.
- `seven-android-release-gates`: Android/API/SAF and release evidence.
- `seven-security-audit`: secrets, permissions, dependencies and input safety.
- `seven-model-routing`: provider fallback, capabilities, rate limits and secrets.
- `seven-evals-observability`: repeatable evaluations and truthful diagnostics.
- `seven-architecture-impact`: architecture boundaries and blast-radius analysis.
- `seven-research-source-check`: authoritative research, freshness and licenses.
- `seven-performance-efficiency`: measured mobile performance.
- `seven-accessibility-qa`: keyboard, contrast, reduced motion and touch targets.
- `seven-game-studio`: RPG systems, narrative loops and player agency.
- `seven-files-planning`: durable plans and decision logs.
- `seven-visual-reference`: screenshot inventory and visual comparison.
- `seven-vercel-web-quality`: stack-compatible web runtime and responsive quality.
- `seven-github-workflow`: branch hygiene, PR review and CI evidence.
- `seven-openai-agent-patterns`: tool-use verification, handoffs and approvals.
- `seven-android-security`: storage, exported components and Android permissions.

## Safety and verification
A `SKILL.md` file in Git proves only that instructions exist in the repository. It does not prove that OpenCode, Claude Code, Hermes or another host discovered, loaded or executed the skill. Record host/version, installed path, upstream revision/license and a harmless activation test in `docs/SEVEN_RPG_SKILL_INSTALLATION_REPORT.md` before reporting host-level installation complete.
