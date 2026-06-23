#!/bin/bash
# _t1_depthmap.sh — 티원(tb3_1) D435 depth 매핑 스택
#   1) RealSense depth+color 재기동  2) base_link→camera static tf
#   3) depthimage_to_laserscan(depth→/scan)  4) slam_toolbox(2D /map)
# 낮은 가벽이 LDS-03 평면 위라 안 잡히는 문제 → 카메라 depth 평면으로 매핑.
# Run on 티원: bash /tmp/_t1_depthmap.sh
set -u
for s in _t_realsense.sh d2scan slamtb statictf; do pkill -f "$s" 2>/dev/null || true; done
pkill -f rs_launch 2>/dev/null || true
sleep 2

# ── 1) RealSense: depth + color (depthimage_to_laserscan용 depth/image_rect_raw 필요) ──
cat > /tmp/_t_rs_depth.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch realsense2_camera rs_launch.py \
  camera_namespace:=tb3_1 camera_name:=camera \
  enable_color:=true enable_depth:=true enable_infra1:=false enable_infra2:=false \
  depth_module.depth_profile:=640x480x15 rgb_camera.color_profile:=640x480x15 \
  pointcloud.enable:=false
EOF

# ── 2) static tf: tb3_1/base_link → tb3_1/camera_link (D435 마운트 추정 오프셋) ──
#   x 전방 0.05m, z 위 0.12m. 실측 시 보정. (URDF에 D435 없어 직접 박음)
cat > /tmp/_t_statictf.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run tf2_ros static_transform_publisher \
  --x 0.05 --y 0.0 --z 0.12 --roll 0 --pitch 0 --yaw 0 \
  --frame-id tb3_1/base_link --child-frame-id tb3_1_camera_link
EOF

# ── 3) depthimage_to_laserscan: depth → /scan (slam_toolbox 글로벌 입력) ──
cat > /tmp/_t_d2scan.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run depthimage_to_laserscan depthimage_to_laserscan_node --ros-args \
  -r depth:=/tb3_1/camera/depth/image_rect_raw \
  -r depth_camera_info:=/tb3_1/camera/depth/camera_info \
  -r scan:=/scan \
  -p scan_height:=10 -p range_min:=0.2 -p range_max:=8.0 \
  -p output_frame:=tb3_1/camera_depth_optical_frame
EOF

# ── 4) slam_toolbox: /scan → 글로벌 /map (frames=tb3_1) ──
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

chmod +x /tmp/_t_rs_depth.sh /tmp/_t_statictf.sh /tmp/_t_d2scan.sh /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_rs_depth.sh  > /tmp/t_rs_depth.log  2>&1 </dev/null &
setsid nohup bash /tmp/_t_statictf.sh  > /tmp/t_statictf.log  2>&1 </dev/null &
sleep 6   # RealSense 워밍업
setsid nohup bash /tmp/_t_d2scan.sh    > /tmp/t_d2scan.log    2>&1 </dev/null &
sleep 2
setsid nohup bash /tmp/_t_slamtb.sh    > /tmp/t_slamtb.log    2>&1 </dev/null &
sleep 2
echo "--- 런처 ---"; pgrep -fl "rs_depth|statictf|d2scan|slamtb" | head
echo OK_DONE
