#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT="${ROBOT:-geng}"
source "${ROOT}/scripts/env.sh"

PATROL_IGNORE_YAW="${PATROL_IGNORE_YAW:-1}"
DEFAULT_YAW_TOLERANCE="${DEFAULT_YAW_TOLERANCE:-0.25}"
DEFAULT_XY_TOLERANCE="${DEFAULT_XY_TOLERANCE:-0.05}"
PATROL_XY_TOLERANCE="${PATROL_XY_TOLERANCE:-0.08}"

restore_yaw_tolerance() {
  if [[ "${PATROL_IGNORE_YAW}" == "1" ]]; then
    timeout 5 ros2 param set /controller_server goal_checker.yaw_goal_tolerance "${DEFAULT_YAW_TOLERANCE}" >/dev/null 2>&1 || true
  fi
  timeout 5 ros2 param set /controller_server goal_checker.xy_goal_tolerance "${DEFAULT_XY_TOLERANCE}" >/dev/null 2>&1 || true
}
trap restore_yaw_tolerance EXIT INT TERM

if [[ "${PATROL_IGNORE_YAW}" == "1" ]]; then
  echo "==> 순찰 1번 yaw 적용, 2번 이후 yaw 정렬 생략"
fi
timeout 5 ros2 param set /controller_server goal_checker.xy_goal_tolerance "${PATROL_XY_TOLERANCE}" >/dev/null

echo "==> Gen.G FollowWaypoints 순찰"
python3 "${ROOT}/scripts/run_patrol.py" "$@"
