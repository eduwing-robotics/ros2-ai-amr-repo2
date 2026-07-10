#!/bin/bash
# _pose_ep_up.sh — AMCL tf(map→<id>/base_footprint)를 /<id>/pose로 발행 + (옵션) ros_tcp_endpoint 기동.
#   AMCL 경로(robot_pose_publisher.py)용 백그라운드 런처. odom-only 경로의 _robot_up.sh 대응.
#   ssh 인라인 setsid는 세션 종료 시 죽으므로 반드시 파일로 실행한다.
# 사용: bash _pose_ep_up.sh <id: tb3_1|tb3_2> [endpoint: yes|no] [domain]
# 주의: set -u 금지(setup.bash 미정의 참조). 도메인은 bringup/amcl 때 쓴 값과 일치시킬 것(로봇별 분리 운영 중).
set +u
ID="$1"; EP="${2:-no}"; DOM="${3:-210}"
if [ -z "$ID" ]; then echo "usage: _pose_ep_up.sh <tb3_1|tb3_2> [yes|no] [domain]"; exit 1; fi
source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash" 2>/dev/null
export ROS_DOMAIN_ID=$DOM RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

pkill -9 -f "[r]obot_pose_publisher" 2>/dev/null
setsid nohup python3 "$HOME/robot_pose_publisher.py" --robot "$ID" --root map --target "$ID/base_footprint" \
  >"/tmp/pp_$ID.log" 2>&1 </dev/null &

if [ "$EP" = "yes" ]; then
  pkill -9 -f "[d]efault_server_endpoint" 2>/dev/null
  ROS_IP=$(hostname -I | awk '{print $1}')
  setsid nohup ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:="$ROS_IP" -p ROS_TCP_PORT:=10000 >/tmp/ep.log 2>&1 </dev/null &
fi
sleep 5
echo "PP-UP id=$ID ep=$EP  pp_procs=$(pgrep -af '[r]obot_pose_publisher' | wc -l)  ep_procs=$(pgrep -af '[d]efault_server_endpoint' | wc -l)"
echo "-- /tmp/pp_$ID.log:"; tail -2 "/tmp/pp_$ID.log" 2>/dev/null
