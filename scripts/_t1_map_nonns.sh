#!/bin/bash
# _t1_map_nonns.sh — 티원 오프라인 맵 제작 전용: non-namespace bringup + 표준 LiDAR SLAM.
#   목적: 순찰용 2D 저장맵 1장 생성. ns(tb3_1)는 런타임 듀얼로봇 순찰에만 필요하고
#   맵 제작엔 불필요 → non-ns로 scan/tf frame을 전부 base_scan/odom으로 일관시켜
#   namespace frame 불일치(라이다 frame_id 버그)·tf bridge 없이 표준 SLAM 구동.
#   젠지 ROS가 꺼져 있어야 함(글로벌 /scan,/tf,/map 충돌 회피).
# 주의: set -u 금지 (ROS setup.bash AMENT unbound 충돌).
# Run on 티원: bash /tmp/_t1_map_nonns.sh <LAPTOP_IP>
PEER="${1:-192.168.10.52}"

# 0) 기존 ns bringup/slam/bridge 전부 정리 (자기-kill 회피 bracket trick)
for p in "[t]urtlebot3" "[d]iff_drive" "[h]lds" "[l]d08" "[r]obot_state" "[s]lam_toolbox" "[a]sync_slam" "[s]tatic_transform" "[d]epthimage" "_t_"; do
  pkill -9 -f "$p" 2>/dev/null
done
sleep 4

# 1) bringup (non-namespace) — /scan(base_scan)·/odom·tf 전부 non-ns 일관
cat > /tmp/_t_bringup.sh <<EOF
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source \$HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=$PEER
exec ros2 launch turtlebot3_bringup robot.launch.py usb_port:=/dev/ttyACM0
EOF

# 2) ros_tcp_endpoint (Unity 라이브 관찰용)
cat > /tmp/_t_ros_tcp.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source $HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ROS_IP=$(hostname -I | awk '{print $1}')
exec ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=$ROS_IP -p ROS_TCP_PORT:=10000
EOF

# 2.5) scan 정규화 릴레이 (/scan 가변빔 → /scan_fixed 고정 400빔) — slam_toolbox Karto 거부 회피
cat > /tmp/_t_scannorm.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec python3 /tmp/scan_normalize.py /scan /scan_fixed 400
EOF

# 3) 표준 slam_toolbox (frames: odom, base_footprint; scan=/scan_fixed)
cat > /tmp/slam_nonns.yaml <<'EOF'
slam_toolbox:
  ros__parameters:
    solver_plugin: solver_plugins::CeresSolver
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_trust_strategy: LEVENBERG_MARQUARDT
    ceres_dogleg_type: TRADITIONAL_DOGLEG
    ceres_loss_function: None
    odom_frame: odom
    map_frame: map
    base_frame: base_footprint
    scan_topic: /scan_fixed
    mode: mapping
    throttle_scans: 1
    transform_publish_period: 0.05
    map_update_interval: 1.0
    resolution: 0.05
    max_laser_range: 3.5
    minimum_time_between_scans: 0.2
    minimum_travel_distance: 0.1
    minimum_travel_heading: 0.1
    scan_buffer_size: 10
    use_scan_matching: true
    transform_timeout: 0.5
    tf_buffer_duration: 30.0
EOF
cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=/tmp/slam_nonns.yaml use_sim_time:=false
EOF

chmod +x /tmp/_t_bringup.sh /tmp/_t_ros_tcp.sh /tmp/_t_scannorm.sh /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_bringup.sh > /tmp/t_bringup.log 2>&1 </dev/null &
setsid nohup bash /tmp/_t_ros_tcp.sh > /tmp/t_ros_tcp.log 2>&1 </dev/null &
sleep 14
setsid nohup bash /tmp/_t_scannorm.sh > /tmp/t_scannorm.log 2>&1 </dev/null &
sleep 3
setsid nohup bash /tmp/_t_slamtb.sh > /tmp/t_slamtb.log 2>&1 </dev/null &
sleep 10

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== 노드 ==="; ros2 node list 2>/dev/null
  echo "=== /scan frame ==="; timeout 5 ros2 topic echo /scan --once --field header.frame_id 2>/dev/null
  echo "=== odom->base_scan tf ==="; timeout 7 ros2 run tf2_ros tf2_echo odom base_scan 2>&1 | grep -iE "Translation|does not exist" | head -1
  echo "=== slam 드롭 수 ==="; grep -c dropping /tmp/t_slamtb.log
  echo "=== slam 로그 끝 ==="; tail -4 /tmp/t_slamtb.log
} > /tmp/map_check.txt 2>&1
echo DONE
