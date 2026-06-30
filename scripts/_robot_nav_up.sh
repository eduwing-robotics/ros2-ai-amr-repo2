#!/bin/bash
# _robot_nav_up.sh — AMCL+Nav2 단일로봇 한방 기동(로봇에서 실행). non-ns(단일) 전제 → 표준 런치 그대로.
# 하는 일: 기존정리 → bringup(라이다+모터) → turtlebot3_navigation2(amcl+map_server+planner/controller/bt) →
#          초기포즈(충전소) 발행 → robot_pose_publisher(/<id>/pose) → patrol_waypoints_bridge [→ endpoint].
# nav_up.sh가 robot_pose_publisher.py+patrol_waypoints_bridge.py+맵과 함께 scp 후 호출.
# 사용: bash _robot_nav_up.sh <id: tb3_2> <ix> <iy> <iyaw_deg> <endpoint: yes|no>
# 주의: set -u 금지(ROS setup.bash가 AMENT_TRACE_SETUP_FILES 미정의 참조라 깨짐).
# ★듀얼 확장 시: ns 분리 + scan_frame_fix + 네임스페이스 nav2 param surgery 필요(지금은 단일이라 생략).
ID=$1; IX=$2; IY=$3; IYAW=${4:-0}; EP=${5:-no}
MAP="${6:-$HOME/maps/arena_v4/map.yaml}"   # 6번째 인자로 맵 override (예: ~/maps/map5/map5.yaml)
source /opt/ros/jazzy/setup.bash
source "$HOME/turtlebot3_ws/install/setup.bash"
export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

# 기존 우리 프로세스 정리. bracket 트릭 + 이 파일 cmdline엔 비-bracket 키워드 없음(파일이라 안전).
# ★nav2는 component_container_isolated 한 프로세스 안에 amcl/bt_navigator 등을 컴포넌트로 담는다.
#   개별 노드명으로 pkill하면 컨테이너를 못 잡아 재실행마다 nav2가 중복 누적 → lifecycle 충돌.
#   반드시 "component_container"로 컨테이너 자체를 죽인다(2026-06-25 중복누적 디버그).
for p in "[o]dom_to_pose" "[r]obot_pose_publisher" "[p]atrol_waypoints_bridge" "[s]can_frame_fix" \
         "[c]omponent_container" "[r]clcpp_component" "[n]avigation2.launch" \
         "[r]obot.launch" "[t]urtlebot3_ros" "[t]urtlebot3_bringup" \
         "[c]oin_d4" "[s]ingle_coin" "[r]obot_state_publisher" "[d]efault_server_endpoint" \
         "[a]mcl" "[m]ap_server" "[p]lanner_server" "[c]ontroller_server" "[b]t_navigator" \
         "[l]ifecycle_manager" "[b]ehavior_server" "[w]aypoint_follower" "[v]elocity_smoother"; do
  pkill -9 -f "$p" 2>/dev/null
done
sleep 3

if [ ! -f "$MAP" ]; then echo "맵 없음: $MAP (nav_up.sh가 scp했는지 확인)"; exit 1; fi

# 1) bringup (라이다 /scan + 모터 + tf base_footprint). non-ns.
setsid nohup ros2 launch turtlebot3_bringup robot.launch.py usb_port:=/dev/ttyACM0 \
  > "/tmp/bu_$ID.log" 2>&1 </dev/null &
sleep 10   # gyro 캘리브레이션 + Run! 대기

# 2) Nav2 풀스택(amcl+map_server+planner+controller+bt_navigator+lifecycle_manager autostart).
# ★nav2는 /opt만 source한 서브셸에서 기동. 워크스페이스 오버레이의 turtlebot3_navigation2가
#   깨져(launch symlink + param/burger.yaml 누락) /opt를 가림 → 패키지명/내부 share 경로가 죄다
#   오버레이로 가서 FileNotFoundError. /opt-only 소싱이면 get_package_share_directory가 /opt로 해석.
#   (bringup은 coin_d4 때문에 워크스페이스 필요하므로 분리; nav2는 /scan 토픽으로만 통신.)
# ★서브셸은 부모 AMENT_PREFIX_PATH를 상속하므로 /opt만 다시 source해도 오버레이가 안 빠짐 →
#   ament 경로를 unset 후 /opt만 fresh source해야 패키지 탐색이 깨끗한 /opt로 해석됨.
# ★turtlebot3 navigation2.launch.py 대신 nav2_bringup bringup_launch.py 사용 — 전자는 rviz를 끼워
#   headless 로봇에서 rviz가 Qt 없어 죽고 재시작 반복하며 CPU를 갉아 controller_server configure가
#   타임아웃(async_send_request)으로 실패. bringup_launch.py는 rviz 없는 정식 헤드리스 런치(2026-06-25).
NAV_LAUNCH=/opt/ros/jazzy/share/nav2_bringup/launch/bringup_launch.py
NAV_PARAMS=/opt/ros/jazzy/share/turtlebot3_navigation2/param/burger.yaml
setsid nohup bash -c "unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH LD_LIBRARY_PATH PYTHONPATH ROS_PACKAGE_PATH; source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; exec ros2 launch '$NAV_LAUNCH' map:='$MAP' params_file:='$NAV_PARAMS' use_sim_time:=false autostart:=true" \
  > "/tmp/nav_$ID.log" 2>&1 </dev/null &
sleep 14   # lifecycle active 대기(patrol bridge가 waitUntilNav2Active로 한번 더 보장)

# 3) 초기포즈 = 충전소. yaw(도)→quaternion. AMCL이 여기서 출발해 회전으로 수렴.
read QZ QW < <(python3 -c "import math;y=math.radians($IYAW);print(math.sin(y/2),math.cos(y/2))")
ros2 topic pub --times 8 -r 2 /initialpose geometry_msgs/msg/PoseWithCovarianceStamped \
  "{header: {frame_id: 'map'}, pose: {pose: {position: {x: $IX, y: $IY, z: 0.0}, orientation: {z: $QZ, w: $QW}}, covariance: [0.25,0,0,0,0,0, 0,0.25,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0, 0,0,0,0,0,0.06853]}}}" \
  > /tmp/initpose.log 2>&1

# 4) tf(map→base_footprint) → /<id>/pose (Unity RobotPoseFeed가 구독).
setsid nohup python3 /tmp/robot_pose_publisher.py --robot "$ID" --root map --target base_footprint \
  > "/tmp/pose_$ID.log" 2>&1 </dev/null &

# 5) Unity goal_pose/patrol_waypoints → Nav2 goToPose/FollowWaypoints 브리지.
setsid nohup python3 /tmp/patrol_waypoints_bridge.py --robot "$ID" \
  > "/tmp/bridge_$ID.log" 2>&1 </dev/null &

# 6) Unity 연결용 endpoint(:10000).
if [ "$EP" = "yes" ]; then
  ROS_IP=$(hostname -I | awk '{print $1}')
  setsid nohup ros2 run ros_tcp_endpoint default_server_endpoint \
    --ros-args -p ROS_IP:="$ROS_IP" -p ROS_TCP_PORT:=10000 > /tmp/ep.log 2>&1 </dev/null &
fi
echo "UP id=$ID initpose=($IX,$IY,${IYAW}deg) endpoint=$EP map=$MAP"
echo "→ AMCL 수렴 안 맞으면: python3 /tmp/drive_rotate.py /cmd_vel 0.4 12  (제자리 회전)"
