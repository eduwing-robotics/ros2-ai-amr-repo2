#!/bin/bash
# _genji_rest_up.sh — 젠지(tb3_2) 나머지 트랙: cartographer + Pi카메라 + 배터리relay + arduino(LDR/PIR)
# 전제: _genji_core_up.sh로 bringup(/scan,/battery_state)+ros_tcp 이미 떠 있음.
# Run on robot: bash /tmp/_genji_rest_up.sh
set -u
for s in slam camera batrelay arduino; do tmux kill-session -t $s 2>/dev/null || true; done

# ── 1) cartographer (apt판; ws 오버레이 깨진 심링크 회피 위해 /opt/ros/jazzy만) ──
cat > /tmp/_g_slam.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=false
EOF

# ── 2) Pi 카메라 (camera_ros, ns /tb3_2, 640x480, libcamera LD_LIBRARY_PATH) ──
cat > /tmp/_g_camera.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export LD_LIBRARY_PATH=/usr/local/lib/aarch64-linux-gnu:$LD_LIBRARY_PATH
export LIBCAMERA_IPA_MODULE_PATH=/usr/local/lib/aarch64-linux-gnu/libcamera
exec ros2 run camera_ros camera_node --ros-args -r __ns:=/tb3_2 -r __node:=camera \
  -p width:=640 -p height:=480
EOF

# ── 3) 배터리 relay (/battery_state → /tb3_2/battery_state) ──
cat > /tmp/_g_batrelay.py <<'EOF'
import rclpy; from rclpy.node import Node
from sensor_msgs.msg import BatteryState
rclpy.init(); n=Node('battery_relay_tb3_2')
p=n.create_publisher(BatteryState,'/tb3_2/battery_state',10)
n.create_subscription(BatteryState,'/battery_state',lambda m:p.publish(m),10)
rclpy.spin(n)
EOF
cat > /tmp/_g_batrelay.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec python3 /tmp/_g_batrelay.py
EOF

# ── 4) arduino_bridge (원본 무수정: /tmp 복사본에 /dev/ttyACM0 주입, ROBOT_ID=tb3_2) ──
sed 's|/dev/tb3_arduino|/dev/ttyACM0|' ~/arduino_bridge.py > /tmp/_g_arduino_bridge.py
cat > /tmp/_g_arduino.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export URHYNIX_ROBOT_ID=tb3_2
exec python3 /tmp/_g_arduino_bridge.py
EOF

chmod +x /tmp/_g_slam.sh /tmp/_g_camera.sh /tmp/_g_batrelay.sh /tmp/_g_arduino.sh
tmux new-session -d -s slam     "bash /tmp/_g_slam.sh 2>&1 | tee /tmp/g_slam.log"
tmux new-session -d -s camera   "bash /tmp/_g_camera.sh 2>&1 | tee /tmp/g_camera.log"
tmux new-session -d -s batrelay "bash /tmp/_g_batrelay.sh 2>&1 | tee /tmp/g_batrelay.log"
tmux new-session -d -s arduino  "bash /tmp/_g_arduino.sh 2>&1 | tee /tmp/g_arduino.log"
sleep 1
tmux ls
echo OK_DONE
