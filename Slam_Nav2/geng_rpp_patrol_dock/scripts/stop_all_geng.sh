#!/usr/bin/env bash
# Gen.G 전용 전체 종료 — 노트북 YOLO/Nav2/RViz/순찰 + Pi 카메라 + bringup.
#
# Usage:
#   cd ~/workspace/museum_nav_ws
#   ./scripts/stop_all_geng.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"
export ROBOT=geng

# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"
# shellcheck source=/dev/null
source "${ROOT}/scripts/_common.sh"

echo "╔══════════════════════════════════════════════════╗"
echo "║ museum_nav_ws — Gen.G 전체 종료                  ║"
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
  view_geng_camera \
  rqt_image_view \
  webcam_yolo_preview \
  webcam_aihub_yolov5 \
  launch_robot_test.sh; do
  pkill -f "${pat}" 2>/dev/null || true
done
pkill -9 -f robot_yolo_viewer.py 2>/dev/null || true

echo "==> 노트북 순찰·도킹 헬퍼 종료"
for pat in \
  run_patrol.py \
  run_patrol.sh \
  run_geng_patrol_aruco_dock \
  park_geng_aruco_stage.py \
  aruco_align_geng_bearing.py \
  rotate_geng_precise.py \
  dock_geng_aruco \
  dock_geng_rear_wall \
  go_nav2.sh \
  go_nav2_geng_rpp \
  nav2_rviz.sh \
  start_geng_camera; do
  pkill -f "${pat}" 2>/dev/null || true
done

fg_stop_local_ros

echo ""
echo "==> Gen.G Pi 카메라 종료"
bash "${ROOT}/scripts/stop_geng_camera.sh" || echo "[WARN] Gen.G 카메라 종료 실패 — 수동 확인"

if [[ -x "${ROBOT_PROJECT}/scripts/robot_bringup_all.sh" ]]; then
  echo ""
  echo "==> Gen.G bringup 종료"
  bash "${ROBOT_PROJECT}/scripts/robot_bringup_all.sh" stop geng || true
else
  echo "[WARN] robot_bringup_all.sh 없음 — bringup은 수동 종료"
fi

echo ""
echo "[OK] Gen.G 전체 종료 완료"
echo "     확인: pgrep -af 'robot_yolo_viewer|rviz2|go_nav2|camera_ros' || echo clean"
