#!/bin/bash
# _genji_core_up.sh — 젠지(tb3_2) SLAM 풀스택 코어: non-ns bringup(usb_port=OpenCR) + ros_tcp
# 듀얼+SLAM 공존: 네임스페이스 없이 글로벌 /scan,/map,/tf,/battery_state 발행. 배터리만 별도 relay.
# Run on robot: bash /tmp/_genji_core_up.sh <LAPTOP_LAN_IP>
set -u
PEER="${1:?LAPTOP_LAN_IP required}"
# OpenCR(0483) 포트 자동 감지 (재부팅마다 ACM 번호 스왑 대응)
OPENCR_PORT=""
for d in /dev/ttyACM*; do
  [ -e "$d" ] || continue
  if udevadm info -q property -n "$d" 2>/dev/null | grep -q "ID_VENDOR_ID=0483"; then OPENCR_PORT="$d"; break; fi
done
OPENCR_PORT="${OPENCR_PORT:-/dev/ttyACM0}"
echo "OpenCR 포트 = $OPENCR_PORT"

tmux kill-session -t bringup 2>/dev/null || true
tmux kill-session -t ros_tcp 2>/dev/null || true

cat > /tmp/_g_bringup.sh <<EOF
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source \$HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=$PEER
exec ros2 launch turtlebot3_bringup robot.launch.py usb_port:=$OPENCR_PORT
EOF
chmod +x /tmp/_g_bringup.sh

cat > /tmp/_g_ros_tcp.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source $HOME/turtlebot3_ws/install/setup.bash
source $HOME/unity_ros_ws/install/setup.bash 2>/dev/null
export ROS_DOMAIN_ID=210
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ROS_IP=$(hostname -I | awk '{print $1}')
exec ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=$ROS_IP -p ROS_TCP_PORT:=10000
EOF
chmod +x /tmp/_g_ros_tcp.sh

tmux new-session -d -s bringup "bash /tmp/_g_bringup.sh 2>&1 | tee /tmp/g_bringup.log"
tmux new-session -d -s ros_tcp "bash /tmp/_g_ros_tcp.sh 2>&1 | tee /tmp/g_ros_tcp.log"
sleep 1
tmux ls
echo OK_DONE
