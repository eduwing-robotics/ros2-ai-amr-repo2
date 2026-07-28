#!/usr/bin/env bash
# AI-Hub 화재 데이터 → YOLO 학습 일괄 실행
#
# 1) AI-Hub에서 데이터 다운로드·압축 해제 (수동, 계정 필요)
#    https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71472
#
# 2) 준비 + 학습:
#    AIHUB_SOURCE=~/Downloads/aihub_fire ./scripts/train_yolo.sh
#
# 3) 로봇에서 카메라 실행, 노트북에서 추론:
#    로봇:   ./scripts/launch_t1_realsense.sh
#    노트북: ./scripts/launch_robot_test.sh run

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AIHUB_SOURCE="${AIHUB_SOURCE:-}"
OUTPUT_DIR="${OUTPUT_DIR:-${WS_DIR}/datasets/museum_fire/processed}"
EPOCHS="${EPOCHS:-50}"
BATCH="${BATCH:-16}"
DEVICE="${DEVICE:-cpu}"

if [[ -f "${WS_DIR}/ros_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/ros_env/bin/activate"
fi

if [[ -z "${AIHUB_SOURCE}" ]]; then
  echo "[ERROR] Set AIHUB_SOURCE to unzipped AI-Hub dataset root." >&2
  echo "  Example: AIHUB_SOURCE=~/Downloads/aihub_fire ${0}" >&2
  exit 1
fi

python3 "${WS_DIR}/ai_perception/yolo_detection/training/prepare_aihub_dataset.py" \
  --source "${AIHUB_SOURCE}" \
  --output "${OUTPUT_DIR}" \
  --indoor-only \
  --val-ratio 0.1

python3 "${WS_DIR}/ai_perception/yolo_detection/training/train_museum_yolo.py" \
  --data "${OUTPUT_DIR}/data.yaml" \
  --epochs "${EPOCHS}" \
  --batch "${BATCH}" \
  --device "${DEVICE}" \
  --export-model "${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt"

echo "[OK] Training done. Weights: ${WS_DIR}/ai_perception/yolo_detection/models/museum_fire_smoke.pt"
