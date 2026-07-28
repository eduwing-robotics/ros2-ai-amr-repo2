#!/usr/bin/env bash
# GENG-only Nav2 foreground launcher.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"
source "${ROOT}/scripts/env.sh"
source "${ROOT}/scripts/_common.sh"
export ROBOT=geng
export ROS_DOMAIN_ID=1
export ROBOT_NS="${GENG_ROBOT_NS:-tb3_2}"
START_BRINGUP="${START_BRINGUP:-0}"
USE_SCAN_NORM="${USE_SCAN_NORM:-0}"
USE_EKF="${USE_EKF:-0}"
USE_LOCAL_ODOM_TF="${USE_LOCAL_ODOM_TF:-0}"
EKF_PARAMS="${EKF_PARAMS:-${ROOT}/config/ekf_odom.yaml}"
export MAP_YAML="${MAP_YAML:-${ROOT}/maps/museum_map.yaml}"
export NAV2_PARAMS="${NAV2_PARAMS:-${ROOT}/config/nav2_params_geng_rpp.yaml}"

if [[ ! -f "${MAP_YAML}" ]]; then
  echo "[FAIL] Map not found: ${MAP_YAML}"
  echo "       매핑 후: ./scripts/save_map.sh"
  exit 1
fi

fg_register_trap

# Clean stale local graph first. Restarting the ROS daemon after readiness checks
# drops DDS discovery and can make Nav2 start before odom TF is rediscovered.
pkill -f 'slam_toolbox|async_slam_toolbox|sync_slam_toolbox' 2>/dev/null || true
fg_stop_local_ros

if [[ "${START_BRINGUP}" == "1" ]]; then
  bash "${ROOT}/scripts/_ensure_robot_ready.sh" 90
fi

if [[ "${USE_SCAN_NORM}" == "1" ]]; then
  echo "==> Coin-D4 scan 재타임스탬프: /scan -> /scan_fixed"
  export SCAN_RESTAMP="${SCAN_RESTAMP:-0}"
  fg_start scan_normalize env SCAN_RESTAMP="${SCAN_RESTAMP}" \
    python3 "${ROOT}/scripts/scan_normalize.py" /scan /scan_fixed 400
  sleep 1
fi

if [[ "${USE_LOCAL_ODOM_TF}" == "1" ]]; then
  export RESTORE_ODOM_TF_ON_EXIT=1
  echo "==> 로컬 odom TF 사용: robot raw TF 비활성화 후 /odom relay 시작"
  relay_tf_ready=0
  for (( i = 0; i < 10; i++ )); do
    if timeout 5 ros2 param set /diff_drive_controller odometry.publish_tf false >/dev/null 2>&1; then
      relay_tf_ready=1
      break
    fi
    sleep 1
  done
  if [[ "${relay_tf_ready}" != "1" ]]; then
    echo "[FAIL] robot raw odom TF 비활성화 실패"
    exit 1
  fi
  fg_start odom_tf_relay python3 "${ROOT}/scripts/odom_tf_relay.py"
  if ! timeout 8 ros2 topic echo /odom --once >/dev/null 2>&1; then
    echo "[FAIL] /odom no data for local TF relay"
    exit 1
  fi
  if ! timeout 8 bash -c 'ros2 run tf2_ros tf2_echo odom base_footprint 2>&1 | grep -m1 -q -- "- Translation:"'; then
    echo "[FAIL] local odom TF relay output missing"
    exit 1
  fi
  echo "[OK] local /odom -> TF relay ready"
elif [[ "${USE_EKF}" == "1" ]]; then
  if [[ ! -f "${EKF_PARAMS}" ]]; then
    echo "[FAIL] EKF params not found: ${EKF_PARAMS}"
    exit 1
  fi

  export RESTORE_ODOM_TF_ON_EXIT=1
  echo "==> EKF odom 사용: raw odom TF 비활성화 후 robot_localization 시작"
  ekf_tf_ready=0
  for (( i = 0; i < 10; i++ )); do
    if timeout 5 ros2 param set /diff_drive_controller odometry.publish_tf false >/dev/null 2>&1; then
      ekf_tf_ready=1
      break
    fi
    sleep 1
  done
  if [[ "${ekf_tf_ready}" != "1" ]]; then
    echo "[FAIL] /diff_drive_controller odometry.publish_tf=false 설정 실패"
    echo "       EKF와 raw odom TF가 중복되면 TF가 더 꼬이므로 중단합니다."
    exit 1
  fi

  fg_start ekf_odom ros2 run robot_localization ekf_node \
    --ros-args -r __node:=ekf_filter_node --params-file "${EKF_PARAMS}"

  if ! timeout 8 ros2 topic echo /odometry/filtered --once >/dev/null 2>&1; then
    echo "[FAIL] /odometry/filtered no data (8s)"
    exit 1
  fi
  echo "[OK] EKF /odometry/filtered publisher ready"
else
  echo "==> EKF 비활성화: raw odom TF 사용"
  # odom→base_footprint 없으면 local_costmap 주황 느낌표 + 제자리 회전
  tf_pub=0
  for (( i = 0; i < 10; i++ )); do
    if timeout 5 ros2 param set /diff_drive_controller odometry.publish_tf true >/dev/null 2>&1; then
      tf_pub=1
      break
    fi
    sleep 1
  done
  if [[ "${tf_pub}" != "1" ]]; then
    echo "[WARN] publish_tf=true 설정 실패 — 로봇 bringup 노드 확인"
  fi
  if ! timeout 20 bash -c \
    'ros2 run tf2_ros tf2_echo odom base_footprint 2>&1 | grep -m1 -q -- "- Translation:"'; then
    echo "[FAIL] TF odom -> base_footprint 없음 — local_costmap/주행 불가"
    echo "       robot_bringup_all.sh restart ${ROBOT}"
    exit 1
  fi
  echo "[OK] TF odom -> base_footprint"
fi

echo "==> Nav2 (Ctrl+C 종료)  ROBOT=${ROBOT}  DOMAIN=${ROS_DOMAIN_ID}  NS=${ROBOT_NS:-none}  EKF=${USE_EKF} LOCAL_ODOM_TF=${USE_LOCAL_ODOM_TF}"
echo "    map=${MAP_YAML}"
echo "    params=${NAV2_PARAMS}"
ros2 launch "${ROOT}/launch/nav2_bringup.launch.py" \
  "map:=${MAP_YAML}" \
  "params_file:=${NAV2_PARAMS}" \
  use_sim_time:=false \
  autostart:=true &
nav_pid=$!
fg_add_child "${nav_pid}"

bash "${ROOT}/scripts/_nav2_wait_ready.sh" 180

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║ Nav2 실행 중 — 이 터미널은 Ctrl+C 로 종료                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ 터미널 2: ./scripts/nav2_rviz.sh                           ║"
echo "║ 터미널 3: ./scripts/nav2_check.sh                            ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  1) 로봇 정지 → RViz '2D Pose Estimate' (실제 위치·방향)     ║"
echo "║  2) 초록 파티클이 로봇 주변에 모이는지 확인                  ║"
echo "║  3) LaserScan(빨간/보라 점)이 벽과 겹치는지 확인             ║"
echo "║  4) 'Nav2 Goal' → 0.5~1m 짧은 goal                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

if ! wait "${nav_pid}"; then
  code=$?
  if [[ "${code}" -eq 130 || "${code}" -eq 143 ]]; then
    exit 0
  fi
  echo ""
  echo "[FAIL] Nav2 프로세스 비정상 종료 (exit=${code})"
  echo "       로그: ${ROS_LOG_DIR}/latest/"
  exit 1
fi
