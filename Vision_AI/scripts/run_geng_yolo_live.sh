#!/usr/bin/env bash
# Gen.G museum_finetune live: fire/statue=finetune, person=yolov8n companion
#
# DOMAIN SAFETY — do NOT source camera_laptop_env.sh (that forces DOMAIN=2 / T1).
# Gen.G is ROS_DOMAIN_ID=1, ns=tb3_2, Cyclone + SUBNET.
#
# Topic default: /tb3_2/camera/image_raw/compressed
# Override: ./scripts/run_geng_yolo_live.sh --camera-topic <topic>
#
# Viewer defaults tuned for Wi-Fi JPEG (single BEST_EFFORT subscribe, queue depth 1):
#   --imgsz 640  --infer-fps 8  --display-fps 15
# Override via PASS_ARGS, e.g. --infer-fps 6
# Camera side (start_geng_camera): CAMERA_WIDTH/HEIGHT, JPEG_MAX_FPS, JPEG_QUALITY
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DEFAULT_TOPIC="/tb3_2/camera/image_raw/compressed"
FALLBACK_RAW="/tb3_2/camera/image_raw"

# Pin Gen.G DDS BEFORE setup_ros_env (which may source T1 multimachine defaults).
export ROS_DOMAIN_ID="${GENJI_ROS_DOMAIN_ID:-1}"
export USE_CYCLONEDDS=1
export SKIP_ROS_MULTIMACHINE=1
set +u
# shellcheck source=/dev/null
source "${ROOT}/scripts/setup_ros_env.sh"
set -u

# Force Gen.G multimachine after setup (Cyclone + SUBNET — not OFF+URI).
export ROS_DOMAIN_ID="${GENJI_ROS_DOMAIN_ID:-1}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset ROS_LOCALHOST_ONLY
unset CYCLONEDDS_URI
unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE

USER_TOPIC=""
PASS_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --camera-topic)
      USER_TOPIC="${2:-}"
      shift 2
      ;;
    --camera-topic=*)
      USER_TOPIC="${1#*=}"
      shift
      ;;
    *)
      PASS_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -n "${USER_TOPIC}" ]]; then
  TOPIC="${USER_TOPIC}"
else
  TOPIC="${CAMERA_TOPIC:-${DEFAULT_TOPIC}}"
  if [[ "${TOPIC}" == *image_detect* || -z "${TOPIC}" ]]; then
    TOPIC="${DEFAULT_TOPIC}"
  fi
fi

# Auto-fallback to raw if compressed has no publishers
if command -v ros2 >/dev/null 2>&1 && [[ -z "${USER_TOPIC}" ]]; then
  info="$(timeout 6 ros2 topic info "${TOPIC}" 2>/dev/null || true)"
  pubs="$(printf '%s\n' "${info}" | awk '/Publisher count:/ {print $3; exit}')"
  pubs="${pubs:-0}"
  if [[ "${pubs}" == "0" ]]; then
    raw_info="$(timeout 6 ros2 topic info "${FALLBACK_RAW}" 2>/dev/null || true)"
    raw_pubs="$(printf '%s\n' "${raw_info}" | awk '/Publisher count:/ {print $3; exit}')"
    raw_pubs="${raw_pubs:-0}"
    if [[ "${raw_pubs}" != "0" ]]; then
      echo "[WARN] No publishers on ${TOPIC}; falling back to ${FALLBACK_RAW}"
      TOPIC="${FALLBACK_RAW}"
      pubs="${raw_pubs}"
    fi
  fi
  echo "[INFO] Publisher count on ${TOPIC}: ${pubs}"
  if [[ "${pubs}" == "0" ]]; then
    echo "[WARN] No Gen.G camera publishers yet."
    echo "       Start camera: cd ~/workspace/museum_nav_ws && ./scripts/start_geng_camera.sh"
  fi
fi

export CAMERA_TOPIC="${TOPIC}"
echo "[INFO] Gen.G YOLO DOMAIN=${ROS_DOMAIN_ID} RMW=${RMW_IMPLEMENTATION} topic=${TOPIC}"

exec python3 "${ROOT}/scripts/robot_yolo_viewer.py" \
  --camera-topic "${TOPIC}" \
  --model "${ROOT}/ai_perception/yolo_detection/models/museum_finetune.pt" \
  --person-model yolov8n.pt \
  --conf 0.50 \
  --statue-conf 0.50 \
  --person-conf 0.75 \
  --model-conf 0.12 \
  --nms-iou 0.45 \
  --statue-nms-iou 0.25 \
  --statue-fragment-soft-iou 0.15 \
  --person-vs-statue-iou 0.10 \
  --person-vs-statue-soft-iou 0.015 \
  --person-vs-statue-pad 0.70 \
  --person-vs-statue-anchor-conf 0.08 \
  --person-vs-fire-iou 0.30 \
  --person-vs-fire-anchor-conf 0.22 \
  --person-in-frame-min-conf 0.78 \
  --reject-sculptural-person \
  --imgsz 640 \
  --upscale-min-width 640 \
  --infer-fps 8 \
  --display-fps 15 \
  "${PASS_ARGS[@]}"
