#!/bin/bash
# _t1_depthmap_full.sh — 티원 D435 depth 2D SLAM 풀 파이프라인 (검증된 픽스 일괄)
#   RealSense(depth, 기본프로파일) → static tf → depthimage_to_laserscan(/scan_raw)
#   → python throttle(/scan_raw→/scan ~7.5Hz) → slam_toolbox(launch+yaml, /map)
# 핵심 픽스: set -u 금지 / explicit depth profile 금지(기본만) / slam은 launch+yaml / scan rate<odom(10Hz)
# Run on 티원: bash /tmp/_t1_depthmap_full.sh
RANGE_ENV="ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET"

# 0) 기존 매핑 파이프라인 완전 리셋 (PID 계산 kill 반복 — 무선 끊김으로 중복 누적 방지)
#    bringup/ros_tcp/라이다는 건드리지 않음 (slam은 /scan_depth만 보므로 라이다 무관)
for n in 1 2 3 4 5; do
  PIDS=$(pgrep -f "realsense|component_container|depthimage_to_laserscan|scan_throttle|slam_toolbox|async_slam|static_transform|_t_rs_run|_t_d2scan|_t_throttle|_t_slamtb|_t_statictf")
  [ -z "$PIDS" ] && break
  kill -9 $PIDS 2>/dev/null
  sleep 2
done
sleep 2

# 1) RealSense depth+color (기본 프로파일 = 안정. explicit profile 금지)
cat > /tmp/_t_rs_run.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch realsense2_camera rs_launch.py camera_namespace:=tb3_1 camera_name:=camera \
  enable_color:=true enable_depth:=true align_depth.enable:=false pointcloud.enable:=false
EOF

# 2) static tf: tb3_1/base_link → camera_link (D435 마운트 추정 x0.05 z0.12)
cat > /tmp/_t_statictf.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run tf2_ros static_transform_publisher --x 0.05 --y 0 --z 0.12 --roll 0 --pitch 0 --yaw 0 \
  --frame-id tb3_1/base_link --child-frame-id camera_link
EOF

# 3) depth → /scan_raw
cat > /tmp/_t_d2scan.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run depthimage_to_laserscan depthimage_to_laserscan_node --ros-args \
  -r depth:=/tb3_1/camera/depth/image_rect_raw -r depth_camera_info:=/tb3_1/camera/depth/camera_info \
  -r scan:=/scan_raw -p scan_height:=10 -p range_min:=0.25 -p range_max:=8.0
EOF

# 4) throttle /scan_raw → /scan (매 4번째 ≈7.5Hz, odom 10Hz 이하)
cat > /tmp/_t_scan_throttle.py <<'EOF'
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
rclpy.init(); n=Node('scan_throttle')
pub=n.create_publisher(LaserScan,'/scan_depth',10); c={'i':0}
def cb(m):
    c['i']+=1
    if c['i']%4==0: pub.publish(m)
n.create_subscription(LaserScan,'/scan_raw',cb,10); rclpy.spin(n)
EOF
cat > /tmp/_t_throttle.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec python3 /tmp/_t_scan_throttle.py
EOF

# 5) slam_toolbox params + launch
cat > /tmp/slam_tb3_1.yaml <<'EOF'
slam_toolbox:
  ros__parameters:
    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT
    ceres_dogleg_type: TRADITIONAL_DOGLEG
    ceres_loss_function: None
    odom_frame: tb3_1/odom
    map_frame: map
    base_frame: tb3_1/base_footprint
    scan_topic: /scan_depth
    mode: mapping
    throttle_scans: 1
    transform_publish_period: 0.05
    map_update_interval: 2.0
    resolution: 0.05
    max_laser_range: 8.0
    minimum_time_between_scans: 0.2
    minimum_travel_distance: 0.1
    minimum_travel_heading: 0.1
    scan_buffer_size: 10
    use_scan_matching: true
    transform_timeout: 1.0
    tf_buffer_duration: 30.0
EOF
cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch slam_toolbox online_async_launch.py slam_params_file:=/tmp/slam_tb3_1.yaml use_sim_time:=false
EOF

chmod +x /tmp/_t_rs_run.sh /tmp/_t_statictf.sh /tmp/_t_d2scan.sh /tmp/_t_throttle.sh /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_rs_run.sh   > /tmp/t_rs_depth.log  2>&1 </dev/null &
setsid nohup bash /tmp/_t_statictf.sh > /tmp/t_statictf.log  2>&1 </dev/null &
sleep 14   # RealSense 워밍업
setsid nohup bash /tmp/_t_d2scan.sh   > /tmp/t_d2scan.log    2>&1 </dev/null &
sleep 2
setsid nohup bash /tmp/_t_throttle.sh > /tmp/t_throttle.log  2>&1 </dev/null &
sleep 2
setsid nohup bash /tmp/_t_slamtb.sh   > /tmp/t_slamtb.log    2>&1 </dev/null &
sleep 10

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== depth stamp vs now ==="; python3 -c "import time;print('now',int(time.time()))"
  timeout 6 ros2 topic echo /tb3_1/camera/depth/image_rect_raw --once --field header.stamp 2>/dev/null | grep sec | head -1
  echo -n "scan_raw hz: "; timeout 7 ros2 topic hz /scan_raw 2>/dev/null | grep -i average | head -1
  echo -n "scan_depth hz: "; timeout 7 ros2 topic hz /scan_depth 2>/dev/null | grep -i average | head -1
  echo -n "/scan_depth pub+sub: "; ros2 topic info /scan_depth 2>/dev/null | grep -oE "count: [0-9]+" | tr "\n" " "; echo
  echo -n "/map pub: "; ros2 topic info /map 2>/dev/null | grep -oE "Publisher count: [0-9]+"
  echo "/map 크기:"; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo -n "slam 드롭(최근6줄): "; tail -6 /tmp/t_slamtb.log 2>/dev/null | grep -ci dropping
} > /tmp/depthmap_check.txt 2>&1
echo DONE
