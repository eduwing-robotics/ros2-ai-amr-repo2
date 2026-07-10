#!/bin/bash
# _t1_bringup_only.sh — 티원 turtlebot3 bringup만 복구 (odom→base_footprint tf 복원)
#   RealSense/d2scan/throttle/slam은 건드리지 않음. 주의: set -u 금지.
# Run on 티원: bash /tmp/_t1_bringup_only.sh <LAPTOP_IP>
PEER="${1:-192.168.10.59}"
# 죽은/좀비 bringup 잔재 정리 (라이다 driver 포함)
for p in turtlebot3_ros diff_drive single_coin_d4 robot_state_publisher hlds ld08; do pkill -9 -f "$p" 2>/dev/null; done
sleep 3

cat > /tmp/_t_bringup.sh <<EOF
#!/bin/bash
source /opt/ros/jazzy/setup.bash
source \$HOME/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=$PEER
exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1 usb_port:=/dev/ttyACM0
EOF
chmod +x /tmp/_t_bringup.sh
setsid nohup bash /tmp/_t_bringup.sh > /tmp/t_bringup.log 2>&1 </dev/null &
sleep 14

source /opt/ros/jazzy/setup.bash; source $HOME/turtlebot3_ws/install/setup.bash 2>/dev/null
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
ros2 daemon stop>/dev/null 2>&1; ros2 daemon start>/dev/null 2>&1; sleep 3
{
  echo -n "turtlebot3_node 노드: "; ros2 node list 2>/dev/null | grep -c turtlebot3_node
  echo "=== base_footprint tf 복원? ==="
  timeout 8 ros2 run tf2_ros tf2_echo tb3_1/base_footprint camera_depth_frame 2>&1 | grep -iE "Translation|does not exist" | head -2
  echo -n "slam 드롭(최근6): "; tail -6 /tmp/t_slamtb.log 2>/dev/null | grep -ci dropping
  echo "/map: "; timeout 6 ros2 topic echo /map --once --field info 2>/dev/null | grep -E "width|height" | head -2
} > /tmp/bringup_check.txt 2>&1
echo DONE
