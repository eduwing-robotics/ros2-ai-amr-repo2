#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ROOT="${1:-$ROOT}"
PLAN_FILE="$TARGET_ROOT/docs/ref/PROJECT-PLAN.md"
STATUS_FILE="$TARGET_ROOT/docs/status/PROJECT-STATUS.md"
SKILLS_ROOT="$TARGET_ROOT/.claude/skills"

if [[ ! -d "$SKILLS_ROOT" ]] || [[ "$(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" = "0" ]]; then
  SKILLS_ROOT="$ROOT/.claude/skills"
fi

missing=0

extract_section() {
  local file="$1"
  local heading="$2"
  awk -v target="$heading" '
    $0 == target { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$file"
}

require_heading() {
  local file="$1"
  local heading="$2"
  if ! grep -qF "$heading" "$file"; then
    echo "MISSING HEADING: ${heading#\#\# } in ${file#$TARGET_ROOT/}"
    missing=1
  fi
}

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "MISSING FILE: $PLAN_FILE"
  exit 1
fi

if [[ ! -f "$STATUS_FILE" ]]; then
  echo "MISSING FILE: $STATUS_FILE"
  exit 1
fi

for heading in \
  "## Intake Verdict" \
  "## Impact Map Summary" \
  "## Sub-Agent Opportunities"
do
  require_heading "$PLAN_FILE" "$heading"
done

for heading in \
  "## Current Sub-Agent Work" \
  "## Handoff Capsule" \
  "## Evidence Status"
do
  require_heading "$STATUS_FILE" "$heading"
done

known_skills="$(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)"
skill_routing_section="$(extract_section "$PLAN_FILE" "## Skill Routing")"
file_map_section="$(extract_section "$PLAN_FILE" "## File Map")"
next_actions_section="$(extract_section "$STATUS_FILE" "## Next Actions")"
verification_section="$(extract_section "$STATUS_FILE" "## Verification Commands")"

intake_section="$(extract_section "$PLAN_FILE" "## Intake Verdict")"
for field in "verdict:" "chosen skill:" "next skill:" "sub-agent needed:"; do
  if ! printf '%s\n' "$intake_section" | grep -qi "$field"; then
    echo "MISSING INTAKE FIELD: $field"
    missing=1
  fi
done

while IFS= read -r skill_name; do
  [[ -z "$skill_name" ]] && continue
  if ! printf '%s\n' "$known_skills" | grep -qx "$skill_name"; then
    echo "UNKNOWN INTAKE SKILL: $skill_name"
    missing=1
  fi
  if ! printf '%s\n' "$skill_routing_section" | grep -q "\`$skill_name\`"; then
    echo "INTAKE SKILL NOT IN SKILL ROUTING: $skill_name"
    missing=1
  fi
done < <(printf '%s\n' "$intake_section" | perl -ne 'print "$1\n" if /chosen skill:\s*`([^`]+)`/i; print "$1\n" if /next skill:\s*`([^`]+)`/i' | sort -u)

impact_section="$(extract_section "$PLAN_FILE" "## Impact Map Summary")"
for field in "core paths:" "doc sync:" "verify matrix:"; do
  if ! printf '%s\n' "$impact_section" | grep -qi "$field"; then
    echo "MISSING IMPACT FIELD: $field"
    missing=1
  fi
done

while IFS= read -r path_ref; do
  [[ -z "$path_ref" ]] && continue
  case "$path_ref" in
    candidate:*|GET*|POST*|PUT*|PATCH*|DELETE*)
      continue
      ;;
  esac
  if ! printf '%s\n%s\n' "$file_map_section" "$impact_section" | grep -q "\`$path_ref\`"; then
    echo "IMPACT PATH NOT LINKED TO PLAN: $path_ref"
    missing=1
  fi
done < <(printf '%s\n' "$impact_section" | perl -ne 'next unless /(core paths|companion docs|doc sync):/i; while (/`([^`]+)`/g) { print "$1\n" }' | sort -u)

subagent_section="$(extract_section "$PLAN_FILE" "## Sub-Agent Opportunities")"
if ! printf '%s\n' "$subagent_section" | grep -Eq 'cheap-explorer|default-worker|strong-synthesizer'; then
  echo "MISSING SUB-AGENT MODEL HINTS"
  missing=1
