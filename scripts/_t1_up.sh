#!/bin/bash
# _t1_up.sh — 티원(tb3_1) 비전 bringup: ns tb3_1 bringup + ros_tcp + RealSense D435
# SLAM 안 함(글로벌 /scan,/map 충돌 회피). namespace로 /tb3_1/* 격리.
# Run on robot: bash /tmp/_t1_up.sh <LAPTOP_LAN_IP>
set -u
PEER="${1:?LAPTOP_LAN_IP required}"
OPENCR_PORT=/dev/ttyACM0   # 티원: ACM0=OpenCR(0483), Arduino 없음

# tmux 미설치 기체 → setsid+nohup. 기존 세션 정리(pkill).
pkill -f _t_bringup.sh 2>/dev/null || true
pkill -f _t_ros_tcp.sh 2>/dev/null || true
pkill -f _t_realsense.sh 2>/dev/null || true
pkill -f default_server_endpoint 2>/dev/null || true
sleep 1

# ── 1) bringup (namespace tb3_1) ──
cat > /tmp/_t_bringup.sh <<EOF
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source \$HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=$PEER
exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1 usb_port:=$OPENCR_PORT
EOF

# ── 2) ros_tcp_endpoint (turtlebot3_ws에 설치됨) ──
cat > /tmp/_t_ros_tcp.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source $HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ROS_IP=$(hostname -I | awk '{print $1}')
exec ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=$ROS_IP -p ROS_TCP_PORT:=10000
EOF

# ── 3) RealSense D435 (ns tb3_1, color만, /tb3_1/camera/color/image_raw[/compressed]) ──
cat > /tmp/_t_realsense.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
exec ros2 launch realsense2_camera rs_launch.py \
  camera_namespace:=tb3_1 camera_name:=camera \
  enable_color:=true enable_depth:=false enable_infra1:=false enable_infra2:=false \
  rgb_camera.color_profile:=640x480x15
EOF

chmod +x /tmp/_t_bringup.sh /tmp/_t_ros_tcp.sh /tmp/_t_realsense.sh
setsid nohup bash /tmp/_t_bringup.sh   > /tmp/t_bringup.log   2>&1 < /dev/null &
setsid nohup bash /tmp/_t_ros_tcp.sh   > /tmp/t_ros_tcp.log   2>&1 < /dev/null &
setsid nohup bash /tmp/_t_realsense.sh > /tmp/t_realsense.log 2>&1 < /dev/null &
sleep 2
echo "--- 떠있는 런처 프로세스 ---"
pgrep -fl "_t_bringup.sh|_t_ros_tcp.sh|_t_realsense.sh" | head
echo OK_DONE
