#!/usr/bin/env bash
# Preflight for Gen.G ArUco dock — does NOT start bringup (operator powers robot).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"

echo "╔══════════════════════════════════════════════════╗"
echo "║ Gen.G ArUco dock preflight (bringup not started) ║"
echo "╚══════════════════════════════════════════════════╝"

fail=0
ping -c 1 -W 2 192.168.20.7 >/dev/null 2>&1 && echo "[OK] ping 192.168.20.7" || { echo "[FAIL] Gen.G not reachable"; fail=1; }

for f in \
  scripts/park_geng_aruco_stage.py \
  scripts/dock_geng_aruco.sh \
  scripts/aruco_marker_config.py \
  scripts/aruco_align_geng_bearing.py \
  scripts/rotate_geng_precise.py \
  scripts/dock_geng_rear_wall_long.py \
  scripts/go_nav2.sh \
  scripts/nav2_rviz.sh \
  config/nav2_params_geng_rpp.yaml \
  maps/museum_map.yaml \
  aruco_markers/markers.yaml \
  aruco_markers/geng_aruco_id12_5cm.png \
  aruco_markers/geng_aruco_id12_A4_5cm.png
do
  if [[ -e "${ROOT}/${f}" ]]; then
    echo "[OK] ${f}"
  else
    echo "[FAIL] missing ${f}"
    fail=1
  fi
done

echo ""
echo "After robot power-on:"
echo "  1) ${ROBOT_PROJECT}/scripts/robot_bringup_all.sh start geng"
echo "  2) ROBOT=geng ${ROOT}/scripts/go_nav2.sh"
echo "  3) ROBOT=geng ${ROOT}/scripts/nav2_rviz.sh   # 2D Pose Estimate"
echo "  4) Gen.G camera_ros under /tb3_2/camera (+ compressed if needed)"
echo "  5) ROBOT=geng ${ROOT}/scripts/dock_geng_aruco.sh"
echo ""
exit "${fail}"
