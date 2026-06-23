#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "AGENTS.md"
  "AGENT.md"
  "CLAUDE.md"
  "ai-context/START-HERE.md"
  "docs/status/PROJECT-STATUS.md"
  "docs/status/DECISION-LOG.md"
  "docs/ref/ARCHITECTURE.md"
  "docs/ref/PRD.md"
  "docs/ref/PROJECT-PLAN.md"
  "docs/ref/STACK-PROFILES.md"
  "scripts/check-agent-layer.sh"
  "scripts/check-doc-consistency.sh"
  "scripts/check-planning.sh"
  "src/AGENTS.md"
  "apps/AGENTS.md"
  "backend/AGENTS.md"
)

missing=0
for rel in "${required_files[@]}"; do
  if [[ ! -f "$ROOT/$rel" ]]; then
    echo "MISSING: $rel"
    missing=1
  fi
done

if [[ $missing -ne 0 ]]; then
  echo "Project scaffold check failed."
  exit 1
fi

bash "$ROOT/scripts/check-planning.sh"
bash "$ROOT/scripts/check-doc-consistency.sh"
bash "$ROOT/scripts/check-agent-layer.sh"

echo "Project scaffold check passed."
