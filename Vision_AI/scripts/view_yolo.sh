#!/usr/bin/env bash
# YOLO detection result viewer — /detect/image_raw
#
# rqt_image_view는 ros_env(ultralytics)가 필요 없으므로
# venv 없이 ROS 2만 로드해 GUI 충돌을 방지합니다.
#
# 사용법:
#   ./scripts/view_yolo.sh
#   ./scripts/view_yolo.sh /camera/depth/image_rect_raw/colored

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TOPIC="${1:-/detect/image_raw}"

# venv 비활성화 (이전 터미널에서 activate 된 경우 정리)
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  deactivate 2>/dev/null || true
  unset VIRTUAL_ENV
fi

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/ros_multimachine_env.sh"

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "[ERROR] ROS 2 Jazzy not found at /opt/ros/jazzy" >&2
  exit 1
fi

# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash

if [[ -f "${WS_DIR}/install/setup.bash" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/install/setup.bash"
fi

if ! ros2 pkg list 2>/dev/null | grep -qx rqt_image_view; then
  echo "[ERROR] rqt_image_view not installed." >&2
  echo "  Run: sudo apt install ros-jazzy-rqt-image-view" >&2
  exit 1
fi

echo "[INFO] Opening rqt_image_view on topic: ${TOPIC}"
echo "[IMPORTANT] 드롭다운에서 ${TOPIC} 선택 (/theora 토픽은 사용하지 마세요)"
echo "[INFO] Robot camera: ./scripts/launch_t1_realsense.sh"
echo "[INFO] Laptop YOLO:  ./scripts/launch_robot_test.sh run"
echo "[TIP]  rqt 창이 안 뜨면: python3 scripts/view_yolo_cv.py ${TOPIC}"

if ! timeout 10 ros2 topic list 2>/dev/null | grep -q "${TOPIC#/}"; then
  echo "[WARN] Topic ${TOPIC} not found yet. Check ROS_DOMAIN_ID and network."
  echo "       ros2 topic list | grep -E 'camera|detect'"
fi

ros2 run rqt_image_view rqt_image_view --clear-config "${TOPIC}" || {
  STATUS=$?
  echo "[ERROR] rqt_image_view exited with code ${STATUS}"
  read -r -p "Enter 키를 누르면 종료..."
  exit "${STATUS}"
}
