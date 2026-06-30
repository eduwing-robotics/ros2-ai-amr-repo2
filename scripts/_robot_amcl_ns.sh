#!/bin/bash
# _robot_amcl_ns.sh — 로봇 self-host AMCL + map_server (저장맵 위치추정). _t1_amcl_ns.sh의 id-일반화 정본.
#   • id를 첫 인자로 받아 젠지(tb3_2)·티원(tb3_1) 양쪽 공용. (_t1_amcl_ns.sh는 레거시 tb3_1 전용.)
#   • lifecycle_manager ABI 깨짐 우회 → 수동 configure→activate (티원 필수, 젠지도 무해).
#   • /map 토픽을 /<id>/map 으로 격리 → 다른 로봇/cartographer(/map non-ns)와 충돌 회피. frame은 공용 "map".
#   • frame: global=map, odom=<id>/odom, base=<id>/base_footprint, scan=/<id>/scan.
#   • 각 로봇은 자기 호스트에서 실행(크로스호스트는 시계 skew로 scan 폐기).
#   • set_initial_pose: 충전소 좌표를 알면 IX/IY/IYAW(rad) 인자로 박아 무-teleop 자동 시작.
# 사용: bash _robot_amcl_ns.sh <id: tb3_1|tb3_2> [map_yaml] [ix] [iy] [iyaw_rad]
#   예) 티원: bash _robot_amcl_ns.sh tb3_1
#       젠지: bash _robot_amcl_ns.sh tb3_2 ~/maps/arena_v5/arena_v5.yaml
#       자동: bash _robot_amcl_ns.sh tb3_1 ~/maps/arena_v5/arena_v5.yaml 0.9 -0.94 -2.46
# 주의: set -u 금지(setup.bash가 미정의 변수 참조).
set +u
NS="$1"
if [ -z "$NS" ]; then echo "usage: _robot_amcl_ns.sh <tb3_1|tb3_2> [map_yaml] [ix iy iyaw_rad]"; exit 1; fi
MAP="${2:-$HOME/maps/arena_v5/arena_v5.yaml}"
IX="$3"; IY="$4"; IYAW="$5"
LOG="/tmp/${NS}_amcl"; mkdir -p "$LOG"
SRC='source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET'
eval "$SRC"

if [ ! -f "$MAP" ]; then echo "맵 없음: $MAP (arena_v5 scp 했는지 확인)"; exit 1; fi

# 초기포즈 인자가 다 있으면 set_initial_pose 활성
SIP="false"; IP_PARAMS=""
if [ -n "$IX" ] && [ -n "$IY" ] && [ -n "$IYAW" ]; then
  SIP="true"
  IP_PARAMS="-p initial_pose.x:=$IX -p initial_pose.y:=$IY -p initial_pose.yaw:=$IYAW"
  echo "==> set_initial_pose=true ($IX,$IY,yaw=$IYAW)"
fi

# scan_frame_fix: coin_d4 scan을 frame=${NS}/base_scan + stamp=now로 교정해 /${NS}/scan_fixed로 republish
# (디바이스 시계 skew로 AMCL이 scan을 "earlier than transform cache"로 폐기하는 것 우회 — 2026-06-29)
pkill -9 -f "[s]can_frame_fix" 2>/dev/null
setsid bash -c "$SRC; exec python3 \$HOME/scan_frame_fix.py --robot ${NS}" \
  >"$LOG/scan_fix.log" 2>&1 </dev/null &
echo "==> scan_frame_fix 기동 (/${NS}/scan → /${NS}/scan_fixed)"

echo "==> map_server 기동 (/${NS}/map, frame=map, yaml=$MAP)"
setsid bash -c "$SRC; exec ros2 run nav2_map_server map_server --ros-args \
  -r __node:=${NS}_map_server -p yaml_filename:='$MAP' -p frame_id:=map -p topic_name:=/${NS}/map" \
  >"$LOG/map_server.log" 2>&1 </dev/null &

echo "==> amcl 기동 (scan=/${NS}/scan_fixed, map=/${NS}/map, odom=${NS}/odom)"
setsid bash -c "$SRC; exec ros2 run nav2_amcl amcl --ros-args \
  -r __node:=${NS}_amcl \
  -p scan_topic:=/${NS}/scan_fixed -p map_topic:=/${NS}/map \
  -p global_frame_id:=map -p odom_frame_id:=${NS}/odom -p base_frame_id:=${NS}/base_footprint \
  -p set_initial_pose:=$SIP $IP_PARAMS -p tf_broadcast:=true \
  -r initialpose:=/${NS}/initialpose -r amcl_pose:=/${NS}/amcl_pose -r particle_cloud:=/${NS}/particle_cloud" \
  >"$LOG/amcl.log" 2>&1 </dev/null &

echo "==> 노드 등장 대기"; sleep 7
# lifecycle_manager 우회: 수동 configure→activate (map_server 먼저 활성→/map latch→amcl)
for N in ${NS}_map_server ${NS}_amcl; do
  echo "-- $N configure"; ros2 lifecycle set /$N configure; sleep 2
  echo "-- $N activate";  ros2 lifecycle set /$N activate;  sleep 2
done
echo "=== lifecycle 상태 ==="
ros2 lifecycle get /${NS}_map_server
ros2 lifecycle get /${NS}_amcl
echo "=== /${NS}/map 발행 확인 ==="
timeout 5 ros2 topic info /${NS}/map | grep "Publisher count"
echo "DONE. 초기포즈 미지정 시 /${NS}/initialpose 발행 또는 제자리 회전으로 수렴."
