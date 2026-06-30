#!/bin/bash
# _t1_rs_pointcloud.sh — 티원 D435 깨끗 재기동 + aligned depth (3D 점군 캡처용)
# Run on 티원: bash /tmp/_t1_rs_pointcloud.sh
# 경로 B: wrapper(4.57)가 pointcloud.enable을 declare 안 함 → 티원에서 점군 안 만들고
#         aligned_depth + color + camera_info만 record → Mac d435_bag_to_ply.py가 deproject.
# record 토픽: /tb3_1/camera/aligned_depth_to_color/image_raw (Z16, color frame 정렬)
#             /tb3_1/camera/color/image_raw/compressed, /tb3_1/camera/color/camera_info
# ROS_DOMAIN_ID=210. 주의: set -u 금지 (AMENT_TRACE_SETUP_FILES unbound). 메모리: urhynix-t1-nav2-lifecycle-abi
pkill -9 -f realsense 2>/dev/null || true
pkill -9 -f rs_launch 2>/dev/null || true
pkill -9 -f component_container 2>/dev/null || true
sleep 4

cat > /tmp/_t_rs_pc_run.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch realsense2_camera rs_launch.py \
  camera_namespace:=tb3_1 camera_name:=camera \
  enable_color:=true enable_depth:=true align_depth.enable:=true \
  depth_module.depth_profile:=640x480x15 \
  rgb_camera.color_profile:=640x480x15
EOF
chmod +x /tmp/_t_rs_pc_run.sh
setsid nohup bash /tmp/_t_rs_pc_run.sh > /tmp/t_rs_pc.log 2>&1 </dev/null &
echo "launched pid_group"
sleep 16

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== rs 프로세스 ==="; pgrep -af "[r]ealsense2_camera_node" >/dev/null && echo RUNNING || echo DEAD
  echo "=== aligned depth 토픽 ==="; ros2 topic list 2>/dev/null | grep -iE "aligned_depth" | grep -vE "compressed|theora|zstd|metadata"
  echo "=== aligned depth frame_id ==="; timeout 8 ros2 topic echo /tb3_1/camera/aligned_depth_to_color/image_raw --once --field header.frame_id 2>/dev/null | head -1
  echo "=== aligned depth hz (10s) ==="; timeout 12 ros2 topic hz /tb3_1/camera/aligned_depth_to_color/image_raw 2>/dev/null | tail -2
  echo "=== load after ==="; uptime
  echo "=== log tail ==="; tail -8 /tmp/t_rs_pc.log
} > /tmp/pc_check.txt 2>&1
echo DONE
