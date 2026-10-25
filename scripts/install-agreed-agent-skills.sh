#!/usr/bin/env bash
set -euo pipefail

# Installs real upstream skills locally into this repository's agent skill directory.
# Run from the repository root on a feature branch after reviewing docs/SEVEN_RPG_AGENT_SKILLS_SOURCES.md.
# No global installation is requested. This script does not merge or delete files.

if [[ ! -f "AGENTS.md" ]]; then
  echo "ERROR: Run from the Seven RPG repository root (AGENTS.md missing)." >&2
  exit 2
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "ERROR: Node.js/npm npx is required. Install it yourself, then rerun." >&2
  exit 2
fi

echo "Installing upstream Superpowers skills into the project..."
npx --yes skills add obra/superpowers --all -y

echo "Installing upstream UI UX Pro Max skills into the project..."
npx --yes skills add nextlevelbuilder/ui-ux-pro-max-skill --all -y

echo "Installing Vercel's general web design guidelines skill only (not framework-specific React/Next skills)..."
npx --yes skills add vercel-labs/agent-skills --skill web-design-guidelines -y

cat <<'EOF'

Initial upstream installs requested. This is not a claim that all agreed skills are installed.
Next mandatory steps:
1. Inspect git diff/status; ensure AGENTS.md and existing project files were not overwritten.
2. Review each installed skill's license, scripts, dependencies and file list.
3. Check whether this host actually discovers .agents/skills.
4. Run a harmless activation smoke test in the intended agent host.
5. Record installed paths, upstream commit/tag, license and test evidence in
   docs/SEVEN_RPG_SKILL_INSTALLATION_REPORT.md.
6. Add more sources only after their exact canonical repository and license are verified.
EOF