fi

current_subagent_section="$(extract_section "$STATUS_FILE" "## Current Sub-Agent Work")"
if ! printf '%s\n' "$current_subagent_section" | grep -qi 'active:'; then
  echo "MISSING SUB-AGENT STATUS FIELD: active:"
  missing=1
fi
if ! printf '%s\n' "$current_subagent_section" | grep -qi 'default packet fields:'; then
  echo "MISSING SUB-AGENT STATUS FIELD: default packet fields:"
  missing=1
fi

handoff_section="$(extract_section "$STATUS_FILE" "## Handoff Capsule")"
for field in "next entrypoint:" "read first:" "blocker:" "first verify:"; do
  if ! printf '%s\n' "$handoff_section" | grep -qi "$field"; then
    echo "MISSING HANDOFF FIELD: $field"
    missing=1
  fi
done

handoff_entrypoint="$(printf '%s\n' "$handoff_section" | perl -ne 'print "$1\n" if /next entrypoint:\s*`([^`]+)`/i' | head -n 1)"
if [[ -n "$handoff_entrypoint" ]] && [[ ! -e "$TARGET_ROOT/$handoff_entrypoint" ]]; then
  echo "HANDOFF ENTRYPOINT NOT FOUND: $handoff_entrypoint"
  missing=1
fi

blocker_value="$(printf '%s\n' "$handoff_section" | perl -ne 'print "$1\n" if /blocker:\s*(.+)$/i' | head -n 1)"
blocker_value_lc="$(printf '%s' "$blocker_value" | tr '[:upper:]' '[:lower:]')"
if [[ -n "$blocker_value" && "$blocker_value_lc" != "none" ]]; then
  if [[ -z "$(printf '%s\n' "$next_actions_section" | grep '^\- \[ \]' || true)" ]]; then
    echo "BLOCKER PRESENT WITHOUT NEXT ACTIONS"
    missing=1
  fi
fi

evidence_section="$(extract_section "$STATUS_FILE" "## Evidence Status")"
for field in "executed verify:" "changed docs:" "release verdict:" "profile recommendation:" "drift verdict:"; do
  if ! printf '%s\n' "$evidence_section" | grep -qi "$field"; then
    echo "MISSING EVIDENCE FIELD: $field"
    missing=1
  fi
done

while IFS= read -r command; do
  [[ -z "$command" ]] && continue
  if ! printf '%s\n' "$verification_section" | grep -q "\`$command\`"; then
    echo "EVIDENCE VERIFY NOT IN STATUS COMMANDS: $command"
    missing=1
  fi
done < <(printf '%s\n' "$evidence_section" | perl -ne 'while (/executed verify:.*`([^`]+)`/ig) { print "$1\n" }' | sort -u)

stack_line="$(perl -ne 'print "$1\n" if /^- Stack: `([^`]+)` from `docs\/ref\/STACK-PROFILES\.md`/' "$PLAN_FILE" | head -n 1)"
profile_recommendation="$(printf '%s\n' "$evidence_section" | perl -ne 'print "$1\n" if /profile recommendation:\s*`([^`]+)`/i' | head -n 1)"
drift_verdict="$(printf '%s\n' "$evidence_section" | perl -ne 'print lc($1), "\n" if /drift verdict:\s*([a-z-]+)/i' | head -n 1)"

if [[ -n "$profile_recommendation" && -n "$stack_line" && "$profile_recommendation" != "$stack_line" ]]; then
  if [[ "$drift_verdict" == "stable" || -z "$drift_verdict" ]]; then
    echo "PROFILE RECOMMENDATION DIFFERS BUT DRIFT IS NOT ESCALATED"
    missing=1
  fi
fi

if [[ "$drift_verdict" == "reprofile-needed" ]]; then
  if ! printf '%s\n' "$evidence_section" | grep -qi 'drift note:'; then
    echo "REPROFILE-NEEDED WITHOUT DRIFT NOTE"
    missing=1
  fi
fi

if [[ $missing -ne 0 ]]; then
  echo
  echo "Agent-layer check failed."
  exit 1
fi

echo "Agent-layer check passed."
