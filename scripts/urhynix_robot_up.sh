#!/bin/bash
# URHYNIX robot one-shot reconnect — bringup + ros_tcp_endpoint
# Run on the robot via:  bash /tmp/urhynix_robot_up.sh <MAC_IP>
set -u
MAC_IP="${1:?MAC_IP required (your laptop LAN IP for ROS_STATIC_PEERS)}"

# Kill old sessions (idempotent)
tmux kill-session -t bringup 2>/dev/null || true
tmux kill-session -t ros_tcp 2>/dev/null || true

# ─── 1) Inner script: TurtleBot bringup ───
# Unquoted heredoc so $MAC_IP is expanded; $HOME stays literal via \$HOME.
cat > /tmp/_tb3_bringup.sh <<EOF
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source \$HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=$MAC_IP
exec ros2 launch turtlebot3_bringup robot.launch.py
EOF
chmod +x /tmp/_tb3_bringup.sh

# ─── 2) Inner script: ROS-TCP-Endpoint ───
# Quoted heredoc so all $ are literal; hostname -I picks robot's own LAN IP.
cat > /tmp/_tb3_ros_tcp.sh <<'EOF'
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source $HOME/turtlebot3_ws/install/setup.bash
source $HOME/unity_ros_ws/install/setup.bash
export ROS_DOMAIN_ID=210
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ROS_IP=$(hostname -I | awk '{print $1}')
exec ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=$ROS_IP -p ROS_TCP_PORT:=10000
EOF
chmod +x /tmp/_tb3_ros_tcp.sh

# ─── 3) Launch both in tmux with tee logging ───
tmux new-session -d -s bringup "bash /tmp/_tb3_bringup.sh 2>&1 | tee /tmp/bringup.log"
tmux new-session -d -s ros_tcp "bash /tmp/_tb3_ros_tcp.sh 2>&1 | tee /tmp/ros_tcp_endpoint.log"

sleep 1
tmux ls
echo OK_DONE
