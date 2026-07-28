#!/usr/bin/env bash
# 멀티볼륨 TS 압축 해제 (비대화형 — TS.z02~z05 없으면 즉시 안내 후 종료)
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ROOT="${1:-${WS_DIR}/datasets/aihub_71472}"
LOG="${ROOT}/extract_ts.log"
TRAIN_SRC="${ROOT}/058.화재영상_3D_객체_데이터_생성/01-1.정식개방데이터/Training/01.원천데이터"

exec > >(tee -a "${LOG}") 2>&1

echo "[INFO] Extract start: $(date)"
df -h "${WS_DIR}" | tail -1

if [[ ! -d "${TRAIN_SRC}" ]]; then
  echo "[ERROR] Training source dir not found: ${TRAIN_SRC}" >&2
  exit 1
fi

cd "${TRAIN_SRC}"

# 이전 중단 잔여물 정리
rm -f TS_merged.zip

PARTS=(TS.z01 TS.z02 TS.z03 TS.z04 TS.z05 TS.zip)
MISSING=()
for part in "${PARTS[@]}"; do
  if [[ -f "${part}" ]]; then
    echo "[OK]   ${part} ($(du -h "${part}" | cut -f1))"
  else
    echo "[MISS] ${part}"
    MISSING+=("${part}")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo ""
  echo "============================================================"
  echo "[STOP] 멀티볼륨 ZIP은 6개 권이 모두 있어야 합니다."
  echo "       없는 파일: ${MISSING[*]}"
  echo ""
  echo "  zip -s 0 은 TS.z02 없으면 대화형으로 멈춥니다 (Ctrl+C로 끊긴 상황)."
  echo ""
  echo "  다음 다운로드 (API 키 설정 후):"
  echo "    ./scripts/download_aihub_plan.sh 4   # TS.z02 (100GB)"
  echo "    ./scripts/download_aihub_plan.sh 5   # TS.z03"
  echo "    ./scripts/download_aihub_plan.sh 6   # TS.z04"
  echo "    ./scripts/download_aihub_plan.sh 7   # TS.z05"
  echo ""
  echo "  지금 당장 학습하려면 (검증 세트, 이미 받음):"
  echo "    ./scripts/train_validation_now.sh"
  echo "============================================================"
  exit 1
fi

echo "[INFO] Merging 6 parts → TS_merged.zip (시간 오래 걸림)"
zip -s 0 TS.zip --out TS_merged.zip < /dev/null

echo "[INFO] Unzipping TS_merged.zip ..."
UNZIP_DISABLE_ZIPBOMB_DETECTION=TRUE unzip -o -q TS_merged.zip -d "${TRAIN_SRC}"

echo "[INFO] Freeing disk: remove merged zip"
rm -f TS_merged.zip

jpg_count=$(find "${TRAIN_SRC}" -name '*.jpg' 2>/dev/null | wc -l)
echo "[INFO] Training JPG count: ${jpg_count}"
echo "[INFO] Extract done: $(date)"
df -h "${WS_DIR}" | tail -1
