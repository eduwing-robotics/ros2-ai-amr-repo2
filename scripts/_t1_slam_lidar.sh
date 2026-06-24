#!/bin/bash
# _t1_slam_lidar.sh — 티원(tb3_1) LDS-03 라이다 기반 2D SLAM 매핑.
#   bringup이 먼저 떠 /tb3_1/scan(라이다)·tf(tb3_1/odom→base_footprint)가 있다고 가정.
#   slam_toolbox online_async를 /tb3_1/scan에 붙여 글로벌 /map 생성 → 텔레옵으로 공간 주행.
#   ⚠️ 함정: tf 트리는 prefix 있음(tb3_1/odom→base_footprint→base_link→base_scan)인데
#     라이다 드라이버가 scan.header.frame_id를 non-ns 'base_scan'으로 발행(turtlebot3 버그).
#     → identity static tf 'tb3_1/base_scan → base_scan' 다리를 놓아 scan을 트리에 연결.
#   젠지(non-ns)와 같은 도메인210이라도 scan이 ns(/tb3_1/scan)라 충돌 없음.
#   단 tf는 글로벌 /tf에 non-ns로 올라가므로 젠지 ROS 동시 구동 시 odom→base_footprint 충돌 위험.
#   결정메모(2026-06-17): LiDAR=2D 매핑. depth(_t1_slam_depth.sh)는 3D 실험용.
# 주의: set -u 금지 (ROS setup.bash AMENT unbound 충돌).
# Run on 티원: bash /tmp/_t1_slam_lidar.sh
pkill -9 -f slam_toolbox 2>/dev/null || true
pkill -9 -f _t_slamtb 2>/dev/null || true
pkill -9 -f _t_scanbridge 2>/dev/null || true
sleep 2

# scan frame 다리: tb3_1/base_scan(트리) → base_scan(scan이 쓰는 frame_id), identity
cat > /tmp/_t_scanbridge.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0 --z 0 --roll 0 --pitch 0 --yaw 0 \
  --frame-id tb3_1/base_scan --child-frame-id base_scan
EOF
chmod +x /tmp/_t_scanbridge.sh
setsid nohup bash /tmp/_t_scanbridge.sh > /tmp/t_scanbridge.log 2>&1 </dev/null &
sleep 2

cat > /tmp/slam_tb3_1_lidar.yaml <<'EOF'
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
    scan_topic: /tb3_1/scan
    mode: mapping
    debug_logging: false
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
    use_scan_barycenter: true
    transform_timeout: 0.5
    tf_buffer_duration: 30.0
EOF

cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=/tmp/slam_tb3_1_lidar.yaml use_sim_time:=false
EOF
chmod +x /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_slamtb.sh > /tmp/t_slamtb.log 2>&1 </dev/null &
sleep 10

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== /tb3_1/scan pub/sub ==="; ros2 topic info /tb3_1/scan 2>/dev/null | grep -iE "Publisher count|Subscription count"
  echo "=== /tb3_1/scan 샘플 ==="; timeout 6 ros2 topic echo /tb3_1/scan --once --field ranges 2>/dev/null | head -c 80; echo
  echo "=== /map pub ==="; ros2 topic info /map 2>/dev/null | grep -iE "Publisher count" || echo no-map
  echo "=== /map 크기 ==="; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo "=== slam_toolbox 로그 ==="; tail -10 /tmp/t_slamtb.log
} > /tmp/slam_check.txt 2>&1
echo DONE
