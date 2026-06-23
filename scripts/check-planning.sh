#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_ROOT="$ROOT"
ALLOW_PLACEHOLDERS=0
missing=0
warned=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template|--allow-placeholders)
      ALLOW_PLACEHOLDERS=1
      shift
      ;;
    *)
      TARGET_ROOT="$1"
      shift
      ;;
  esac
done

PLAN_FILE="$TARGET_ROOT/docs/ref/PROJECT-PLAN.md"
SKILLS_ROOT="$TARGET_ROOT/.claude/skills"

if [[ ! -d "$SKILLS_ROOT" ]] || [[ "$(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" = "0" ]]; then
  SKILLS_ROOT="$ROOT/.claude/skills"
fi

if [[ ! -f "$PLAN_FILE" ]]; then
  echo "MISSING PLAN: $PLAN_FILE"
  exit 1
fi

required_headings=(
  "## Project Snapshot"
  "## Problem"
  "## Goal"
  "## Non-Goals"
  "## Constraints"
  "## Assumptions"
  "## Risks"
  "## Dependencies"
  "## Success Metrics"
  "## Naming Contract"
  "## File Map"
  "## Folder Boundaries"
  "## Skill Routing"
  "## Intake Verdict"
  "## Impact Map Summary"
  "## Sub-Agent Opportunities"
  "## Phase Plan"
  "## Open Questions"
  "## Later Backlog"
  "## Handoff Notes"
)

for heading in "${required_headings[@]}"; do
  if ! grep -qF "$heading" "$PLAN_FILE"; then
    echo "MISSING HEADING: ${heading#\#\# }"
    missing=1
  fi
done

if [[ $ALLOW_PLACEHOLDERS -eq 0 ]]; then
  if perl -ne '
    while (/(\.\.\.|<[^>]+>|TBD|TODO|FIXME)/g) {
      print "$.:$1\n";
      $bad = 1;
    }
    END { exit($bad ? 0 : 1) }
  ' "$PLAN_FILE" >/tmp/check-planning-placeholders.$$; then
    echo "PLACEHOLDER FOUND: $PLAN_FILE"
    cat /tmp/check-planning-placeholders.$$
    rm -f /tmp/check-planning-placeholders.$$
    missing=1
  else
    rm -f /tmp/check-planning-placeholders.$$ 2>/dev/null || true
  fi
fi

phase_count="$(grep -c '^### Phase ' "$PLAN_FILE" || true)"
if (( phase_count < 1 )); then
  echo "MISSING PHASES: $PLAN_FILE"
  missing=1
fi

if (( phase_count > 5 )); then
  echo "WARN TOO MANY PHASES: $phase_count"
  warned=1
fi

if ! awk '
function flush_phase() {
  if (!in_phase) {
    return
  }

  if (!goal) {
    print "MISSING PHASE FIELD: Goal in " phase
    bad = 1
  }
  if (!files) {
    print "MISSING PHASE FIELD: Files in " phase
    bad = 1
  }
  if (!skills) {
    print "MISSING PHASE FIELD: Skills in " phase
    bad = 1
  }
  if (!verification) {
    print "MISSING PHASE FIELD: Verification in " phase
    bad = 1
  }
  if (!docsync) {
    print "MISSING PHASE FIELD: Doc Sync in " phase
    bad = 1
  }
  if (!exitc) {
    print "MISSING PHASE FIELD: Exit Criteria in " phase
    bad = 1
  }
  if (!decision) {
    print "MISSING PHASE FIELD: Decision Gates in " phase
    bad = 1
  }
}

/^### Phase / {
  flush_phase()
  in_phase = 1
  phase = $0
  goal = files = skills = verification = docsync = exitc = decision = 0
  next
}

in_phase {
  if ($0 ~ /^Goal:/) {
    goal = 1
  } else if ($0 ~ /^Files:/) {
    files = 1
  } else if ($0 ~ /^Skills:/) {
    skills = 1
  } else if ($0 ~ /^Verification:/) {
    verification = 1
  } else if ($0 ~ /^Doc Sync:/) {
    docsync = 1
  } else if ($0 ~ /^Exit Criteria:/) {
    exitc = 1
  } else if ($0 ~ /^Decision Gates:/) {
    decision = 1
  }
}

END {
  flush_phase()
  exit bad
}
' "$PLAN_FILE"; then
  missing=1
fi

skill_section="$(
  awk '
    /^## Skill Routing$/ { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$PLAN_FILE"
)"

