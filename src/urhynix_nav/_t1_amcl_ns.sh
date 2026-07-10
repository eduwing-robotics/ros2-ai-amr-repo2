#!/bin/bash
# _t1_amcl_ns.sh — 티원(tb3_1) self-host AMCL + map_server (arena_v5 저장맵 위치추정).
#   • lifecycle_manager가 ABI 깨짐(undefined symbol diagnostic_updater) → 수동 configure→activate 우회.
#   • /map 토픽을 /tb3_1/map 으로 격리 → 젠지 cartographer(/map non-ns)와 충돌 회피. frame은 공용 "map".
#   • frame: global=map, odom=tb3_1/odom, base=tb3_1/base_footprint, scan=/tb3_1/scan.
#   • 각 로봇 self-host AMCL(크로스호스트는 시계skew로 scan 폐기). set -u 금지(setup.bash가 미정의 참조).
# 사용: bash _t1_amcl_ns.sh [map_yaml]   (기본 ~/maps/arena_v5/arena_v5.yaml)
set +u
NS=tb3_1
MAP="${1:-$HOME/maps/arena_v5/arena_v5.yaml}"
LOG=/tmp/t1_amcl; mkdir -p "$LOG"
SRC='source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET'
eval "$SRC"

echo "==> map_server 기동 (/${NS}/map, frame=map, yaml=$MAP)"
setsid bash -c "$SRC; exec ros2 run nav2_map_server map_server --ros-args \
  -r __node:=${NS}_map_server -p yaml_filename:='$MAP' -p frame_id:=map -p topic_name:=/${NS}/map" \
  >"$LOG/map_server.log" 2>&1 </dev/null &

echo "==> amcl 기동 (scan=/${NS}/scan, map=/${NS}/map, odom=${NS}/odom)"
setsid bash -c "$SRC; exec ros2 run nav2_amcl amcl --ros-args \
  -r __node:=${NS}_amcl \
  -p scan_topic:=/${NS}/scan -p map_topic:=/${NS}/map \
  -p global_frame_id:=map -p odom_frame_id:=${NS}/odom -p base_frame_id:=${NS}/base_footprint \
  -p set_initial_pose:=false -p tf_broadcast:=true \
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
echo "DONE (초기포즈는 /${NS}/initialpose 로 별도 발행)"
