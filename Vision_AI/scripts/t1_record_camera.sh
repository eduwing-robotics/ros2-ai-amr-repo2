#!/usr/bin/env bash
# T1 RealSense 녹화 헬퍼 (노트북)
# 사용:
#   source scripts/camera_laptop_env.sh
#   ./scripts/t1_record_camera.sh frames ~/Downloads/추가학습_로봇/사람 30
#   PREVIEW=0 ./scripts/t1_record_camera.sh frames ~/Downloads/추가학습_로봇/사람 30  # 창 없이
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/scripts/camera_laptop_env.sh"

MODE="${1:-frames}"
OUT="${2:-$HOME/datasets/t1_capture}"
SECS="${3:-60}"
FPS="${FPS:-5}"
PREVIEW="${PREVIEW:-1}"

case "${MODE}" in
  frames|video|both) ;;
  *)
    echo "usage: $0 frames|video|both <out> [secs]"
    exit 1
    ;;
esac

TOPIC="${T1_CAMERA_COMPRESSED:-/camera/color/image_detect/compressed}"
echo "==> check camera topic ${TOPIC}"
if ! timeout 8 ros2 topic echo "${TOPIC}" --once >/dev/null 2>&1; then
  echo "[FAIL] ${TOPIC} 없음"
  echo "       로봇: cd ~/workspace/robot_project && export LAPTOP_IP=192.168.20.4 && ./scripts/launch_t1_realsense.sh"
  exit 1
fi

PREVIEW_FLAG=()
if [[ "${PREVIEW}" == "1" || "${PREVIEW}" == "true" ]]; then
  PREVIEW_FLAG=(--preview)
fi

echo "==> record mode=${MODE} out=${OUT} secs=${SECS} fps=${FPS} preview=${PREVIEW} topic=${TOPIC}"
exec python3 "${ROOT}/scripts/t1_record_camera.py" \
  --mode "${MODE}" \
  --out "${OUT}" \
  --secs "${SECS}" \
  --fps "${FPS}" \
  --topic "${TOPIC}" \
  "${PREVIEW_FLAG[@]}"
