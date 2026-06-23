#!/usr/bin/env bash
# secret-scan/scan.sh — URHYNIX 시크릿 노출 점검
# Usage: bash .claude/skills/secret-scan/scan.sh [--save]

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

SAVE=0
[[ "${1:-}" == "--save" ]] && SAVE=1

PATTERNS='(xox[baprs]-[0-9a-zA-Z-]{10,}|sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35}|ghp_[a-zA-Z0-9]{36}|eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+|supabase\.co.*service_role|postgres://[^@]+:[^@]+@|bot[0-9]+:[A-Za-z0-9_-]{35,})'
EXCLUDE='\.env\.example|node_modules|\.lock$|unity-src/Library|unity-src/Temp|docs/_archived-fr5|\.claude/skills/secret-scan/'

TODAY="$(date +%F)"
SCANNED=$(git ls-files | wc -l | tr -d ' ')

HITS=$(git ls-files 2>/dev/null \
  | xargs grep -nE "$PATTERNS" 2>/dev/null \
  | grep -vE "$EXCLUDE" || true)

echo "🔍 secret-scan 결과 ($TODAY)"
echo "스캔: $SCANNED files"

if [[ -z "$HITS" ]]; then
  echo "발견: 0건 ✅"
  exit 0
fi

COUNT=$(printf '%s\n' "$HITS" | wc -l | tr -d ' ')

echo "발견: $COUNT건 ⚠️"
echo ""
printf '%s\n' "$HITS" | awk -F: '{
  # 매치를 마스킹: 앞 4 + *** + 뒤 4
  match($0, /[A-Za-z0-9_/+-]{12,}/)
  if (RSTART > 0) {
    token = substr($0, RSTART, RLENGTH)
    masked = substr(token, 1, 4) "***" substr(token, length(token)-3)
    printf "  %s:%s  (%s)\n", $1, $2, masked
  } else {
    print "  " $0
  }
}'

echo ""
echo "→ .gitignore 추가 또는 환경변수로 분리 필요"

if [[ "$SAVE" -eq 1 ]]; then
  OUT="docs/status/SECRET-SCAN-$TODAY.md"
  {
    echo "# Secret Scan — $TODAY"
    echo ""
    echo "- 스캔: $SCANNED files"
    echo "- 발견: $COUNT건"
    echo ""
    echo '```'
    printf '%s\n' "$HITS"
    echo '```'
  } > "$OUT"
  echo "→ 저장: $OUT"
fi

exit 1
