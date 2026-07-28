#!/usr/bin/env bash
# 노트북 카메라 수신용 환경 (T1 tb3_1, CycloneDDS — 로봇과 동일)
# 사용: source scripts/camera_laptop_env.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ROS_DOMAIN_ID=2
export LAPTOP_IP="${LAPTOP_IP:-$(hostname -I | awk '{print $1}')}"
export ROBOT_IP="${ROBOT_IP:-192.168.20.101}"
export ROBOT_NS=tb3_1
export USE_CYCLONEDDS=1
unset RMW_IMPLEMENTATION FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE

set +u
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/setup_ros_env.sh"
# ---------------------------------------------------------------------------
# TOPIC SAFETY — do not regress the previous bug:
#   Never overwrite /tb3_1/.../image_raw/compressed with missing
#   /camera/.../image_detect/compressed.
# setup_ros_env → ros_multimachine_env 가
#   /tb3_1/camera/color/image_raw/compressed  를 설정함
# (realsense_compressed.launch.py 기본과 동일). 덮어쓰지 말 것.
# CAMERA_TOPIC 이 있으면 그걸 우선. 단 image_detect 는 예전 버그 잔재라 무시.
# ---------------------------------------------------------------------------
if [[ "${CAMERA_TOPIC:-}" == *image_detect* ]]; then
  echo "[WARN] camera_laptop_env: ignoring CAMERA_TOPIC=${CAMERA_TOPIC} (use tb3_1 compressed)"
  unset CAMERA_TOPIC
fi
if [[ -n "${CAMERA_TOPIC:-}" ]]; then
  export T1_CAMERA_COMPRESSED="${CAMERA_TOPIC}"
fi
# Default MUST stay tb3_1 compressed (NOT image_detect). Never rewrite to image_detect.
export T1_CAMERA_COMPRESSED="${T1_CAMERA_COMPRESSED:-/${ROBOT_NS}/camera/color/image_raw/compressed}"
if [[ "${T1_CAMERA_COMPRESSED}" == *image_detect* ]]; then
  export T1_CAMERA_COMPRESSED="/${ROBOT_NS}/camera/color/image_raw/compressed"
fi
export T1_CAMERA_RAW="${T1_CAMERA_RAW:-/${ROBOT_NS}/camera/color/image_raw}"
export CAMERA_TOPIC="${T1_CAMERA_COMPRESSED}"
# Wi-Fi JPEG: SUBNET 고정 (OFF+URI면 hz=0)
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset CYCLONEDDS_URI
unset ROS_LOCALHOST_ONLY
# set -u 금지: colcon setup 재-source 시 COLCON_TRACE 오류

echo "[OK] Laptop camera env — RMW=${RMW_IMPLEMENTATION:-?} DOMAIN=${ROS_DOMAIN_ID} discovery=${ROS_AUTOMATIC_DISCOVERY_RANGE} laptop=${LAPTOP_IP} robot=${ROBOT_IP}"
echo "     topic: ${T1_CAMERA_COMPRESSED}"
echo "     check: bash scripts/check_robot_camera.sh"
echo "     view:  bash scripts/camera_go.sh view"
