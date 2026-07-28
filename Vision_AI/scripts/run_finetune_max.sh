#!/usr/bin/env bash
# DEBUG ONLY: 파인튜닝 모델 최대 감지 (필터/companion 해제 — 라이브 데모용 아님)
# 라이브 권장: ./scripts/run_finetune_live.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/scripts/camera_laptop_env.sh"

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

TOPIC="${USER_TOPIC:-${CAMERA_TOPIC:-${T1_CAMERA_COMPRESSED:-/tb3_1/camera/color/image_raw/compressed}}}"
echo "[INFO] YOLO camera topic: ${TOPIC}"

exec python3 "${ROOT}/scripts/robot_yolo_viewer.py" \
  --camera-topic "${TOPIC}" \
  --model "${ROOT}/ai_perception/yolo_detection/models/museum_finetune.pt" \
  --person-model '' \
  --max-detect \
  --model-conf 0.05 \
  --conf 0.08 \
  --person-conf 0.08 \
  --statue-conf 0.08 \
  "${PASS_ARGS[@]}"
