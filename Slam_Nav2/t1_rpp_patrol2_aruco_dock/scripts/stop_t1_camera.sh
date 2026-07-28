#!/usr/bin/env bash
# Laptop → T1: stop remote RealSense + JPEG compressor (SSH).
#
# Usage:
#   cd ~/workspace/museum_nav_ws
#   ./scripts/stop_t1_camera.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"
SSH_T1="${SSH_T1:-${ROBOT_PROJECT}/scripts/ssh_t1.py}"

if [[ ! -f "${SSH_T1}" ]]; then
  echo "[FAIL] ssh_t1.py 없음: ${SSH_T1}" >&2
  exit 1
fi

echo "==> T1 RealSense 카메라 원격 종료 (SSH)"
python3 "${SSH_T1}" \
  'pkill -9 -f "realsense|jpeg_camera_compressor|realsense2_camera|launch_t1_realsense|realsense_compressed|realsense_only" 2>/dev/null || true
   sleep 1
   if pgrep -af "realsense|jpeg_camera" >/tmp/t1_cam_left.txt 2>/dev/null; then
     echo "[WARN] still running:"
     cat /tmp/t1_cam_left.txt
     exit 1
   fi
   echo "[OK] T1 camera stopped"' \
  || {
    echo "[WARN] T1 카메라 SSH 종료 실패 — 로봇에서 수동 pkill" >&2
    exit 1
  }
