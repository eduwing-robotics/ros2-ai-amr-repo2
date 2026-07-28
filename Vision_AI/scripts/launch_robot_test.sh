#!/usr/bin/env bash
# 로봇 RealSense + 노트북 YOLO + 화면
#
# ★ 권장 (JPEG 압축 + YOLO, 터미널 2개):
#   로봇:  ./scripts/launch_t1_realsense.sh
#   노트북: ./scripts/launch_robot_test.sh run
#
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-help}"
MODEL_PATH="${MODEL_PATH:-${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt}"
PERSON_MODEL="${PERSON_MODEL:-yolov8n.pt}"
PERSON_CONF="${PERSON_CONF:-0.40}"
YOLO_CONF="${YOLO_CONF:-0.38}"
SMOKE_CONF="${SMOKE_CONF:-0.32}"
MODEL_CONF="${MODEL_CONF:-0.12}"

stop_local_webcam() {
  local stopped=0
  for pattern in webcam_publisher.py webcam_yolo_preview.py robot_yolo_viewer.py; do
    if pgrep -f "${pattern}" >/dev/null 2>&1; then
      echo "[INFO] 종료: ${pattern}"
      pkill -f "${pattern}" || true
      stopped=1
    fi
  done
  if [[ "${stopped}" -eq 1 ]]; then
    sleep 1
  fi
}

check_webcam_not_running() {
  if pgrep -f webcam_publisher.py >/dev/null 2>&1 \
    || pgrep -f webcam_yolo_preview.py >/dev/null 2>&1; then
    echo "[ERROR] 노트북 웹캠이 실행 중입니다. ./scripts/launch_robot_test.sh stop" >&2
    exit 1
  fi
}

source_ros() {
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/setup_ros_env.sh"
}

resolve_robot_image_topic() {
  {
    source_ros
  } >&2

  local topics=(
    "${T1_CAMERA_COMPRESSED:-/camera/color/image_detect/compressed}"
    '/camera/color/image_detect/compressed'
    '/camera/color/image_raw/compressed'
    '/camera/color/image_raw'
    '/tb3_1/camera/color/image_raw/compressed'
    '/tb3_1/camera/color/image_raw'
  )
  local t
  for t in "${topics[@]}"; do
    if timeout 8 ros2 topic list 2>/dev/null | grep -qx "${t}"; then
      echo "${t}"
      return 0
    fi
  done
  echo ''
}

case "${MODE}" in
  run)
    stop_local_webcam
    check_webcam_not_running
    TOPIC="$(resolve_robot_image_topic)"
    if [[ -z "${TOPIC}" ]]; then
      echo "[ERROR] 로봇 카메라 토픽 없음. 로봇에서 launch_t1_realsense.sh 실행" >&2
      exit 1
    fi
    # shellcheck source=/dev/null
    source "${SCRIPT_DIR}/setup_ros_env.sh"
    echo "[INFO] ★ 단일 프로세스 (카메라 1회 구독 + YOLO + 화면): ${TOPIC}"
    exec python3 "${SCRIPT_DIR}/robot_yolo_viewer.py" \
      --camera-topic "${TOPIC}" \
      --model "${MODEL_PATH}" \
      --person-model "${PERSON_MODEL}" \
      --conf "${YOLO_CONF}" \
      --smoke-conf "${SMOKE_CONF}" \
      --person-conf "${PERSON_CONF}" \
      --model-conf "${MODEL_CONF}" \
      --imgsz 640 \
      --upscale-min-width 640 \
      --fire-confirm-frames 2 \
      --smoke-confirm-frames 2 \
      --infer-fps 10 \
      --display-fps 12
    ;;
  stop)
    stop_local_webcam
    "${SCRIPT_DIR}/stop_demo.sh"
    ;;
  help|*)
    cat <<EOF
로봇 RealSense 테스트

  ★ YOLO Wi-Fi (노트북 터미널 1개):
    export ROS_DOMAIN_ID=210
    ./scripts/launch_robot_test.sh run

  로봇 (SSH) — 카메라 + JPEG (namespace tb3_1):
    export ROS_DOMAIN_ID=210
    ./scripts/launch_t1_realsense.sh

  토픽: /tb3_1/camera/color/image_raw/compressed
  YOLO: fire 2프레임 확정, conf 0.38
EOF
    ;;
esac
