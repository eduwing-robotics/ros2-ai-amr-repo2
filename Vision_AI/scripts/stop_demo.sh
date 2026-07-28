#!/usr/bin/env bash
# 로컬 데모/테스트 ROS 프로세스 일괄 종료
set -eo pipefail

patterns=(
  webcam_publisher.py
  webcam_yolo_preview.py
  test_camera_publisher.py
  "museum_patrol.launch.py"
  robot_yolo_viewer.py
)

for p in "${patterns[@]}"; do
  if pgrep -f "${p}" >/dev/null 2>&1; then
    echo "[INFO] Stopping: ${p}"
    pkill -f "${p}" || true
  fi
done

sleep 1
echo "[OK] Demo processes stopped."
