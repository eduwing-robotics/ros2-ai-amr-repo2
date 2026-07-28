#!/usr/bin/env bash
# AI-Hub 71472 단계별 다운로드 (용량 절약 플랜)
# 1) Validation VS+VL  2) TL 라벨  3) TS.z01 학습 원천 1/6
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEST="${WS_DIR}/datasets/aihub_71472"
AIHUB="${WS_DIR}/aihubshell"
API_KEY="${AIHUB_APIKEY:-}"

if [[ -z "${API_KEY}" ]]; then
  echo "[ERROR] Set AIHUB_APIKEY environment variable." >&2
  echo "  export AIHUB_APIKEY='your-api-key'" >&2
  exit 1
fi

if [[ ! -x "${AIHUB}" ]]; then
  echo "[ERROR] aihubshell not found at ${AIHUB}" >&2
  exit 1
fi

mkdir -p "${DEST}"
cd "${DEST}"

run_dl() {
  local step="$1"
  local filekeys="$2"
  local log="${DEST}/step_${step}.log"
  echo ""
  echo "========== Step ${step} (filekey=${filekeys}) =========="
  df -h "${WS_DIR}" | tail -1
  if "${AIHUB}" -mode d -datasetkey 71472 -aihubapikey "${API_KEY}" -filekey "${filekeys}" 2>&1 | tee "${log}"; then
    echo "[OK] Step ${step} complete"
    rm -f download.tar 2>/dev/null || true
    "${SCRIPT_DIR}/extract_aihub_zips.sh" "${DEST}" 2>/dev/null || true
    return 0
  fi
  echo "[FAIL] Step ${step} — see ${log}" >&2
  return 1
}

STEP="${1:-all}"

case "${STEP}" in
  1) run_dl 1 "496756,496757" ;;
  2) run_dl 2 "496309" ;;
  3) run_dl 3 "496303" ;;
  3b) run_dl 3b "496308" ;;
  4) run_dl 4 "496304" ;;  # TS.z02
  5) run_dl 5 "496305" ;;  # TS.z03
  6) run_dl 6 "496306" ;;  # TS.z04
  7) run_dl 7 "496307" ;;  # TS.z05
  all)
    run_dl 1 "496756,496757"
    run_dl 2 "496309"
    echo ""
    echo "[INFO] Step 3 (TS.z01 ~100GB) starting — may take 30+ minutes..."
    run_dl 3 "496303"
    ;;
  *)
    echo "Usage: AIHUB_APIKEY=... $0 [1|2|3|3b|4|5|6|7|all]" >&2
    exit 1
    ;;
esac

echo ""
echo "[DONE] Files in ${DEST}:"
du -sh "${DEST}"/* 2>/dev/null | head -20
find "${DEST}" -maxdepth 4 -type d 2>/dev/null | head -15
