#!/usr/bin/env bash
# 로봇 카메라 + 노트북 수신 자동 기동 (노트북에서 실행)
#
# 사전 1회:
#   bash scripts/install_laptop_vision_deps.sh
#   export ROBOT_SSH_PASSWORD='로봇비밀번호'
#
# 사용:
#   bash scripts/robot_vision_up.sh
#   bash scripts/robot_vision_up.sh check
#   bash scripts/robot_vision_up.sh yolo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-up}"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-210}"
export LAPTOP_IP="${LAPTOP_IP:-$(hostname -I | awk '{print $1}')}"
export ROBOT_IP="${ROBOT_IP:-192.168.20.101}"
export USE_CYCLONEDDS="${USE_CYCLONEDDS:-1}"

if [[ ! -f /opt/ros/jazzy/lib/librmw_cyclonedds_cpp.so ]]; then
  echo "[ERROR] 노트북에 CycloneDDS 없음. 먼저 실행:" >&2
  echo "  bash scripts/install_laptop_vision_deps.sh" >&2
  exit 1
fi

if [[ -z "${ROBOT_SSH_PASSWORD:-}" ]]; then
  echo "[ERROR] export ROBOT_SSH_PASSWORD='...' 설정 필요" >&2
  exit 1
fi

_sync_and_restart_robot() {
  echo "[1/4] Sync → robot..."
  python3 "${SCRIPT_DIR}/sync_to_robot.py"

  echo "[2/4] Robot: 카메라는 로봇 SSH에서 포그라운드 실행:"
  echo "  ssh t1@${ROBOT_IP} 'cd ~/workspace/robot_project && export ROS_DOMAIN_ID=${ROS_DOMAIN_ID} LAPTOP_IP=${LAPTOP_IP} USE_CYCLONEDDS=1 && ./scripts/launch_t1_realsense.sh'"
}

_check_camera() {
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/setup_ros_env.sh"
  bash "${SCRIPT_DIR}/check_robot_camera.sh"
}

case "${MODE}" in
  check)
    _check_camera
    ;;
  yolo)
    _check_camera
    exec "${SCRIPT_DIR}/launch_robot_test.sh" run
    ;;
  up|*)
    _sync_and_restart_robot
    echo "[3/4] Check stream..."
    if _check_camera; then
      echo ""
      echo "════════════════════════════════════════"
      echo "[OK] Robot vision ready!"
      echo "  YOLO:  bash scripts/robot_vision_up.sh yolo"
      echo "════════════════════════════════════════"
    else
      echo "[FAIL] robot: tail -30 /tmp/realsense.log" >&2
      exit 1
    fi
    ;;
esac
