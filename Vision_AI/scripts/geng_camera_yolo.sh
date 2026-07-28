#!/usr/bin/env bash
# All-in-one: remote-start Gen.G camera+JPEG, wait for topic, launch YOLO viewer.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOPIC="${CAMERA_TOPIC:-/tb3_2/camera/image_raw/compressed}"
WAIT_SEC="${WAIT_SEC:-45}"

echo "==> 1/3 Gen.G 카메라+JPEG 원격 기동"
"${ROOT}/scripts/start_geng_camera.sh"

echo "==> 2/3 토픽 대기 (${TOPIC}, max ${WAIT_SEC}s)"
export ROS_DOMAIN_ID="${GENJI_ROS_DOMAIN_ID:-1}"
export USE_CYCLONEDDS=1
export SKIP_ROS_MULTIMACHINE=1
set +u
# shellcheck source=/dev/null
source "${ROOT}/scripts/setup_ros_env.sh"
set -u
export ROS_DOMAIN_ID="${GENJI_ROS_DOMAIN_ID:-1}"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset ROS_LOCALHOST_ONLY CYCLONEDDS_URI

deadline=$((SECONDS + WAIT_SEC))
got=0
while (( SECONDS < deadline )); do
  if timeout 3 ros2 topic echo "${TOPIC}" --once >/dev/null 2>&1; then
    got=1
    break
  fi
  sleep 1
done
if [[ "${got}" != "1" ]]; then
  echo "[FAIL] ${TOPIC} 미수신 — DOMAIN/카메라 확인" >&2
  timeout 5 ros2 topic list 2>/dev/null | grep -E 'tb3_2/camera|image' || true
  exit 2
fi
echo "[OK] ${TOPIC} 수신"

echo "==> 3/3 YOLO 뷰어"
exec "${ROOT}/scripts/run_geng_yolo_live.sh" --camera-topic "${TOPIC}" "$@"
