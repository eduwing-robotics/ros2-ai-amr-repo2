#!/bin/bash
# _keepout_filter_up.sh — nav2 Costmap Filter(KeepoutFilter)용 마스크 map_server + costmap_filter_info_server 기동.
#   • _robot_amcl_ns.sh와 같은 패턴(수동 노드 기동 + lifecycle_manager ABI 우회 수동 configure→activate).
#   • global/local costmap의 filters:[keepout_filter]가 구독하는 filter_info_topic을 이 스크립트가 채운다.
#   • nav2_tb3_1_params.yaml에 keepout_filter 블록이 이미 있어야 함(patch_nav_params_ns.py로 생성).
# 사용: bash _keepout_filter_up.sh <id: tb3_1|tb3_2> <mask_yaml> [domain]
#   예) bash _keepout_filter_up.sh tb3_1 /home/t1/maps/arena_shared/keepout_mask.yaml 2
set +u
NS="$1"; MASK="$2"; DOM="${3:-2}"
if [ -z "$NS" ] || [ -z "$MASK" ]; then echo "usage: _keepout_filter_up.sh <tb3_1|tb3_2> <mask_yaml> [domain]"; exit 1; fi
if [ ! -f "$MASK" ]; then echo "마스크 없음: $MASK (scp 했는지 확인)"; exit 1; fi
LOG="/tmp/${NS}_keepout"; mkdir -p "$LOG"
SRC="source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=$DOM RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET"
eval "$SRC"

echo "==> keepout mask_server 기동 (/${NS}/keepout_mask, yaml=$MASK)"
setsid bash -c "$SRC; exec ros2 run nav2_map_server map_server --ros-args \
  -r __node:=${NS}_keepout_mask_server -p yaml_filename:='$MASK' -p frame_id:=map \
  -r map:=/${NS}/keepout_mask" \
  >"$LOG/mask_server.log" 2>&1 </dev/null &

echo "==> costmap_filter_info_server 기동 (/${NS}/costmap_filter_info)"
setsid bash -c "$SRC; exec ros2 run nav2_map_server costmap_filter_info_server --ros-args \
  -r __node:=${NS}_costmap_filter_info_server \
  -p filter_info_topic:=/${NS}/costmap_filter_info -p mask_topic:=/${NS}/keepout_mask \
  -p type:=0 -p base:=0.0 -p multiplier:=1.0" \
  >"$LOG/filter_info.log" 2>&1 </dev/null &

echo "==> 노드 등장 대기"; sleep 5
for N in ${NS}_keepout_mask_server ${NS}_costmap_filter_info_server; do
  echo "-- $N configure"; ros2 lifecycle set /$N configure; sleep 1
  echo "-- $N activate";  ros2 lifecycle set /$N activate;  sleep 1
done
echo "=== lifecycle 상태 ==="
ros2 lifecycle get /${NS}_keepout_mask_server
ros2 lifecycle get /${NS}_costmap_filter_info_server
echo "DONE."
