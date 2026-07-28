#!/usr/bin/env bash
# T1-only Nav2 RViz (2D Pose + Goal).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "${ROOT}/scripts/env.sh"
export ROBOT=t1
export ROS_DOMAIN_ID=2
export ROBOT_NS="${T1_ROBOT_NS:-tb3_1}"
RVIZ_CFG="${RVIZ_CFG:-${MUSEUM_NAV_WS}/rviz/nav2.rviz}"
echo "==> T1 Nav2 RViz (DOMAIN=${ROS_DOMAIN_ID} NS=${ROBOT_NS})"
exec rviz2 -d "${RVIZ_CFG}"
