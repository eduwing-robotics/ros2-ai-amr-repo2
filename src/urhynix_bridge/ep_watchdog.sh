#!/bin/bash
# ep_watchdog.sh — 젠지·티원 ros_tcp_endpoint(default_server_endpoint, TCP 10000)가 죽으면 자동 재기동(Mac에서 실행).
#   멀티 endpoint 경로 전제: 두 로봇이 각자 endpoint를 띄움(_pose_ep_up.sh <id> yes). Unity Play/Stop·wifi로
#   endpoint가 자주 죽는 운영 함정 대응 — 죽은 쪽만 골라 _pose_ep_up.sh로 복구한다.
# 사용: bash scripts/ep_watchdog.sh [T1_SSH] [GENJI_SSH] [INTERVAL_SEC]   (IP drift 시 인자로 덮어쓰기, Ctrl-C 종료)
set -u
# ssh alias 우선(~/.ssh/config: t1→티원, g1→젠지). alias가 user+HostName을 한 곳에서 관리 → IP drift 무관.
T1=${1:-t1}
GENJI=${2:-g1}
INT=${3:-15}
D="$(cd "$(dirname "$0")" && pwd)"
SSH="ssh -o ConnectTimeout=12 -o ControlMaster=no -o BatchMode=yes"

host_of() { case "$1" in tb3_1) echo "$T1";; tb3_2) echo "$GENJI";; esac; }

# 런처+의존 스크립트 보장(scp hang 시 stdin 전송 fallback) 후 endpoint 재기동
restart_ep() {
  id="$1"; h="$(host_of "$id")"
  echo "[$(date +%H:%M:%S)] $id endpoint DOWN → 재기동 ($h)"
  scp -o ConnectTimeout=10 "$D/_pose_ep_up.sh" "$D/robot_pose_publisher.py" "$h":/tmp/ 2>/dev/null \
    || { $SSH "$h" 'cat > /tmp/_pose_ep_up.sh'        < "$D/_pose_ep_up.sh"; \
         $SSH "$h" 'cat > /tmp/robot_pose_publisher.py' < "$D/robot_pose_publisher.py"; }
  $SSH "$h" "bash /tmp/_pose_ep_up.sh $id yes" 2>&1 | tail -2
}

echo "== ep_watchdog 시작 (interval=${INT}s, Ctrl-C 종료) =="
echo "   감시: tb3_1=$T1 / tb3_2=$GENJI  (default_server_endpoint, TCP 10000)"
while true; do
  for id in tb3_1 tb3_2; do
    h="$(host_of "$id")"
    # ssh 자체 실패(로봇 off/wifi)면 unreachable로 스킵 — 헛재기동 방지
    if ! n=$($SSH "$h" "pgrep -fc '[d]efault_server_endpoint' || echo 0" 2>/dev/null); then
      echo "[$(date +%H:%M:%S)] $id unreachable ($h) — 스킵"
      continue
    fi
    n=${n:-0}
    if [ "${n//[^0-9]/}" -lt 1 ] 2>/dev/null; then
      restart_ep "$id"
    fi
  done
  sleep "$INT"
done
