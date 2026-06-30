#!/bin/bash
# d435_record_only.sh — 티원 로컬: aligned depth+color+tf를 N초 record(자동 종료). 회전 명령 없음.
# d435_record_smoke.sh의 record 블록만(자동회전 제거) — 동료 teleop 협업 매핑용.
#   자동회전을 빼는 이유: teleop_stamped.py와 /tb3_1/cmd_vel publisher가 겹치면 명령이 싸워 떨림.
# Run on 티원: bash /tmp/d435_record_only.sh [secs]   (기본 120s)
# 선행: bringup(/tb3_1/odom) + _t1_rs_pointcloud.sh(aligned depth) + base_link→camera_link static tf.
# 산출: /tmp/d435_rot_<ts> (rosbag2). scp → Mac → scripts/d435_bag_to_ply.py. 주의: set -u 금지.
SECS="${1:-120}"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
BAG=/tmp/d435_rot_$(date +%s)
rm -rf "$BAG"
echo "record ${SECS}s 시작 — 지금부터 동료가 teleop으로 천천히 주행하세요 (벽 0.3~3m, 급회전 금지)."
# timeout --signal=INT = record 자동 종료(ros2 bag record는 pkill -INT로 안 닫혀 5GB 폭주 → 함정 회피).
timeout --signal=INT "${SECS}" ros2 bag record -o "$BAG" \
  /tb3_1/camera/aligned_depth_to_color/image_raw \
  /tb3_1/camera/aligned_depth_to_color/camera_info \
  /tb3_1/camera/color/image_raw/compressed \
  /tf /tf_static /tb3_1/odom
echo "=== bag info ==="
ros2 bag info "$BAG" 2>/dev/null | grep -E "Duration|Messages|Topic:|Count" | head -25
du -sh "$BAG" 2>/dev/null
echo "BAG=$BAG  → Mac으로: scp -r t1:$BAG docs/evidence/3d_maps/<session>/"
