#!/bin/bash
# _dock_reseed.sh — 손으로 옮겨 놓은 로봇을 저장맵 고정좌표(기본: 티원 충전독)로 AMCL 재시딩(로봇에서 실행).
# 반올림 쿼터니언 함정 회피(정밀 sin/cos) + nomotion 1회 + "Setting pose" 수락로그·amcl_pose 검증까지 한 번에.
# 사용: bash _dock_reseed.sh [ns=tb3_1] [x=0.038] [y=1.405] [yaw_rad=0.293] [domain=2]
# ⚠️ 전제: 로봇이 실제로 그 좌표·방향에 물리적으로 놓여 있어야 함(재시딩=위치 선언, amcl 스킬 함정#4).
# ⚠️ 기본 좌표는 arena_shared(2026-07-03 재캡처) 기준 — 맵 재캡처 시 "초기포즈 재확보 절차"로 갱신할 것.
NS=${1:-tb3_1}; X=${2:-0.038}; Y=${3:-1.405}; YAW=${4:-0.293}; DOM=${5:-2}
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=$DOM RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
read QZ QW < <(python3 -c "import math;y=$YAW;print(repr(math.sin(y/2)),repr(math.cos(y/2)))")
timeout 15 ros2 topic pub --times 5 -r 2 /$NS/initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: map}, pose: {pose: {position: {x: $X, y: $Y, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.01,0,0,0,0,0, 0,0.01,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.06]}}" >/dev/null 2>&1
sleep 1
timeout 8 ros2 service call /$NS/request_nomotion_update std_srvs/srv/Empty {} >/dev/null 2>&1
echo "== 수락 판정(이 줄의 좌표가 방금 값이어야 함) =="
grep "Setting pose" "/tmp/${NS}_amcl/amcl.log" | tail -1
timeout 6 ros2 topic echo --once /$NS/amcl_pose 2>/dev/null | grep -E "^      [xy]:" | head -2
