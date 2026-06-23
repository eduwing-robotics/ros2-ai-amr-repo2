#!/bin/bash
# _t1_rs_depth_only.sh — 티원 D435 depth+color 깨끗한 재기동 (depth 매핑용)
# Run on 티원: bash /tmp/_t1_rs_depth_only.sh
# 주의: set -u 금지 — ROS setup.bash가 AMENT_TRACE_SETUP_FILES unbound로 죽음.
pkill -9 -f realsense 2>/dev/null || true
pkill -9 -f rs_launch 2>/dev/null || true
pkill -9 -f component_container 2>/dev/null || true
sleep 4

cat > /tmp/_t_rs_run.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch realsense2_camera rs_launch.py \
  camera_namespace:=tb3_1 camera_name:=camera \
  enable_color:=true enable_depth:=true align_depth.enable:=false pointcloud.enable:=false
EOF
chmod +x /tmp/_t_rs_run.sh
setsid nohup bash /tmp/_t_rs_run.sh > /tmp/t_rs_depth.log 2>&1 </dev/null &
echo "launched pid_group"
sleep 14

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== rs 프로세스 ==="; pgrep -f _t_rs_run >/dev/null && echo RUNNING || echo DEAD
  echo "=== depth 토픽 ==="; ros2 topic list 2>/dev/null | grep -iE "depth" | grep -vE "compressed|theora|zstd|metadata|extrinsics"
  echo "=== depth frame_id ==="; timeout 6 ros2 topic echo /tb3_1/camera/depth/image_rect_raw --once --field header.frame_id 2>/dev/null | head -1
  echo "=== log tail ==="; tail -12 /tmp/t_rs_depth.log
} > /tmp/depth_check.txt 2>&1
echo DONE
