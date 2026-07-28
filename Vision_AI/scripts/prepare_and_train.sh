#!/usr/bin/env bash
# TS.z01 압축 해제 완료 후 학습 데이터 준비 + 학습 시작
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TRAINING_ROOT="${WS_DIR}/datasets/aihub_71472/058.화재영상_3D_객체_데이터_생성/01-1.정식개방데이터/Training"
OUTPUT="${WS_DIR}/datasets/museum_fire/processed"
EPOCHS="${EPOCHS:-50}"
BATCH="${BATCH:-8}"
DEVICE="${DEVICE:-cpu}"

# shellcheck source=/dev/null
source "${WS_DIR}/ros_env/bin/activate"

jpg_count=$(find "${TRAINING_ROOT}/01.원천데이터" -name '*.jpg' 2>/dev/null | wc -l)
if [[ "${jpg_count}" -lt 100 ]]; then
  echo "[ERROR] Training images not found (${jpg_count} jpg). Run extract first:" >&2
  echo "  ./scripts/extract_ts_z01.sh" >&2
  exit 1
fi

echo "[INFO] Training JPG files: ${jpg_count}"
python3 "${WS_DIR}/ai_perception/yolo_detection/training/prepare_aihub_dataset.py" \
  --source "${TRAINING_ROOT}" \
  --output "${OUTPUT}" \
  --indoor-only \
  --val-ratio 0.1

python3 "${WS_DIR}/ai_perception/yolo_detection/training/train_museum_yolo.py" \
  --data "${OUTPUT}/data.yaml" \
  --epochs "${EPOCHS}" \
  --batch "${BATCH}" \
  --device "${DEVICE}" \
  --export-model "${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt"

echo "[OK] Weights: ${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt"
echo "     Robot:   ./scripts/launch_t1_realsense.sh"
echo "     Laptop:  MODEL_PATH=${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt ./scripts/launch_robot_test.sh run"
