#!/bin/bash
# _restart_nav_ns.sh — nav_ns_launch.py 스택만 깨끗이 재기동(로봇에서 실행).
# bringup(모터/라이다)이나 map_server/amcl은 안 건드림 — nav2 노드만 pkill 후 재실행.
# tf 리스너가 오래된 프로세스일수록 discovery 캐시가 꼬일 수 있어 재기동 후 다시 lifecycle
# configure→activate 필요([[urhynix-t1-nav2-lifecycle-abi]]).
for p in "[c]ontroller_server" "[p]lanner_server" "[b]ehavior_server" "[b]t_navigator" \
         "[w]aypoint_follower" "[v]elocity_smoother" "[c]ollision_monitor" "[s]moother_server" \
         "[r]oute_server" "[o]pennav_docking" "[l]ifecycle_manager" "[n]av_ns_launch"; do
  pkill -9 -f "$p" 2>/dev/null
done
sleep 3
unset AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH LD_LIBRARY_PATH PYTHONPATH ROS_PACKAGE_PATH
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
setsid nohup ros2 launch /home/t1/nav_ns_launch.py > /tmp/nav_tb3_1.log 2>&1 </dev/null &
echo RELAUNCHED_PID=$!
