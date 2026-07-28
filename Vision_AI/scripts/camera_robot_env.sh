#!/usr/bin/env bash
# 로봇(T1) 카메라 송신용 환경 — CycloneDDS, 노트북 IP 고정
# 사용: source scripts/camera_robot_env.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-2}"
export ROBOT_IP="${ROBOT_IP:-192.168.20.101}"
export ROBOT_NS=tb3_1
export USE_CYCLONEDDS=1
export REALSENSE_USB_RESET=0
export CAMERA_QUALITY=ultra
export JPEG_STREAM=1

set +u
source /opt/ros/jazzy/setup.bash
[[ -f "${ROOT}/install/setup.bash" ]] && source "${ROOT}/install/setup.bash"
# shellcheck source=/dev/null
source "${ROOT}/scripts/ros_multimachine_env.sh"
# set -u 금지: colcon setup.bash 재-source 시 COLCON_TRACE 오류

echo "[OK] Robot camera env — RMW=${RMW_IMPLEMENTATION:-?} DOMAIN=${ROS_DOMAIN_ID} laptop=${LAPTOP_IP}"
