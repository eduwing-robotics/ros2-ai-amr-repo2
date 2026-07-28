#!/usr/bin/env bash
# GENG-only Nav2 RViz (2D Pose + Goal).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT}/scripts/env.sh"
export ROBOT=geng
export ROS_DOMAIN_ID=1
export ROBOT_NS="${GENG_ROBOT_NS:-tb3_2}"
RVIZ_CFG="${RVIZ_CFG:-${MUSEUM_NAV_WS}/rviz/nav2.rviz}"
echo "==> GENG Nav2 RViz (DOMAIN=${ROS_DOMAIN_ID} NS=${ROBOT_NS})"
exec rviz2 -d "${RVIZ_CFG}"
