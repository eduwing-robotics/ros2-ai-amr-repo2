#!/usr/bin/env bash
# YOLO 탐지 결과 화면 (/detect/image_raw) — 박스·라벨이 그려진 영상
#
# 터미널이 바로 닫히는 문제 방지:
#   - exec 사용 안 함 (오류 메시지를 볼 수 있게)
#   - ros_env(venv) 비활성화 — OpenCV/Qt 와 rclpy GUI 충돌 방지
#
# 사용법:
#   ./scripts/view_detect.sh              # rqt_image_view (권장, 안정적)
#   ./scripts/view_detect.sh --opencv     # OpenCV 창 (rqt 대안)

# set -u 는 ROS setup.bash 와 충돌 (AMENT_TRACE_SETUP_FILES unbound variable)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TOPIC="/detect/image_raw"
USE_OPENCV=0

if [[ "${1:-}" == "--opencv" ]]; then
  USE_OPENCV=1
elif [[ -n "${1:-}" ]]; then
  TOPIC="$1"
fi

# 이전 터미널에서 activate 된 venv 정리 (GUI 충돌 원인)
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  deactivate 2>/dev/null || true
  unset VIRTUAL_ENV
fi

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/ros_multimachine_env.sh"

if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "[ERROR] ROS 2 Jazzy not found at /opt/ros/jazzy" >&2
  read -r -p "Enter 키를 누르면 종료..."
  exit 1
fi

# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash

if [[ -f "${WS_DIR}/install/setup.bash" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/install/setup.bash"
fi

echo "[INFO] YOLO 결과 토픽: ${TOPIC}"
echo "[INFO] (원본 카메라: python3 scripts/view_yolo_cv.py /camera/color/image_raw)"

if ! timeout 8 ros2 topic list 2>/dev/null | grep -q "${TOPIC#/}"; then
  echo "[WARN] 토픽 ${TOPIC} 이(가) 아직 없습니다."
  echo "       YOLO 실행: ./scripts/launch_robot_test.sh run"
  echo "       ros2 topic list | grep detect"
fi

STATUS=0

if [[ "${USE_OPENCV}" -eq 1 ]]; then
  echo "[INFO] OpenCV 뷰어 시작..."
  python3 "${SCRIPT_DIR}/view_yolo_cv.py" "${TOPIC}" || STATUS=$?
elif ros2 pkg list 2>/dev/null | grep -qx rqt_image_view; then
  echo "[INFO] rqt_image_view 시작"
  echo "[IMPORTANT] 토픽은 반드시 ${TOPIC} 를 선택하세요."
  echo "            /theora 로 끝나는 토픽은 회색 화면만 나옵니다."
  echo "            (안 되면: ./scripts/view_detect.sh --opencv)"
  ros2 run rqt_image_view rqt_image_view --clear-config "${TOPIC}" || STATUS=$?
else
  echo "[WARN] rqt_image_view 미설치 — OpenCV 뷰어로 대체"
  echo "       설치: sudo apt install ros-jazzy-rqt-image-view"
  python3 "${SCRIPT_DIR}/view_yolo_cv.py" "${TOPIC}" || STATUS=$?
fi

if [[ "${STATUS}" -ne 0 ]]; then
  echo ""
  echo "[ERROR] 뷰어가 종료되었습니다 (코드 ${STATUS})"
  read -r -p "Enter 키를 누르면 종료..."
fi

exit "${STATUS}"
