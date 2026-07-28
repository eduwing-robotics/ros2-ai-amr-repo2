#!/usr/bin/env bash
# T1 전용 전체 종료 — 노트북 YOLO/Nav2/RViz/순찰 + 로봇 카메라 + bringup.
#
# Usage:
#   cd ~/workspace/museum_nav_ws
#   ./scripts/stop_all_t1.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"
export ROBOT=t1

# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"
# shellcheck source=/dev/null
source "${ROOT}/scripts/_common.sh"

echo "╔══════════════════════════════════════════════════╗"
echo "║ museum_nav_ws — T1 전체 종료                     ║"
echo "╚══════════════════════════════════════════════════╝"

# Zero cmd so last angular command cannot latch.
timeout 2 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
timeout 2 ros2 topic pub -r 20 /cmd_vel_nav geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true

echo "==> 노트북 YOLO / 카메라 뷰어 종료"
for pat in \
  robot_yolo_viewer.py \
  view_yolo \
  rqt_image_view \
  webcam_yolo_preview \
  webcam_aihub_yolov5 \
  launch_robot_test.sh; do
  pkill -f "${pat}" 2>/dev/null || true
done
# Stuck OpenCV windows
pkill -9 -f robot_yolo_viewer.py 2>/dev/null || true

echo "==> 노트북 순찰·도킹 헬퍼 종료"
for pat in \
  run_patrol.py \
  run_patrol_continuous.py \
  run_patrol.sh \
  run_t1_patrol2_aruco_dock \
  park_t1.py \
  aruco_align_t1.py \
  rotate_t1_precise.py \
  rotate_map_yaw.py \
  dock_t1_rear_wall \
  dock_t1_aruco \
  go_nav2.sh \
  nav2_rviz.sh; do
  pkill -f "${pat}" 2>/dev/null || true
done

fg_stop_local_ros

echo ""
echo "==> T1 RealSense 카메라 종료"
bash "${ROOT}/scripts/stop_t1_camera.sh" || echo "[WARN] T1 카메라 종료 실패 — 수동 확인"

if [[ -x "${ROBOT_PROJECT}/scripts/robot_bringup_all.sh" ]]; then
  echo ""
  echo "==> T1 bringup 종료"
  bash "${ROBOT_PROJECT}/scripts/robot_bringup_all.sh" stop t1 || true
else
  echo "[WARN] robot_bringup_all.sh 없음 — bringup은 수동 종료"
fi

echo ""
echo "[OK] T1 전체 종료 완료"
echo "     확인: pgrep -af 'robot_yolo_viewer|rviz2|go_nav2|realsense' || echo clean"
