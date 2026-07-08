#!/usr/bin/env bash
# ip-drift-resync — DHCP robot IP 변경 시 default_robots.json(SSOT) + known_hosts 동기화.
# Usage:
#   bash resync.sh <tb3_1|tb3_2>                  # tb3-ip 자동 발견
#   bash resync.sh <tb3_1|tb3_2> 192.168.20.7      # explicit
#
# 2026-07-03: unity-smoke(SampleScene.unity/RosSmokeDashboard.cs) 타겟은 폐기된 프로토타입이라
# 실제로 아무것도 안 고쳐지고 있었음(젠지 IP 드리프트 실사고로 발견) — 현재 SSOT인
# default_robots.json으로 교체. JSON은 TextAsset이라 Unity가 자동 save-back 안 함(Scene/Script와
# 다름) — Editor kill/재시작 스텝 불필요, Play 중이면 재시작만 하면 반영(Resources.Load 캐시).

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

ROBOTS_JSON="$REPO_ROOT/unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json"
TB3SH="$REPO_ROOT/scripts/tb3.sh"

sed_inplace() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

ROBOT_ID="${1:-}"
if [[ -z "$ROBOT_ID" ]]; then
  echo "usage: resync.sh <tb3_1|tb3_2> [new_ip]" >&2; exit 1
fi

if [[ $# -ge 2 ]]; then
  NEW_IP="$2"
  echo "→ explicit IP: $NEW_IP"
else
  if [[ ! -f "$TB3SH" ]]; then
    echo "❌ missing $TB3SH (자동 발견 불가 — IP를 직접 넘기거나 robot-ip-detect-fallback 스킬 먼저 실행)" >&2; exit 1
  fi
  # shellcheck disable=SC1090
  source "$TB3SH"
  NEW_IP=$(tb3-ip 2>/dev/null) || { echo "❌ tb3-ip failed (robot offline?)" >&2; exit 1; }
  echo "→ auto-discovered IP: $NEW_IP"
fi

if [[ ! "$NEW_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "❌ invalid IP: $NEW_IP" >&2; exit 1
fi

[[ -f "$ROBOTS_JSON" ]] || { echo "❌ missing $ROBOTS_JSON" >&2; exit 1; }

# 해당 robotId 블록의 hostAddress 라인만 추출 (user@ip 형식)
OLD_LINE=$(awk -v id="\"$ROBOT_ID\"" '
  $0 ~ id { found=1 }
  found && /"hostAddress"/ { print; exit }
' "$ROBOTS_JSON")
OLD_IP=$(echo "$OLD_LINE" | grep -oE '@[0-9.]+' | tr -d '@')
USER_PART=$(echo "$OLD_LINE" | grep -oE '"[a-zA-Z0-9_]+@' | tr -d '"@')

if [[ -z "$OLD_IP" || -z "$USER_PART" ]]; then
  echo "❌ $ROBOT_ID hostAddress 파싱 실패 — default_robots.json 형식 확인" >&2; exit 1
fi

echo "  $ROBOT_ID old: $USER_PART@$OLD_IP"

if [[ "$OLD_IP" == "$NEW_IP" ]]; then
  echo "✅ already in sync ($NEW_IP) — nothing to patch"
  exit 0
fi

sed_inplace "s/\"$USER_PART@$OLD_IP\"/\"$USER_PART@$NEW_IP\"/" "$ROBOTS_JSON"
echo "→ default_robots.json patched: $USER_PART@$OLD_IP → $USER_PART@$NEW_IP"

if grep -q "^$OLD_IP " "$HOME/.ssh/known_hosts" 2>/dev/null; then
  ssh-keygen -R "$OLD_IP" >/dev/null 2>&1
  echo "→ known_hosts purged: $OLD_IP"
fi

echo ""
echo "=== 검증 ==="
grep -A8 "\"$ROBOT_ID\"" "$ROBOTS_JSON" | grep hostAddress
echo ""
echo "✅ ip-drift-resync 완료 — $ROBOT_ID 새 IP: $NEW_IP"
echo "   Unity가 Play 중이면 재시작 필요(Resources.Load 캐시) — play stop → play start"
