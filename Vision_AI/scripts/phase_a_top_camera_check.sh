#!/usr/bin/env bash
# Phase A — T1 위쪽 마운트 RealSense depth+RGB 확인 (3D 맵핑 전)
#
# 1) 로봇(T1) — 저번과 동일 (JPEG Wi-Fi 스트림):
#    export ROS_DOMAIN_ID=210 LAPTOP_IP=<노트북IP>
#    cd ~/workspace/robot_project && ./scripts/launch_t1_realsense.sh
#    또는 백그라운드: ./scripts/phase_a_top_camera_check.sh robot-bg
#
# 2) 노트북 — 수신·뷰어:
#    cd ~/workspace/robot_project && ./scripts/phase_a_top_camera_check.sh laptop
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

_robot_ros_env() {
  set +u
  source /opt/ros/jazzy/setup.bash
  [[ -f "${ROOT}/install/setup.bash" ]] && source "${ROOT}/install/setup.bash"
  set -u
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-210}"
  export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_fastrtps_cpp}"
  export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}"
}

_laptop_ros_env() {
  set +u
  # shellcheck source=/dev/null
  source "${ROOT}/scripts/setup_ros_env.sh"
  set -u
}

ROBOT_NS="${ROBOT_NS:-tb3_1}"
COLOR_TOPIC="/${ROBOT_NS}/camera/color/image_raw/compressed"
COLOR_RAW="/${ROBOT_NS}/camera/color/image_raw"
DEPTH_TOPIC="/${ROBOT_NS}/camera/depth/image_rect_raw"
DEPTH_COLORED="/${ROBOT_NS}/camera/depth/image_rect_raw/colored"
LAPTOP_IP="${LAPTOP_IP:-$(hostname -I | awk '{print $1}')}"

_robot() {
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-210}"
  export LAPTOP_IP="${LAPTOP_IP:-$(ip -4 route get "${ROBOT_IP:-192.168.20.101}" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')}"
  export ROBOT_NS="${ROBOT_NS:-tb3_1}"
  export JPEG_STREAM="${JPEG_STREAM:-1}"
  export REALSENSE_USB_RESET="${REALSENSE_USB_RESET:-0}"
  # Pi 4: ultra(424x240) 기본 — 저번 Wi-Fi 순찰과 동일
  export CAMERA_QUALITY="${CAMERA_QUALITY:-ultra}"
  echo "[INFO] Phase A → launch_t1_realsense.sh (저번 방식, JPEG compressed)"
  exec "${ROOT}/scripts/launch_t1_realsense.sh" "$@"
}

_robot_bg() {
  exec "${ROOT}/scripts/launch_t1_realsense.sh"
}

_laptop_check() {
  _laptop_ros_env
  export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-210}"
  echo "[INFO] DOMAIN=${ROS_DOMAIN_ID} robot=${ROBOT_IP:-192.168.20.101}"
  ros2 daemon stop >/dev/null 2>&1 || true
  ros2 daemon start >/dev/null 2>&1 || true
  sleep 1

  echo ""
  echo "=== camera topics ==="
  ros2 topic list 2>/dev/null | grep -E "${ROBOT_NS}/camera" || echo "(none yet)"

  for t in "${COLOR_RAW}" "${COLOR_TOPIC}" "${DEPTH_TOPIC}"; do
    echo ""
    echo "── ${t} ──"
    if ! ros2 topic list 2>/dev/null | grep -qx "${t}"; then
      echo "[SKIP] not listed"
      continue
    fi
    pub="$(ros2 topic info "${t}" 2>/dev/null | awk '/Publisher count:/{print $3}')"
    echo "Publisher count: ${pub:-?}"
    if [[ "${pub}" != "0" && -n "${pub}" ]]; then
      timeout 6 ros2 topic hz "${t}" 2>&1 | tail -2 || true
    fi
  done

  echo ""
  echo "=== save RGB snapshot ==="
  if python3 "${ROOT}/scripts/debug_camera_frame.py" "${COLOR_TOPIC}"; then
    echo "[OK] /tmp/camera_debug.jpg"
  else
    echo "[WARN] RGB snapshot failed — robot launch running?"
  fi

  echo ""
  echo "=== live view (pick one) ==="
  echo "  ./scripts/view_yolo.sh ${COLOR_RAW}"
  echo "  ./scripts/view_yolo.sh ${DEPTH_TOPIC}"
}

case "${1:-laptop}" in
  robot) _robot ;;
  robot-bg|daemon) _robot_bg ;;
  laptop|check) _laptop_check ;;
  *)
    echo "Usage: $0 {robot|robot-bg|laptop}" >&2
    exit 1
    ;;
esac
