#!/bin/bash
# _robot_up.sh — odom-only 단일로봇 기동(로봇에서 실행): 기존정리 → ns bringup → odom_to_pose [→ endpoint].
# dual_marker_up.sh가 odom_to_pose.py와 함께 scp 후 호출. AMCL 없음(충전소 도킹 전제, odom 원점=충전소).
# 사용: bash _robot_up.sh <ns: tb3_1|tb3_2> <ox> <oy> <endpoint: yes|no>
# 주의: set -u 금지 — ROS setup.bash가 AMENT_TRACE_SETUP_FILES 미정의 참조라 깨짐.
NS=$1; OX=$2; OY=$3; EP=${4:-no}
source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash"
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

# 기존 우리 프로세스 정리. bracket 트릭 + 이 스크립트 cmdline엔 비-bracket 키워드 없음(파일이라 안전).
for p in "[o]dom_to_pose" "[r]obot.launch" "[t]urtlebot3_ros" "[t]urtlebot3_bringup" "[c]oin_d4" "[s]ingle_coin" "[r]obot_state_publisher" "[d]efault_server_endpoint"; do
  pkill -9 -f "$p" 2>/dev/null
done
sleep 2

setsid nohup ros2 launch turtlebot3_bringup robot.launch.py namespace:="$NS" usb_port:=/dev/ttyACM0 > "/tmp/bu_$NS.log" 2>&1 </dev/null &
sleep 9   # gyro 캘리브레이션 + Run! 대기
setsid nohup python3 /tmp/odom_to_pose.py --robot "$NS" --ox "$OX" --oy "$OY" > "/tmp/pose_$NS.log" 2>&1 </dev/null &

if [ "$EP" = "yes" ]; then
  ROS_IP=$(hostname -I | awk '{print $1}')
  setsid nohup ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:="$ROS_IP" -p ROS_TCP_PORT:=10000 > /tmp/ep.log 2>&1 </dev/null &
fi
echo "UP ns=$NS offset=($OX,$OY) endpoint=$EP"
