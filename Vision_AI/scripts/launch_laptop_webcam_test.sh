#!/usr/bin/env bash
# 노트북 웹캠으로 YOLO 테스트 (로봇 RealSense 없이)
#
# ★ 권장 (끊김 없음, 1개 터미널):
#   ./scripts/launch_laptop_webcam_test.sh preview
#
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-help}"
WEBCAM_DEVICE="${WEBCAM_DEVICE:-0}"
IMAGE_TOPIC="${IMAGE_TOPIC:-/camera/color/image_raw}"
MODEL_PATH="${MODEL_PATH:-${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt}"
YOLO_CONF="${YOLO_CONF:-0.25}"
SMOKE_CONF="${SMOKE_CONF:-0.45}"

source_ros() {
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/ros_multimachine_env.sh"
  source /opt/ros/jazzy/setup.bash
  if [[ -f "${WS_DIR}/install/setup.bash" ]]; then
    # shellcheck source=/dev/null
    source "${WS_DIR}/install/setup.bash"
  fi
}

case "${MODE}" in
  preview)
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/setup_ros_env.sh"
    echo "[INFO] 단일 프로세스 미리보기 (웹캠+YOLO+화면, 끊김 최소)"
    echo "[INFO] conf fire=${YOLO_CONF} smoke=${SMOKE_CONF} (단색 오탐 필터 적용)"
    exec python3 "${SCRIPT_DIR}/webcam_yolo_preview.py" \
      --device-index "${WEBCAM_DEVICE}" \
      --model "${MODEL_PATH}" \
      --conf "${YOLO_CONF}" \
      --smoke-conf "${SMOKE_CONF}" \
      --imgsz 640 \
      --infer-fps 12
    ;;
  webcam)
    source_ros
    if [[ ! -e "/dev/video${WEBCAM_DEVICE}" ]] && ! ls /dev/video* &>/dev/null; then
      echo "[ERROR] 웹캠을 찾을 수 없습니다. ls /dev/video* 확인" >&2
      exit 1
    fi
    echo "[INFO] 웹캠 device=${WEBCAM_DEVICE} → ${IMAGE_TOPIC}"
    exec python3 "${SCRIPT_DIR}/webcam_publisher.py" \
      --ros-args \
      -p device_index:="${WEBCAM_DEVICE}" \
      -p topic:="${IMAGE_TOPIC}" \
      -p fps:=30.0
    ;;
  help|*)
    cat <<EOF
노트북 웹캠 YOLO 테스트

  ★ 권장 (1터미널, 부드러운 화면):
    ./scripts/launch_laptop_webcam_test.sh preview

  라이터 테스트 팁:
    - 불꽃을 카메라 20~30cm 앞, 2~3초 유지
    - conf 낮추기: YOLO_CONF=0.15 ./scripts/launch_laptop_webcam_test.sh preview
    - 웹캠 변경: WEBCAM_DEVICE=1 ./scripts/launch_laptop_webcam_test.sh preview

EOF
    ;;
esac
