#!/bin/bash
# _t1_slam_reset.sh — slam_toolbox만 리셋(맵 0%로). RealSense/d2scan/throttle은 유지.
# /tmp/slam_tb3_1.yaml(마스터 스크립트가 생성) 재사용. 주의: set -u 금지.
# Run on 티원: bash /tmp/_t1_slam_reset.sh

# 1) slam_toolbox 완전 종료 (PID loop — 중복 누적 방지)
for n in 1 2 3 4 5; do
  PIDS=$(pgrep -f "slam_toolbox|async_slam|_t_slamtb")
  [ -z "$PIDS" ] && break
  kill -9 $PIDS 2>/dev/null
  sleep 2
done
sleep 1
echo "slam 잔여: $(pgrep -fc async_slam_toolbox_node)"

# 2) yaml 없으면 재작성
if [ ! -f /tmp/slam_tb3_1.yaml ]; then
cat > /tmp/slam_tb3_1.yaml <<'EOF'
slam_toolbox:
  ros__parameters:
    odom_frame: tb3_1/odom
    map_frame: map
    base_frame: tb3_1/base_footprint
    scan_topic: /scan_depth
    mode: mapping
    resolution: 0.05
    max_laser_range: 8.0
    minimum_travel_distance: 0.1
    transform_timeout: 1.0
    tf_buffer_duration: 30.0
EOF
fi

# 3) fresh slam 1개 기동
cat > /tmp/_t_slamtb.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch slam_toolbox online_async_launch.py slam_params_file:=/tmp/slam_tb3_1.yaml use_sim_time:=false
EOF
chmod +x /tmp/_t_slamtb.sh
setsid nohup bash /tmp/_t_slamtb.sh > /tmp/t_slamtb.log 2>&1 </dev/null &
sleep 10

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo -n "slam 노드 수(1이어야): "; pgrep -fc async_slam_toolbox_node
  echo -n "/scan_depth 구독(slam): "; ros2 topic info /scan_depth 2>/dev/null | grep -oE "Subscription count: [0-9]+"
  echo -n "/map pub: "; ros2 topic info /map 2>/dev/null | grep -oE "Publisher count: [0-9]+"
  echo "/map 크기(리셋되어 작아야): "; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo -n "slam 드롭(최근6): "; tail -6 /tmp/t_slamtb.log 2>/dev/null | grep -ci dropping
} > /tmp/reset_check.txt 2>&1
echo DONE
