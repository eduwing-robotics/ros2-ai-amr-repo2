#!/bin/bash
# nav_up.sh — AMCL+Nav2 단일(젠지) 한방 기동(Mac에서 실행). 좌표주행용. odom 쌍(dual_marker_up.sh)의 주행판.
# ★전제: 젠지를 충전소에 도킹한 뒤 실행(초기포즈=충전소). 젠지는 풀 nav2 스택 보유(티원은 패키지 미설치라 제외).
# 하는 일: 스크립트4종+arena_v4 맵을 젠지에 scp(맵은 ~/maps/arena_v4/로 격리 — 기존 map.pgm 충돌 회피) → _robot_nav_up.sh 기동.
# 사용: bash scripts/nav_up.sh [GENJI_SSH] [IX] [IY] [IYAW_deg]   (IP drift/충전소좌표/heading은 인자로 덮어쓰기)
# Unity: ros_endpoint.json=젠지 IP. Play 후 맵 우클릭 "출동"=/tb3_2/goal_pose → 브리지 → Nav2 실주행.
set -u
GENJI=${1:-kim@192.168.10.84}
IX=${2:-0.0}; IY=${3:-0.0}; IYAW=${4:-0}
D="$(cd "$(dirname "$0")" && pwd)"
MAPDIR="$D/../docs/evidence/maps/arena_v4"
SSH="ssh -o ConnectTimeout=12 -o ControlMaster=no"

echo "== 스크립트 scp =="
for f in robot_pose_publisher.py patrol_waypoints_bridge.py drive_rotate.py _robot_nav_up.sh; do
  scp -o ConnectTimeout=10 "$D/$f" "$GENJI":/tmp/ || { echo "scp 실패: $f"; exit 1; }
done

echo "== arena_v4 맵 scp(→ ~/maps/arena_v4/, image:map.pgm 참조 유지) =="
$SSH "$GENJI" 'mkdir -p ~/maps/arena_v4'
scp -o ConnectTimeout=10 "$MAPDIR/arena_v4.pgm"  "$GENJI":'~/maps/arena_v4/map.pgm'  || { echo "맵 pgm scp 실패"; exit 1; }
scp -o ConnectTimeout=10 "$MAPDIR/arena_v4.yaml" "$GENJI":'~/maps/arena_v4/map.yaml' || { echo "맵 yaml scp 실패"; exit 1; }

echo "== 젠지(tb3_2) AMCL+Nav2 기동 + endpoint =="
$SSH "$GENJI" "bash /tmp/_robot_nav_up.sh tb3_2 $IX $IY $IYAW yes"

cat <<'EOF'
DONE.
1) Unity ros_endpoint.json = 젠지 IP 확인 → Stop→Play.
2) 충전소에 젠지 마커(파랑) 뜨는지 확인. 위치 어긋나면(AMCL 미수렴):
   ssh <GENJI> 'source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp; python3 /tmp/drive_rotate.py /cmd_vel 0.4 12'
   → 제자리 회전으로 particle 수렴, Unity 마커가 실제 위치에 붙는지 재확인.
3) 마커 정합되면 맵에서 목표 클릭(출동) → /tb3_2/goal_pose → Nav2 실주행.
EOF
