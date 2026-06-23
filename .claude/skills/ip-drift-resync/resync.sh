#!/usr/bin/env bash
# ip-drift-resync — DHCP robot IP 변경 시 Unity Scene/Script/known_hosts 일괄 동기화
# Usage:
#   bash resync.sh             # tb3-ip 자동 발견
#   bash resync.sh 192.168.0.42  # explicit
#
# Unity Editor 자동 save back 함정 회피 — Editor 종료 → patch → (옵션) 재시작.

set -u

# repo root (이 파일 기준 3단계 상위)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

SCENE="$REPO_ROOT/unity-smoke/Assets/Scenes/SampleScene.unity"
SCRIPT="$REPO_ROOT/unity-smoke/Assets/Scripts/RosSmokeDashboard.cs"
TB3SH="$REPO_ROOT/scripts/tb3.sh"

# OS-portable sed in-place
sed_inplace() {
  if [[ "$(uname -s)" == "Darwin" ]]; then
    sed -i '' "$@"
  else
    sed -i "$@"
  fi
}

# 1) 새 IP 결정
if [[ $# -ge 1 ]]; then
  NEW_IP="$1"
  echo "→ explicit IP: $NEW_IP"
else
  # tb3-ip 호출 (helper 필요)
  if [[ ! -f "$TB3SH" ]]; then
    echo "❌ missing $TB3SH" >&2; exit 1
  fi
  # shellcheck disable=SC1090
  source "$TB3SH"
  NEW_IP=$(tb3-ip 2>/dev/null) || { echo "❌ tb3-ip failed (robot offline?)" >&2; exit 1; }
  echo "→ auto-discovered IP: $NEW_IP"
fi

# IP 형식 검증
if [[ ! "$NEW_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "❌ invalid IP: $NEW_IP" >&2; exit 1
fi

# 2) 현재 Scene/Script에서 옛 IP 추출
[[ -f "$SCENE" ]] || { echo "❌ missing $SCENE" >&2; exit 1; }
[[ -f "$SCRIPT" ]] || { echo "❌ missing $SCRIPT" >&2; exit 1; }

OLD_SCENE_IP=$(grep -oE 'rosIP: [0-9.]+' "$SCENE" | awk '{print $2}' | head -1)
OLD_SCRIPT_IP=$(grep -oE 'rosIP = "[0-9.]+"' "$SCRIPT" | grep -oE '[0-9.]+' | head -1)

echo "  Scene  old IP: $OLD_SCENE_IP"
echo "  Script old IP: $OLD_SCRIPT_IP"

if [[ "$OLD_SCENE_IP" == "$NEW_IP" && "$OLD_SCRIPT_IP" == "$NEW_IP" ]]; then
  echo "✅ already in sync ($NEW_IP) — nothing to patch"
  exit 0
fi

# 3) Unity Editor 종료 (자동 save back 함정 회피)
if pgrep -f "Unity.app/Contents/MacOS/Unity" >/dev/null 2>&1; then
  echo "→ killing Unity Editor (자동 save back 함정 회피)..."
  pkill -f "Unity.app/Contents/MacOS/Unity"
  sleep 3
  if pgrep -f "Unity.app/Contents/MacOS/Unity" >/dev/null 2>&1; then
    echo "⚠️ Unity still running — manual kill required" >&2; exit 2
  fi
  echo "  Unity killed ✅"
else
  echo "  Unity not running — skipping"
fi

# 4) sed 일괄 patch
if [[ -n "$OLD_SCENE_IP" && "$OLD_SCENE_IP" != "$NEW_IP" ]]; then
  sed_inplace "s/rosIP: $OLD_SCENE_IP/rosIP: $NEW_IP/" "$SCENE"
  echo "→ Scene patched: $OLD_SCENE_IP → $NEW_IP"
fi
if [[ -n "$OLD_SCRIPT_IP" && "$OLD_SCRIPT_IP" != "$NEW_IP" ]]; then
  sed_inplace "s|rosIP = \"$OLD_SCRIPT_IP\"|rosIP = \"$NEW_IP\"|" "$SCRIPT"
  echo "→ Script patched: $OLD_SCRIPT_IP → $NEW_IP"
fi

# 5) known_hosts 정리 (옛 IP만, 새 IP는 그대로 두고 다음 ssh accept-new로 추가)
for old in "$OLD_SCENE_IP" "$OLD_SCRIPT_IP"; do
  [[ -z "$old" || "$old" == "$NEW_IP" ]] && continue
  if grep -q "^$old " "$HOME/.ssh/known_hosts" 2>/dev/null; then
    ssh-keygen -R "$old" >/dev/null 2>&1
    echo "→ known_hosts purged: $old"
  fi
done

# 6) 검증 출력
echo ""
echo "=== 검증 ==="
grep -nE "rosIP" "$SCENE" "$SCRIPT" | head -4
echo ""
echo "✅ ip-drift-resync 완료 — 새 IP: $NEW_IP"
echo "   다음 단계: tb3-unity (Unity 재시작) → 30s 후 ros_tcp_endpoint 로그에서 새 IP 연결 확인"