if [[ -z "$skill_section" ]]; then
  echo "EMPTY SECTION: Skill Routing"
  missing=1
fi

known_skills_list="$(find "$SKILLS_ROOT" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)"
routed_skills_list="$(printf '%s\n' "$skill_section" | perl -ne 'while (/`([a-z0-9-]+)`/g) { print "$1\n" }' | sort -u)"

if [[ -z "$routed_skills_list" ]]; then
  echo "EMPTY SKILL ROUTING: no backticked skill names found"
  missing=1
fi

while IFS= read -r skill_name; do
  [[ -z "$skill_name" ]] && continue
  if ! printf '%s\n' "$known_skills_list" | grep -qx "$skill_name"; then
    echo "UNKNOWN SKILL ROUTING ENTRY: $skill_name"
    missing=1
  fi
done < <(printf '%s\n' "$routed_skills_list")

file_map_section="$(
  awk '
    /^## File Map$/ { capture=1; next }
    /^## / && capture { exit }
    capture { print }
  ' "$PLAN_FILE"
)"

if [[ -z "$file_map_section" ]]; then
  echo "EMPTY SECTION: File Map"
  missing=1
fi

while IFS= read -r line; do
  [[ -z "$line" ]] && continue

  kind="$(printf '%s\n' "$line" | perl -ne 'print "$1\n" if /^\s*-\s*(create|modify|keep|existing|candidate):/i')"
  path="$(printf '%s\n' "$line" | perl -ne 'print "$1\n" if /`([^`]+)`/')"

  [[ -z "$kind" ]] && continue
  [[ -z "$path" ]] && continue

  case "$kind" in
    modify|keep|existing)
      if [[ ! -e "$TARGET_ROOT/$path" ]]; then
        echo "MISSING FILE MAP TARGET: $kind -> $path"
        missing=1
      fi
      ;;
  esac
done < <(printf '%s\n' "$file_map_section")

allowed_doc_sync_pattern='^(docs/status/[^`]+|docs/ref/[^`]+|ai-context/START-HERE\.md)$'
doc_sync_refs="$(perl -0ne '
  while (/^## Doc Sync Targets\n(.*?)(?=^## |\z)/msg) {
    while ($1 =~ /`([^`]+)`/g) {
      print "$1\n";
    }
  }
  while (/^Doc Sync:\n(.*?)(?=^(?:### Phase |## |\z))/msg) {
    while ($1 =~ /`([^`]+)`/g) {
      print "$1\n";
    }
  }
' "$PLAN_FILE" | sort -u)"

if [[ -z "$doc_sync_refs" ]]; then
  echo "MISSING DOC SYNC TARGETS: $PLAN_FILE"
  missing=1
fi

while IFS= read -r doc_path; do
  [[ -z "$doc_path" ]] && continue

  if [[ ! "$doc_path" =~ $allowed_doc_sync_pattern ]]; then
    echo "INVALID DOC SYNC TARGET: $doc_path"
    missing=1
  fi

  if [[ "$doc_path" != candidate:* ]] && [[ ! -e "$TARGET_ROOT/$doc_path" ]]; then
    echo "DOC SYNC TARGET NOT FOUND: $doc_path"
    missing=1
  fi
done < <(printf '%s\n' "$doc_sync_refs")

open_question_count="$(awk '
  /^## Open Questions$/ { capture=1; next }
  /^## / && capture { exit }
  capture && /^[[:space:]]*-[[:space:]]+/ { count++ }
  END { print count + 0 }
' "$PLAN_FILE")"

if (( open_question_count > 6 )); then
  echo "WARN MANY OPEN QUESTIONS: $open_question_count"
  warned=1
fi

for section in "Risks" "Dependencies" "Later Backlog" "Handoff Notes"; do
  count="$(awk -v target="## ${section}" '
    $0 == target { capture=1; next }
    /^## / && capture { exit }
    capture && /^[[:space:]]*-[[:space:]]+/ { count++ }
    END { print count + 0 }
  ' "$PLAN_FILE")"
  if (( count < 1 )); then
    echo "WARN THIN SECTION: $section"
    warned=1
  fi
done

if [[ $missing -ne 0 ]]; then
  echo
  echo "Planning check failed."
  exit 1
fi

if [[ $warned -ne 0 ]]; then
  echo "Planning check passed with warnings."
  exit 0
fi

echo "Planning check passed."
