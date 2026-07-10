#!/bin/bash
# d435_record_smoke.sh — 티원 로컬: aligned depth + color + tf 30초 record + 제자리 회전 캡처.
# Run on 티원: bash /tmp/d435_record_smoke.sh [wz rad/s] [secs]
# 선행 조건: bringup(/tb3_1/odom) + _t1_rs_pointcloud.sh(aligned depth) + base_link→camera_link static tf 가동.
# 산출: /tmp/d435_smoke_<ts> (rosbag2 디렉토리). scp로 Mac 복사 → scripts/d435_bag_to_ply.py.
# 좌표 누적: tf chain tb3_1/odom → base_footprint → base_link → camera_link → camera_color_optical_frame.
# 주의: set -u 금지 (ROS setup.bash). 회전은 병진 0 = 제자리(벽 충돌 없음). 충전 케이블 사전 확인.
WZ="${1:-0.3}"; SECS="${2:-21}"
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
BAG=/tmp/d435_rot_$(date +%s)
rm -rf "$BAG"
RECSECS=$((SECS + 8))   # 회전 전후 여유. timeout --signal=INT = record 자동 종료(폭주 방지)
timeout --signal=INT "${RECSECS}" ros2 bag record -o "$BAG" \
  /tb3_1/camera/aligned_depth_to_color/image_raw \
  /tb3_1/camera/aligned_depth_to_color/camera_info \
  /tb3_1/camera/color/image_raw/compressed \
  /tf /tf_static /tb3_1/odom > /tmp/d435_rec.log 2>&1 &
RECPID=$!
sleep 4
echo "rotating TwistStamped wz=$WZ rad/s for ${SECS}s (제자리) ..."
# turtlebot3_node는 /tb3_1/cmd_vel을 TwistStamped로 구독 + 매틱 현재 stamp 필요 → drive_rotate.py (ros2 topic pub 불가).
python3 /tmp/drive_rotate.py /tb3_1/cmd_vel "$WZ" "$SECS"   # 끝에 정지 명령 포함
wait "$RECPID"
echo "=== bag info ==="
ros2 bag info "$BAG" 2>/dev/null | grep -E "Duration|Messages|Topic:|Count|Storage" | head -25
du -sh "$BAG" 2>/dev/null
echo "BAG=$BAG"
