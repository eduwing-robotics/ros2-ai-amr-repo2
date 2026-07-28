#!/usr/bin/env bash
# AI-Hub YOLOv5 (fire/smoke) — 노트북 웹캠 테스트
#
#   ./scripts/webcam_aihub_yolov5_test.sh
#   SMOKE_CONF=0.18 ./scripts/webcam_aihub_yolov5_test.sh
#
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/aihub_yolov5_env.sh"

if [[ -f "${WS_DIR}/ros_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/ros_env/bin/activate"
fi

python3 -c "import pandas, tqdm" 2>/dev/null || pip install -q pandas seaborn thop tqdm

FIRE_CONF="${FIRE_CONF:-0.38}"
SMOKE_CONF="${SMOKE_CONF:-0.18}"
MODEL_CONF="${MODEL_CONF:-0.12}"
IMGSZ="${IMGSZ:-416}"
DEVICE="${DEVICE:-0}"

echo "[INFO] AI-Hub YOLOv5 webcam test"
echo "[INFO] Weights: ${AIHUB_WEIGHTS}"
echo "[INFO] fire=${FIRE_CONF} smoke=${SMOKE_CONF} nms=${MODEL_CONF} imgsz=${IMGSZ}"
echo "[INFO] 밝은 얼굴/역광 fire 오탐 필터 ON. Q 종료."

exec python3 "${SCRIPT_DIR}/webcam_aihub_yolov5_preview.py" \
  --fire-conf "${FIRE_CONF}" \
  --smoke-conf "${SMOKE_CONF}" \
  --model-conf "${MODEL_CONF}" \
  --imgsz "${IMGSZ}" \
  --device "${DEVICE}"
