#!/bin/bash
# _t1_scan_throttle.sh — depth scan 30Hz를 ~7.5Hz로 다운샘플(odom 10Hz 이하)해서
#   slam_toolbox 메시지필터 큐풀 드롭 해결. d2scan→/scan_raw, 파이썬 릴레이→/scan(원본 stamp 유지).
# 주의: set -u 금지 (ROS setup.bash AMENT unbound).
# Run on 티원: bash /tmp/_t1_scan_throttle.sh
pkill -9 -f depthimage_to_laserscan 2>/dev/null || true
pkill -9 -f scan_throttle 2>/dev/null || true
sleep 2

# d2scan: 이제 /scan_raw로 출력
cat > /tmp/_t_d2scan.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 run depthimage_to_laserscan depthimage_to_laserscan_node --ros-args \
  -r depth:=/tb3_1/camera/depth/image_rect_raw \
  -r depth_camera_info:=/tb3_1/camera/depth/camera_info \
  -r scan:=/scan_raw \
  -p scan_height:=10 -p range_min:=0.25 -p range_max:=8.0
EOF

# 파이썬 throttle 릴레이: /scan_raw 매 4번째만 /scan으로 (≈7.5Hz), stamp/frame 보존
cat > /tmp/_t_scan_throttle.py <<'EOF'
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
rclpy.init()
n = Node('scan_throttle')
pub = n.create_publisher(LaserScan, '/scan', 10)
c = {'i': 0}
def cb(m):
    c['i'] += 1
    if c['i'] % 4 == 0:
        pub.publish(m)
n.create_subscription(LaserScan, '/scan_raw', cb, 10)
rclpy.spin(n)
EOF
cat > /tmp/_t_throttle.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec python3 /tmp/_t_scan_throttle.py
EOF

chmod +x /tmp/_t_d2scan.sh /tmp/_t_throttle.sh
setsid nohup bash /tmp/_t_d2scan.sh   > /tmp/t_d2scan.log   2>&1 </dev/null &
setsid nohup bash /tmp/_t_throttle.sh > /tmp/t_throttle.log 2>&1 </dev/null &
sleep 8

source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1; sleep 3
{
  echo -n "scan_raw hz: "; timeout 6 ros2 topic hz /scan_raw 2>/dev/null | grep -i average | head -1
  echo -n "scan hz(throttled): "; timeout 7 ros2 topic hz /scan 2>/dev/null | grep -i average | head -1
  echo "map 크기: "; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
  echo -n "slam 드롭(최근5줄): "; tail -5 /tmp/t_slamtb.log 2>/dev/null | grep -ci dropping
} > /tmp/throttle_check.txt 2>&1
echo DONE
