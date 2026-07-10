#!/bin/bash
# _t1_slamtb_relaunch.sh — slam_toolbox를 params yaml + online_async_launch로 정석 재기동
# (sparse -p로는 /scan 구독이 안 붙던 문제 우회). 주의: set -u 금지.
# Run on 티원: bash /tmp/_t1_slamtb_relaunch.sh
pkill -9 -f slam_toolbox 2>/dev/null || true
sleep 2

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
    scan_topic: /scan
    mode: mapping
    debug_logging: false
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
    use_scan_barycenter: true
    transform_timeout: 0.5
    tf_buffer_duration: 30.0
EOF

cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch slam_toolbox online_async_launch.py \
  slam_params_file:=/tmp/slam_tb3_1.yaml use_sim_time:=false
EOF
chmod +x /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_slamtb.sh > /tmp/t_slamtb.log 2>&1 </dev/null &
sleep 10

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo "=== /scan 구독자 ==="; ros2 topic info /scan 2>/dev/null | grep -iE "subscription|publisher"
  echo "=== /map pub ==="; ros2 topic info /map 2>/dev/null | grep -i publisher || echo no-map
  echo "=== /map 크기 ==="; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo "=== slam_toolbox 로그 ==="; tail -10 /tmp/t_slamtb.log
} > /tmp/slam_check.txt 2>&1
echo DONE
