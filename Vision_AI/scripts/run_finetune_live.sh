#!/usr/bin/env bash
# museum_finetune live (권장): fire/statue=finetune, person=yolov8n companion
#
# TOPIC SAFETY — do not regress:
#   Hard default: /tb3_1/camera/color/image_raw/compressed
#   Only --camera-topic on the CLI may override.
#   Never auto-pick image_detect from ros2 topic list (discovery race).
#   Inherited CAMERA_TOPIC=*image_detect* is ignored.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export LAPTOP_IP="${LAPTOP_IP:-$(hostname -I | awk '{print $1}')}"
# shellcheck source=/dev/null
source "${ROOT}/scripts/camera_laptop_env.sh"

DEFAULT_TOPIC="/tb3_1/camera/color/image_raw/compressed"

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

# Ignore stale shell env that points at the old missing topic
if [[ "${CAMERA_TOPIC:-}" == *image_detect* ]]; then
  echo "[WARN] Ignoring CAMERA_TOPIC=${CAMERA_TOPIC} (image_detect). Using ${DEFAULT_TOPIC}"
  unset CAMERA_TOPIC
fi

if [[ -n "${USER_TOPIC}" ]]; then
  TOPIC="${USER_TOPIC}"
else
  # Prefer multimachine default; never scan topic list for image_detect
  TOPIC="${T1_CAMERA_COMPRESSED:-${DEFAULT_TOPIC}}"
  if [[ "${TOPIC}" == *image_detect* || -z "${TOPIC}" ]]; then
    TOPIC="${DEFAULT_TOPIC}"
  fi
fi

export CAMERA_TOPIC="${TOPIC}"
export T1_CAMERA_COMPRESSED="${TOPIC}"

echo "[INFO] YOLO camera topic: ${TOPIC}"
if command -v ros2 >/dev/null 2>&1; then
  info="$(timeout 6 ros2 topic info "${TOPIC}" 2>/dev/null || true)"
  pubs="$(printf '%s\n' "${info}" | awk '/Publisher count:/ {print $3; exit}')"
  pubs="${pubs:-0}"
  echo "[INFO] Publisher count on ${TOPIC}: ${pubs}"
  if [[ "${pubs}" == "0" ]]; then
    echo "[WARN] No publishers on ${TOPIC}."
    echo "       On robot: LAPTOP_IP=${LAPTOP_IP} ./scripts/launch_t1_realsense.sh"
    echo "       Or pass:  ./scripts/run_finetune_live.sh --camera-topic <actual_topic>"
  fi
fi

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
