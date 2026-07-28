#!/usr/bin/env bash
# T1-only ROS 2 environment (source only).
set -euo pipefail
_WS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROBOT=t1
export MUSEUM_NAV_WS="${MUSEUM_NAV_WS:-${_WS}}"
export ROS_DOMAIN_ID=2
export ROBOT_NS="${T1_ROBOT_NS:-tb3_1}"
export T1_HOST="${T1_HOST:-192.168.20.101}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=OFF
unset ROS_LOCALHOST_ONLY CYCLONEDDS_URI FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE ROS_STATIC_PEERS
_LOCAL_IP="$(ip -4 route get "${T1_HOST}" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')"
export ROS_STATIC_PEERS="${T1_HOST}${_LOCAL_IP:+;${_LOCAL_IP}};127.0.0.1"
unset _LOCAL_IP
set +u
source /opt/ros/jazzy/setup.bash
[[ -f "${MUSEUM_NAV_WS}/install/setup.bash" ]] && source "${MUSEUM_NAV_WS}/install/setup.bash"
[[ -f "${HOME}/turtlebot3_ws/install/setup.bash" ]] && source "${HOME}/turtlebot3_ws/install/setup.bash"
set -u
export MAP_YAML="${MAP_YAML:-${MUSEUM_NAV_WS}/maps/t1_map_new.yaml}"
export NAV2_PARAMS="${NAV2_PARAMS:-${MUSEUM_NAV_WS}/config/nav2_params_t1_patrol_rpp.yaml}"
export ROS_LOG_DIR="${ROS_LOG_DIR:-${MUSEUM_NAV_WS}/.ros-log}"
mkdir -p "${ROS_LOG_DIR}"
