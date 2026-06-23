#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ROOT="$ROOT"
missing=0
warned=0

if [[ $# -gt 0 ]]; then
  TARGET_ROOT="$1"
fi

PRD_FILE="$TARGET_ROOT/docs/ref/PRD.md"
PLAN_FILE="$TARGET_ROOT/docs/ref/PROJECT-PLAN.md"
ARCH_FILE="$TARGET_ROOT/docs/ref/ARCHITECTURE.md"
STATUS_FILE="$TARGET_ROOT/docs/status/PROJECT-STATUS.md"
STACK_FILE="$TARGET_ROOT/docs/ref/STACK-PROFILES.md"
KNOWN_SKILLS_DIR="$TARGET_ROOT/.claude/skills"

if [[ ! -d "$KNOWN_SKILLS_DIR" ]] || [[ "$(find "$KNOWN_SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" = "0" ]]; then
  KNOWN_SKILLS_DIR="$ROOT/.claude/skills"
fi

section_has_heading() {
  local file="$1"
  local heading="$2"
  grep -qF "$heading" "$file"
}

section_item_count() {
  local file="$1"
  local heading="$2"
  awk -v target="$heading" '
    $0 == target { capture=1; next }
    /^## / && capture { exit }
    capture && /^[[:space:]]*-[[:space:]]+/ { count++ }
    END { print count + 0 }
  ' "$file"
}

extract_section() {
  local file="$1"
  local heading="$2"
  awk -v target="$heading" '
    $0 == target { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$file"
}

for file in "$PRD_FILE" "$PLAN_FILE" "$ARCH_FILE" "$STATUS_FILE" "$STACK_FILE"; do
  if [[ ! -f "$file" ]]; then
    echo "MISSING DOC: $file"
    missing=1
  fi
done

if [[ $missing -ne 0 ]]; then
  echo
  echo "Doc consistency check failed."
  exit 1
fi

for heading in "## Problem" "## Goal" "## Users" "## Scope" "## Non-Goals" "## Success Metrics"; do
  if ! section_has_heading "$PRD_FILE" "$heading"; then
    echo "MISSING PRD HEADING: ${heading#\#\# }"
    missing=1
  fi
done

for heading in "## System Overview" "## Layers" "## Boundaries"; do
  if ! section_has_heading "$ARCH_FILE" "$heading"; then
    echo "MISSING ARCHITECTURE HEADING: ${heading#\#\# }"
    missing=1
  fi
done

for heading in "## Current Phase" "## Active Tracks" "## Verification Commands" "## Next Actions"; do
  if ! section_has_heading "$STATUS_FILE" "$heading"; then
    echo "MISSING STATUS HEADING: ${heading#\#\# }"
    missing=1
  fi
done

for heading in "## Problem" "## Goal" "## Scope" "## Non-Goals" "## Success Metrics"; do
  if (( "$(section_item_count "$PRD_FILE" "$heading")" < 1 )); then
    echo "THIN PRD SECTION: ${heading#\#\# }"
    missing=1
  fi
done

for heading in "## System Overview" "## Boundaries"; do
  if (( "$(extract_section "$ARCH_FILE" "$heading" | awk 'NF {count++} END {print count+0}')" < 1 )); then
    echo "THIN ARCHITECTURE SECTION: ${heading#\#\# }"
    missing=1
  fi
done

layers_count="$(extract_section "$ARCH_FILE" "## Layers" | awk '/^[[:space:]]*[0-9]+\./ {count++} END {print count+0}')"
if (( layers_count < 3 )); then
  echo "THIN ARCHITECTURE LAYERS: need at least 3 layers"
  missing=1
fi

status_cmd_count="$(extract_section "$STATUS_FILE" "## Verification Commands" | awk '/^[[:space:]]*-[[:space:]]+`/ {count++} END {print count+0}')"
if (( status_cmd_count < 1 )); then
  echo "THIN STATUS SECTION: Verification Commands"
  missing=1
fi

current_phase="$(extract_section "$STATUS_FILE" "## Current Phase" | awk '/^[[:space:]]*-[[:space:]]+/ {sub(/^[[:space:]]*-[[:space:]]+/, "", $0); print; exit}')"
if [[ -z "$current_phase" ]]; then
  echo "EMPTY STATUS CURRENT PHASE"
  missing=1
fi

phase_ids="$(grep '^### Phase ' "$PLAN_FILE" | perl -ne 'print "$1\n" if /(Phase [0-9]+)/')"
if [[ -n "$current_phase" && "$current_phase" != "bootstrapping" ]]; then
  phase_match=0
  while IFS= read -r phase_id; do
    [[ -z "$phase_id" ]] && continue
    if [[ "$current_phase" == *"$phase_id"* ]]; then
      phase_match=1
      break
    fi
  done < <(printf '%s\n' "$phase_ids")
  if [[ $phase_match -eq 0 ]]; then
    echo "STATUS PHASE NOT IN PLAN: $current_phase"
    missing=1
  fi
fi

file_map_section="$(extract_section "$PLAN_FILE" "## File Map")"
for expected_path in "docs/ref/PRD.md" "docs/status/PROJECT-STATUS.md"; do
  if ! printf '%s\n' "$file_map_section" | grep -q "$expected_path"; then
    echo "PLAN FILE MAP MISSING CORE DOC: $expected_path"
    missing=1
  fi
done

doc_sync_section="$(perl -0ne '
  while (/^## Doc Sync Targets\n(.*?)(?=^## |\z)/msg) { print $1 }
  while (/^Doc Sync:\n(.*?)(?=^(?:### Phase |## |\z))/msg) { print $1 }
' "$PLAN_FILE")"
for expected_path in "docs/ref/PRD.md" "docs/status/PROJECT-STATUS.md"; do
  if ! printf '%s\n' "$doc_sync_section" | grep -q "$expected_path"; then
    echo "PLAN DOC SYNC MISSING CORE DOC: $expected_path"
    missing=1
  fi
done

repo_boundary_line="$(grep '^- Repo boundary:' "$PLAN_FILE" || true)"
arch_boundaries="$(extract_section "$ARCH_FILE" "## Boundaries")"
repo_boundary_tokens="$(printf '%s\n' "$repo_boundary_line" | perl -ne 'while (/`([^`]+)`/g) { print "$1\n" }')"
while IFS= read -r token; do
  [[ -z "$token" ]] && continue
  if ! printf '%s\n' "$arch_boundaries" | grep -qF "\`$token\`"; then
    echo "ARCHITECTURE BOUNDARIES MISSING TOKEN: $token"
    missing=1
  fi
done < <(printf '%s\n' "$repo_boundary_tokens")

stack_line="$(grep '^- Stack:' "$PLAN_FILE" || true)"
if [[ -z "$stack_line" ]]; then
  echo "PLAN SNAPSHOT MISSING STACK LINE"
  missing=1
fi

stack_profile_name="$(printf '%s\n' "$stack_line" | perl -ne 'print "$1\n" if /- Stack: `([^`]+)`/')"
if [[ -n "$stack_profile_name" ]]; then
  if ! grep -qxF "## $stack_profile_name" "$STACK_FILE"; then
    echo "UNKNOWN STACK PROFILE IN PLAN: $stack_profile_name"
    missing=1
  fi
fi

profile_verify_section="$(
  awk -v profile="$stack_profile_name" '
    $0 == "## " profile { in_profile=1; next }
    /^## / && in_profile { exit }
    in_profile && $0 == "- Suggested verify:" { capture=1; next }
    in_profile && /^- [^:]+:$/ && capture { exit }
    capture { print }
  ' "$STACK_FILE" | sed 's/^  - /- /'
)"

status_commands="$(extract_section "$STATUS_FILE" "## Verification Commands" | perl -ne 'while (/`([^`]+)`/g) { print "$1\n" }')"
while IFS= read -r cmd; do
  [[ -z "$cmd" ]] && continue
  if [[ -n "$stack_profile_name" ]]; then
    if ! printf '%s\n' "$profile_verify_section" | grep -qF "\`$cmd\`" && ! grep -qF "\`$cmd\`" "$PLAN_FILE"; then
      echo "STATUS VERIFY NOT REFERENCED IN PLAN OR STACK PROFILE: $cmd"
      missing=1
    fi
  else
    if ! grep -qF "\`$cmd\`" "$PLAN_FILE"; then
      echo "STATUS VERIFY NOT REFERENCED IN PLAN: $cmd"
      missing=1
    fi
  fi
done < <(printf '%s\n' "$status_commands")

profile_boundaries="$(
  awk -v profile="$stack_profile_name" '
    $0 == "## " profile { in_profile=1; next }
    /^## / && in_profile { exit }
    in_profile && $0 == "- Suggested boundaries:" { capture=1; next }
    in_profile && /^- [^:]+:$/ && capture { exit }
    capture { print }
  ' "$STACK_FILE" | sed 's/^  - //' | tr -d '`'
)"

if [[ -n "$stack_profile_name" ]]; then
  while IFS= read -r boundary; do
    [[ -z "$boundary" ]] && continue
    if ! printf '%s\n' "$repo_boundary_tokens" | grep -qxF "$boundary"; then
      echo "PLAN REPO BOUNDARY MISSING PROFILE TOKEN: $boundary"
      missing=1
    fi
    if ! printf '%s\n' "$arch_boundaries" | grep -qF "\`$boundary\`"; then
      echo "ARCHITECTURE BOUNDARIES MISSING PROFILE TOKEN: $boundary"
      missing=1
    fi
  done < <(printf '%s\n' "$profile_boundaries")
fi

plan_contracts="$(extract_section "$PLAN_FILE" "## Naming Contract" | perl -ne 'print "$1\n" if /route:\s*`([^`]+)`/; print "$1\n" if /table\/schema:\s*`([^`]+)`/; print "$1\n" if /env:\s*`([^`]+)`/')"
arch_contracts="$(extract_section "$ARCH_FILE" "## Key Contracts")"
prd_constraints="$(extract_section "$PRD_FILE" "## Constraints")"

while IFS= read -r token; do
  [[ -z "$token" ]] && continue
  if ! printf '%s\n' "$arch_contracts" | grep -qF "$token"; then
    echo "ARCHITECTURE MISSING CONTRACT TOKEN: $token"
    missing=1
  fi

  case "$token" in
    GET*|POST*|PUT*|PATCH*|DELETE*|NEXT_PUBLIC_*|SUPABASE_*|SERVICE_*|QUEUE_*|ROBOT_*|UNITY_*|*_*)
      if ! printf '%s\n%s\n' "$arch_contracts" "$prd_constraints" | grep -qF "$token"; then
        echo "DOCS MISSING CONTRACT TOKEN: $token"
        missing=1
      fi
      ;;
  esac
done < <(printf '%s\n' "$plan_contracts")

intake_section="$(extract_section "$PLAN_FILE" "## Intake Verdict")"
intake_skill="$(printf '%s\n' "$intake_section" | perl -ne 'print "$1\n" if /chosen skill:\s*`([^`]+)`/i' | head -n 1)"
next_skill="$(printf '%s\n' "$intake_section" | perl -ne 'print "$1\n" if /next skill:\s*`([^`]+)`/i' | head -n 1)"
skill_routing_section="$(extract_section "$PLAN_FILE" "## Skill Routing")"

for skill_name in "$intake_skill" "$next_skill"; do
  [[ -z "$skill_name" ]] && continue
  if [[ ! -d "$KNOWN_SKILLS_DIR/$skill_name" ]]; then
    echo "INTAKE REFERENCES UNKNOWN SKILL: $skill_name"
    missing=1
  fi
  if ! printf '%s\n' "$skill_routing_section" | grep -q "\`$skill_name\`"; then
    echo "INTAKE SKILL NOT IN SKILL ROUTING: $skill_name"
    missing=1
  fi
done

impact_section="$(extract_section "$PLAN_FILE" "## Impact Map Summary")"
while IFS= read -r impact_path; do
  [[ -z "$impact_path" ]] && continue
  case "$impact_path" in
    candidate:*|GET*|POST*|PUT*|PATCH*|DELETE*)
      continue
      ;;
  esac
  if ! printf '%s\n%s\n' "$file_map_section" "$doc_sync_section" | grep -qF "$impact_path"; then
    echo "IMPACT MAP PATH NOT TIED TO FILE MAP OR DOC SYNC: $impact_path"
    missing=1
  fi
done < <(printf '%s\n' "$impact_section" | perl -ne 'next unless /(core paths|companion docs|doc sync):/i; while (/`([^`]+)`/g) { print "$1\n" }' | sort -u)

handoff_section="$(extract_section "$STATUS_FILE" "## Handoff Capsule")"
blocker_value="$(printf '%s\n' "$handoff_section" | perl -ne 'print "$1\n" if /blocker:\s*(.+)$/i' | head -n 1)"
blocker_value_lc="$(printf '%s' "$blocker_value" | tr '[:upper:]' '[:lower:]')"
if [[ -n "$blocker_value" && "$blocker_value_lc" != "none" ]]; then
  next_actions_items="$(extract_section "$STATUS_FILE" "## Next Actions" | grep '^\- \[ \]' || true)"
  if [[ -z "$next_actions_items" ]]; then
    echo "HANDOFF BLOCKER WITHOUT NEXT ACTIONS"
    missing=1
  fi
fi

evidence_section="$(extract_section "$STATUS_FILE" "## Evidence Status")"
profile_recommendation="$(printf '%s\n' "$evidence_section" | perl -ne 'print "$1\n" if /profile recommendation:\s*`([^`]+)`/i' | head -n 1)"
drift_verdict="$(printf '%s\n' "$evidence_section" | perl -ne 'print lc($1), "\n" if /drift verdict:\s*([a-z-]+)/i' | head -n 1)"
drift_note="$(printf '%s\n' "$evidence_section" | perl -ne 'print "$1\n" if /drift note:\s*(.+)$/i' | head -n 1)"
status_verify_section="$(extract_section "$STATUS_FILE" "## Verification Commands")"

while IFS= read -r evidence_verify; do
  [[ -z "$evidence_verify" ]] && continue
  if ! printf '%s\n' "$status_verify_section" | grep -q "\`$evidence_verify\`"; then
    echo "EVIDENCE VERIFY COMMAND MISSING FROM STATUS: $evidence_verify"
    missing=1
  fi
done < <(printf '%s\n' "$evidence_section" | perl -ne 'while (/executed verify:.*`([^`]+)`/ig) { print "$1\n" }')

if [[ -n "$profile_recommendation" && -n "$stack_profile_name" && "$profile_recommendation" != "$stack_profile_name" ]]; then
  if [[ "$drift_verdict" == "stable" || -z "$drift_verdict" ]]; then
    echo "PROFILE RECOMMENDATION DIFFERS FROM STACK WITHOUT DRIFT ESCALATION"
    missing=1
  fi
fi

if [[ "$drift_verdict" == "reprofile-needed" && -z "$drift_note" ]]; then
  echo "REPROFILE-NEEDED WITHOUT DRIFT NOTE"
  missing=1
fi

next_actions_count="$(extract_section "$STATUS_FILE" "## Next Actions" | awk '/^[[:space:]]*-[[:space:]]*\[ \]/ {count++} END {print count+0}')"
if (( next_actions_count < 1 )); then
  echo "THIN STATUS SECTION: Next Actions"
  warned=1
fi

if [[ $missing -ne 0 ]]; then
  echo
  echo "Doc consistency check failed."
  exit 1
fi

if [[ $warned -ne 0 ]]; then
  echo "Doc consistency check passed with warnings."
  exit 0
fi

echo "Doc consistency check passed."
