#!/bin/bash
# _t1_slam_depth.sh — 티원 depth 2D SLAM 매핑 (RealSense는 이미 떠 있다고 가정)
#   static tf(base_link→camera_link) + depthimage_to_laserscan(/scan) + slam_toolbox(/map)
# 주의: set -u 금지 (ROS setup.bash AMENT unbound 충돌).
# Run on 티원: bash /tmp/_t1_slam_depth.sh
for s in statictf d2scan slamtb; do pkill -9 -f "_t_$s" 2>/dev/null || true; done
pkill -9 -f static_transform_publisher 2>/dev/null || true
pkill -9 -f depthimage_to_laserscan 2>/dev/null || true
pkill -9 -f slam_toolbox 2>/dev/null || true
sleep 2

# static tf: 로봇 base_link → 카메라 (D435 마운트 추정 x0.05 z0.12, 실측 보정)
cat > /tmp/_t_statictf.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run tf2_ros static_transform_publisher \
  --x 0.05 --y 0.0 --z 0.12 --roll 0 --pitch 0 --yaw 0 \
  --frame-id tb3_1/base_link --child-frame-id camera_link
EOF

# depth → /scan (scan 프레임 = depth optical frame, 기본)
cat > /tmp/_t_d2scan.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run depthimage_to_laserscan depthimage_to_laserscan_node --ros-args \
  -r depth:=/tb3_1/camera/depth/image_rect_raw \
  -r depth_camera_info:=/tb3_1/camera/depth/camera_info \
  -r scan:=/scan \
  -p scan_height:=10 -p range_min:=0.25 -p range_max:=8.0
EOF

# slam_toolbox: /scan → 글로벌 /map (frames=tb3_1)
cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run slam_toolbox async_slam_toolbox_node --ros-args \
  -p odom_frame:=tb3_1/odom \
  -p base_frame:=tb3_1/base_footprint \
  -p map_frame:=map \
  -p scan_topic:=/scan \
  -p mode:=mapping \
  -p resolution:=0.05 \
  -p max_laser_range:=8.0 \
  -p minimum_travel_distance:=0.1 \
  -p use_sim_time:=false
EOF

chmod +x /tmp/_t_statictf.sh /tmp/_t_d2scan.sh /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_statictf.sh > /tmp/t_statictf.log 2>&1 </dev/null &
setsid nohup bash /tmp/_t_d2scan.sh   > /tmp/t_d2scan.log   2>&1 </dev/null &
sleep 3
setsid nohup bash /tmp/_t_slamtb.sh   > /tmp/t_slamtb.log   2>&1 </dev/null &
sleep 8

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== /scan pub ==="; ros2 topic info /scan 2>/dev/null | grep -i publisher
  echo "=== /scan ranges 샘플 ==="; timeout 6 ros2 topic echo /scan --once --field ranges 2>/dev/null | head -c 80; echo
  echo "=== /map pub ==="; ros2 topic info /map 2>/dev/null | grep -i publisher
  echo "=== /map 크기 ==="; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo "=== slam_toolbox 로그 ==="; tail -6 /tmp/t_slamtb.log
  echo "=== d2scan 로그 ==="; tail -4 /tmp/t_d2scan.log
} > /tmp/slam_check.txt 2>&1
echo DONE
