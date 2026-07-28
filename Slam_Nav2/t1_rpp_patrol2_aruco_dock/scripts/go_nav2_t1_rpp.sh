#!/usr/bin/env bash
# T1 Nav2: RPP controller + raw odom TF (known-good patrol path).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROBOT="${ROBOT:-t1}"
export NAV2_PARAMS="${ROOT}/config/nav2_params_t1_patrol_rpp.yaml"
export MAP_YAML="${MAP_YAML:-${ROOT}/maps/t1_map_new.yaml}"
export USE_LOCAL_ODOM_TF="${USE_LOCAL_ODOM_TF:-0}"
export USE_SCAN_NORM="${USE_SCAN_NORM:-0}"
export USE_EKF="${USE_EKF:-0}"
export START_BRINGUP="${START_BRINGUP:-0}"
# Resolve behavior-tree absolute paths for this package layout.
PARAMS_SRC="${NAV2_PARAMS}"
PARAMS_RUNTIME="${ROOT}/.runtime_nav2_params_t1_patrol_rpp.yaml"
sed \
  -e "s|BEHAVIOR_TREE_NAV_TO_POSE|${ROOT}/behavior_trees/navigate_to_pose_narrow.xml|g" \
  -e "s|BEHAVIOR_TREE_NAV_THROUGH|${ROOT}/behavior_trees/navigate_through_poses_narrow.xml|g" \
  "${PARAMS_SRC}" > "${PARAMS_RUNTIME}"
export NAV2_PARAMS="${PARAMS_RUNTIME}"

exec "${ROOT}/scripts/go_nav2.sh" "$@"
