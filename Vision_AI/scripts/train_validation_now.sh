#!/usr/bin/env bash
# 검증(Validation) 세트로 즉시 학습 — Training 원천 없이도 가능
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VAL_SRC="${WS_DIR}/datasets/aihub_71472/058.화재영상_3D_객체_데이터_생성/01-1.정식개방데이터/Validation"
OUTPUT="${WS_DIR}/datasets/museum_fire/validation_processed"
EPOCHS="${EPOCHS:-50}"
BATCH="${BATCH:-16}"
DEVICE="${DEVICE:-0}"

source "${WS_DIR}/ros_env/bin/activate"

if [[ ! -d "${VAL_SRC}" ]]; then
  echo "[ERROR] Validation data missing. Run: ./scripts/download_aihub_plan.sh 1" >&2
  exit 1
fi

python3 "${WS_DIR}/ai_perception/yolo_detection/training/prepare_aihub_dataset.py" \
  --source "${VAL_SRC}" \
  --output "${OUTPUT}" \
  --val-ratio 0.1

python3 "${WS_DIR}/ai_perception/yolo_detection/training/train_museum_yolo.py" \
  --data "${OUTPUT}/data.yaml" \
  --epochs "${EPOCHS}" \
  --batch "${BATCH}" \
  --device "${DEVICE}" \
  --export-model "${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt"

echo "[OK] ai_perception/yolo_detection/models/museum_fire_smoke.pt"
