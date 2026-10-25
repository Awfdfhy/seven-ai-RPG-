# Seven RPG — Upstream Skill Sources and Installation Plan

This file tracks real upstream projects separately from Seven RPG's locally authored workflow instructions. Links were checked on 25 October 2026. A listed source is **not** proof of installation; the host's installer must run and resulting files must be inspected.

## Confirmed upstream sources

| Agreed capability | Canonical source | Integration method | Scope notes |
|---|---|---|---|
| Structured engineering workflow, TDD, debugging, review, parallel agents, verification | https://github.com/obra/superpowers | `npx skills add obra/superpowers --all -y` | Use all 15 upstream skills; review host-specific installation and skill invocation. |
| UI/UX design intelligence and design-system generation | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill | `npx skills add nextlevelbuilder/ui-ux-pro-max-skill --all -y` | Upstream documents MIT for the basic repository. Keep its actual data/scripts intact; no hand-recreated substitute. |
| General agent skill standard and Vercel's official skills | https://github.com/vercel-labs/agent-skills | `npx skills add vercel-labs/agent-skills --skill web-design-guidelines -y` | Select relevant skills only; React/Next.js skills are not automatically applicable to this repository's current stack. Check repository licensing before vendoring. |
| Anthropic's public Agent Skills examples | https://github.com/anthropics/skills | Inspect repository and install only skills whose license and task relevance are verified. | Some document skills are source-available rather than open source; do not blindly copy all files. |
| Game-development studio workflows | https://github.com/toukanno/claude-code-game-studios | Inspect license, supported engine and selected workflow skills before installing. | This project should not inherit Unity/Godot/Unreal assumptions unless the actual app uses that engine. The repo identity and current license must be checked at install time. |
| Everything Claude Code agent harness | https://github.com/affaan-m/everything-claude-code | Inspect canonical repository, current install instructions, license, host support and file overlap before installing. | Includes agents/hooks/rules/MCP in addition to skills; install only relevant components and avoid replacing project safety rules. |

## Other previously discussed names — identity must be verified before installation

- Duel: treat as the agreed adversarial review workflow unless an exact canonical repository URL is supplied/verified. The local `seven-duel-review` is a project-specific implementation, not a claim that an upstream "Duel" package was installed.
- Graphify: confirm exact upstream repository and license; do not guess among similarly named projects.
- Impeccable: confirm exact source and host support before adding.
- Planning with Files: use the project-local workflow now; install an upstream package only after its canonical source/license is verified.
- Agent Skills for Context Engineering, OpenAI Skills, Android Skills, QA collections, cybersecurity collections, Matt Pocock / Addy Osmani skills, Awesome Agent Skills, GitHub Awesome Copilot, Understand Anything, Cloudflare Security Audit: these are not one interchangeable package each. Pin exact repositories and selected skills before installing; avoid bulk copying unreviewed collections.
- Do not assume a skill is compatible merely because it has a `SKILL.md`; its scripts, tools, hooks and runtime dependencies may be host- or stack-specific.

## Installation safety contract

1. Run installers only from the project root and on a feature branch.
2. Inspect the command's dry-run/options first where available.
3. Do not install global packages or modify the user's home-directory configuration as part of a repository-only change.
4. Do not overwrite `AGENTS.md`, project safety rules, package manifests or existing skills without a diff review.
5. Review each installed skill's source, license, scripts, dependencies and requested permissions.
6. Run the host's skill-list/discovery command and a harmless activation smoke test. Record the exact host/version and results.
7. Record upstream URL, resolved commit/tag, license, installed path, and any local patch in `docs/SEVEN_RPG_SKILL_INSTALLATION_REPORT.md`.
8. Installation failures must be reported; do not fabricate success.
