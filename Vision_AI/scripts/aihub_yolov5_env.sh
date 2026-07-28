#!/usr/bin/env bash
# AI-Hub YOLOv5 (화재영상 3D 객체 데이터 생성) 경로 — source 후 사용
#
# 기본 위치: ~/Downloads/ai/AI 모델_1-018-058-001

export AIHUB_ROOT="${AIHUB_ROOT:-${HOME}/Downloads/ai/AI 모델_1-018-058-001}"
export AIHUB_YOLOV5_DIR="${AIHUB_ROOT}/1.AI모델 소스코드/yolov5"
export AIHUB_WEIGHTS="${AIHUB_ROOT}/2.학습모델파일/best_fire_yolov5s_results.pt"

if [[ ! -d "${AIHUB_YOLOV5_DIR}" ]]; then
  echo "[ERROR] YOLOv5 not found: ${AIHUB_YOLOV5_DIR}" >&2
  return 1 2>/dev/null || exit 1
fi
if [[ ! -f "${AIHUB_WEIGHTS}" ]]; then
  echo "[ERROR] Weights not found: ${AIHUB_WEIGHTS}" >&2
  return 1 2>/dev/null || exit 1
fi
