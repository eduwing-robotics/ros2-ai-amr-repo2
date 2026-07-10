# URHYNIX aliases — auto-loaded at the end of scripts/tb3.sh
# Cross-platform (macOS + Linux). All paths derived from TB3_REPO_ROOT (set by tb3.sh).

[ -z "$TB3_REPO_ROOT" ] && return 0

# ─────────────────────────────────────────────────────────────
# Directory jumps
# ─────────────────────────────────────────────────────────────
alias urhynix='cd "$TB3_REPO_ROOT"'
alias urhynix-unity='cd "$TB3_REPO_ROOT/unity-smoke"'
alias urhynix-scripts='cd "$TB3_REPO_ROOT/scripts"'
alias urhynix-sketches='cd "$TB3_REPO_ROOT/sketches/pir_led"'
alias urhynix-docs='cd "$TB3_REPO_ROOT/docs"'

# ─────────────────────────────────────────────────────────────
# Document viewing
# ─────────────────────────────────────────────────────────────
alias urhynix-status='less "$TB3_REPO_ROOT/docs/status/PROJECT-STATUS.md"'
alias urhynix-handoff='less "$TB3_REPO_ROOT/docs/status/HANDOFF.md"'
alias urhynix-decisions='tail -200 "$TB3_REPO_ROOT/docs/status/DECISION-LOG.md"'
alias urhynix-schema='less "$TB3_REPO_ROOT/docs/ref/SCHEMA.md"'

# HTML board rebuild
alias urhynix-board='python3 "$TB3_REPO_ROOT/docs/whiteboards/build_bundle.py"'

# Git shortcuts
alias urhynix-pull='git -C "$TB3_REPO_ROOT" pull'
alias urhynix-st='git -C "$TB3_REPO_ROOT" status'
alias urhynix-log='git -C "$TB3_REPO_ROOT" log --oneline -20'

# Shell reload (source ~/.zshrc + 한 줄 검증)
reload() {
  if [ -n "$ZSH_VERSION" ]; then
    source ~/.zshrc 2>/dev/null
  else
    source ~/.bashrc 2>/dev/null
  fi
  printf "reloaded · PWD=%s · tb3-go=%s · sb-count=%s\n" \
    "${TB3_PASSWORD:+set}" \
    "$(type tb3-go 2>/dev/null | head -1 | awk '{print $4}')" \
    "$(type sb-count 2>/dev/null | head -1 | awk '{print $NF}')"
}

# ─────────────────────────────────────────────────────────────
# Supabase Management API helpers
#   SUPABASE_ACCESS_TOKEN  required (put in ~/.tb3rc)
#   SUPABASE_PROJECT_REF   defaults to current URHYNIX project
# ─────────────────────────────────────────────────────────────
: "${SUPABASE_PROJECT_REF:=ueupkrxwybuuqxflstvg}"
export SUPABASE_PROJECT_REF

sb-sql() {
  local q="$*"
  : "${SUPABASE_ACCESS_TOKEN:?set SUPABASE_ACCESS_TOKEN (sbp_... token) in ~/.tb3rc first}"
  if [ -z "$q" ]; then
    echo "usage: sb-sql \"<SQL>\"" >&2; return 2
  fi
  curl -s -X POST \
    -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg q "$q" '{query: $q}')" \
    "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" | jq .
}

alias sb-events="sb-sql \"select id, ts, event_type, severity, x, y, raw_payload->>'label' as label from public.events order by ts desc limit 10\""
alias sb-count='sb-sql "select count(*) as events_count from public.events"'
alias sb-tables="sb-sql \"select table_name from information_schema.tables where table_schema='public' order by table_name\""
alias sb-session='sb-sql "select session_id, started_at, scenario, notes from public.session_meta"'
sb-by-type() {
  sb-sql "select event_type, count(*) as n from public.events group by event_type order by n desc"
}
sb-dark() {
  sb-sql "select id, ts, severity, raw_payload->>'ldr' as ldr from public.events where event_type='dark' order by ts desc limit 5"
}
sb-pir() {
  sb-sql "select id, ts, severity, raw_payload->>'label' as label from public.events where event_type='pir' order by ts desc limit 5"
}

sb-tail() {
  # events 한 화면: 총 수 + 최근 5건
  echo "── 총 events 수 ──"
  sb-count
  echo "── 최근 5건 ──"
  sb-sql "select id, ts, event_type, severity, raw_payload->>'label' as label from public.events order by ts desc limit 5"
}

# ─────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────
urhynix-help() {
  cat <<HELP
URHYNIX aliases (loaded from scripts/aliases.sh)

Navigation
  urhynix              cd repo root ($TB3_REPO_ROOT)
  urhynix-unity        cd unity-smoke
  urhynix-scripts      cd scripts
  urhynix-sketches     cd sketches/pir_led
  urhynix-docs         cd docs

Documents
  urhynix-status       less PROJECT-STATUS.md
  urhynix-handoff      less HANDOFF.md
  urhynix-decisions    tail -200 DECISION-LOG.md
  urhynix-schema       less SCHEMA.md

Board / Git / Shell
  urhynix-board        rebuild docs/dev-plan-bundle.html
  urhynix-pull         git pull
  urhynix-st           git status
  urhynix-log          git log --oneline -20
  reload               ★ source ~/.zshrc + 환경 한 줄 검증

Supabase Management API  (needs SUPABASE_ACCESS_TOKEN in ~/.tb3rc)
  sb-sql "<SQL>"       run arbitrary SQL on $SUPABASE_PROJECT_REF
  sb-events            last 10 events rows
  sb-count             events row count
  sb-tables            list public tables
  sb-session           list session_meta rows
  sb-tail              ★ count + last 5 (한 화면 요약)
  sb-by-type           이벤트 타입별 카운트 (pir/dark/...)
  sb-dark              최근 dark(어두움) 이벤트 5건
  sb-pir               최근 pir(인체감지) 이벤트 5건

Robot (tb3.sh)
  tb3-help             robot helper menu (myip/ip/ssh/vnc/port/up/down/bridge/arduino/poweroff/unity)
HELP
}
