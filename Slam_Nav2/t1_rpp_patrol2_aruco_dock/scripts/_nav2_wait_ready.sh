#!/usr/bin/env bash
# Wait until Nav2 lifecycle + robot odom/TF are ready before 2D Pose Estimate.
set -euo pipefail

TIMEOUT="${1:-60}"
deadline=$((SECONDS + TIMEOUT))
SCAN_TOPIC="${SCAN_TOPIC:-/scan}"

wait_lifecycle() {
  local node="$1"
  while (( SECONDS < deadline )); do
    local state
    state="$(ros2 lifecycle get "/${node}" 2>/dev/null || true)"
    if [[ "${state%% *}" == "active" ]]; then
      echo "[OK] ${node} active"
      return 0
    fi
    sleep 1
  done
  echo "[FAIL] ${node} not active (${TIMEOUT}s)"
  return 1
}

wait_topic_once() {
  local topic="$1"
  while (( SECONDS < deadline )); do
    if timeout 5 ros2 topic echo "${topic}" --once >/dev/null 2>&1; then
      echo "[OK] ${topic} flowing"
      return 0
    fi
    sleep 1
  done
  echo "[FAIL] ${topic} no data (${TIMEOUT}s)"
  return 1
}

wait_tf() {
  local remaining=$((deadline - SECONDS))
  if (( remaining <= 0 )); then
    echo "[FAIL] TF odom -> base_footprint (${TIMEOUT}s)"
    return 1
  fi

  # Keep one listener alive. Recreating tf2_echo every few seconds resets DDS
  # discovery, which is slow on the robot Wi-Fi and prevents /tf reception.
  if timeout "${remaining}" bash -c     'ros2 run tf2_ros tf2_echo odom base_footprint 2>&1 | grep -m1 -q -- "- Translation:"'; then
    echo "[OK] TF odom -> base_footprint"
    return 0
  fi

  echo "[FAIL] TF odom -> base_footprint (${TIMEOUT}s)"
  return 1
}

echo "==> Nav2 준비 대기 (최대 ${TIMEOUT}s)"

fail=0
# Robot /scan, /odom, and odom->base_footprint are verified by
# _ensure_robot_ready.sh before Nav2 starts. Waiting for fresh CLI subscribers
# here can consume the whole timeout on Wi-Fi and prevents RViz initial pose.
for node in map_server amcl controller_server; do
  wait_lifecycle "${node}" || fail=1
done

# The navigation lifecycle can pause while the global costmap waits for the
# initial map->odom transform. Requiring local costmap data here creates a
# startup deadlock: RViz must set the initial pose before navigation activates.

if [[ "${fail}" -ne 0 ]]; then
  echo ""
  echo "[FAIL] Nav2 localization 준비 실패"
  exit 1
fi

echo "[OK] RViz 2D Pose Estimate 가능 (로봇 가만히 둔 상태에서 클릭)"
exit 0
