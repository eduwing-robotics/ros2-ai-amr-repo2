#!/usr/bin/env bash
# Gen.G: patrol x1 -> ArUco stage -> JPEG align -> 180° -> rear-wall dock.
# Mirrors 검증된 path (Gen.G 전용 순찰 경로) with Gen.G identity.
set -Eeo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export ROBOT=geng
# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"

stop_robot() {
  timeout 2 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
  timeout 2 ros2 topic pub -r 20 /cmd_vel_nav geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
}

failed() {
  status=$?
  echo "[FAIL] Gen.G 순찰/도킹 중단 (exit=${status})" >&2
  stop_robot
  exit "${status}"
}
trap failed ERR INT TERM

echo "===== 1/2 순찰 1회 ====="
python3 scripts/run_patrol.py

echo "===== 2/2 ArUco 도킹 ====="
bash scripts/dock_geng_aruco.sh

stop_robot
trap - ERR INT TERM
echo "[OK] Gen.G 순찰 및 ArUco 도킹 완료"
