#!/bin/bash
# _robot_bringup_ns.sh — 네임스페이스 bringup 런처(로봇에서 실행). dual_bringup.launch.py를 env 세팅 후 호출.
# 기존 단일 non-ns 경로(_robot_nav_up.sh의 robot.launch.py)와 완전 별개 — 단일 경로 무수정.
# 동시 주행 전제: 각 로봇이 /<id>/{scan,odom,cmd_vel,...} 토픽 + <id>/* TF + /<id>/tf 트리로 격리.
# 사용: bash _robot_bringup_ns.sh <id: tb3_1|tb3_2> [usb_port] [domain_id]
#   예) 젠지:  bash _robot_bringup_ns.sh tb3_2
#       티원:  bash _robot_bringup_ns.sh tb3_1
# 주의: set -u 금지(ROS setup.bash가 미정의 변수 참조라 깨짐 — _robot_nav_up.sh와 동일).
set +u
ID=$1; USB=${2:-/dev/ttyACM0}; DOM=${3:-210}
if [ -z "$ID" ]; then echo "usage: _robot_bringup_ns.sh <tb3_1|tb3_2> [usb_port] [domain]"; exit 1; fi

# 우리 ns bringup 프로세스만 정리(기존 single-coin/turtlebot3_ros/rsp). bracket 트릭(이 파일 cmdline은 매칭 안 됨).
for p in "[s]ingle_coin_d4_node" "[t]urtlebot3_ros" "[r]obot_state_publisher" "[d]ual_bringup"; do
  pkill -9 -f "$p" 2>/dev/null
done
sleep 2

source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash"
export ROS_DOMAIN_ID=$DOM TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

LAUNCH="$HOME/dual_bringup.launch.py"   # nav_up.sh 패턴처럼 scp로 홈에 배치
if [ ! -f "$LAUNCH" ]; then echo "launch 없음: $LAUNCH (dual_bringup.launch.py scp 했는지 확인)"; exit 1; fi

setsid nohup ros2 launch "$LAUNCH" namespace:="$ID" usb_port:="$USB" \
  > "/tmp/nsbu_$ID.log" 2>&1 </dev/null &
sleep 12   # gyro 캘리브레이션 + lidar warmup 대기
echo "NS-BRINGUP id=$ID domain=$DOM → /$ID/scan(frame $ID/base_scan) /$ID/odom /$ID/tf"
echo "→ 확인: ROS_DOMAIN_ID=$DOM ros2 topic list | grep $ID ; ros2 run tf2_ros tf2_echo $ID/odom $ID/base_scan"
