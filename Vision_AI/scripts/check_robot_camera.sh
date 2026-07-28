#!/usr/bin/env bash
# 로봇 카메라 토픽이 노트북에서 보이는지 빠른 점검
#
#   export ROS_DOMAIN_ID=210
#   bash scripts/check_robot_camera.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/setup_ros_env.sh"

# realsense_compressed.launch.py 기본 (JPEG compressor 출력)
export T1_CAMERA_COMPRESSED="${CAMERA_TOPIC:-${T1_CAMERA_COMPRESSED:-/tb3_1/camera/color/image_raw/compressed}}"
export T1_CAMERA_RAW="${T1_CAMERA_RAW:-/tb3_1/camera/color/image_raw}"

TOPIC="${1:-${T1_CAMERA_COMPRESSED}}"
RAW_TOPIC="${T1_CAMERA_RAW}"
STATUS=0
WAIT_SEC="${WAIT_SEC:-20}"

echo "[INFO] ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "[INFO] RMW=${RMW_IMPLEMENTATION:-default} robot=${ROBOT_IP} laptop=${LAPTOP_IP}"
echo ""

# stale graph 정리 (Publisher count=0 고스트 토픽 방지)
ros2 daemon stop >/dev/null 2>&1 || true
ros2 daemon start >/dev/null 2>&1 || true
sleep 1

if ! command -v ros2 >/dev/null 2>&1; then
  echo "[FAIL] ros2 없음 — source scripts/setup_ros_env.sh"
  exit 1
fi

check_one_topic() {
  local t="$1"
  echo "── ${t} ──"
  if ! ros2 topic list 2>/dev/null | grep -qx "${t}"; then
    echo "[SKIP] not in topic list"
    return 1
  fi
  ros2 topic info "${t}" 2>/dev/null | sed -n '1,6p' || true
  local pub
  pub="$(ros2 topic info "${t}" 2>/dev/null | awk '/Publisher count:/{print $3}')"
  if [[ "${pub}" == "0" ]]; then
    echo "[FAIL] Publisher count = 0 (토픽 이름만 보이고 송신기 없음)"
    return 1
  fi
  echo "[INFO] waiting up to ${WAIT_SEC}s for one message..."
  for qos in best_effort reliable; do
    for dur in volatile transient_local; do
      echo "[INFO]   try qos=${qos} durability=${dur}"
      if timeout "${WAIT_SEC}" ros2 topic echo "${t}" --once \
        --qos-reliability "${qos}" \
        --qos-durability "${dur}" \
        >/dev/null 2>&1; then
        echo "[OK] message received (qos=${qos} durability=${dur})"
        return 0
      fi
    done
  done
  if timeout "${WAIT_SEC}" ros2 topic hz "${t}" --window 5 2>/dev/null | grep -q 'average rate'; then
    echo "[OK] hz reports data (echo failed but stream active)"
    return 0
  fi
  echo "[FAIL] publisher=${pub} but no message in ${WAIT_SEC}s"
  return 1
}

if check_one_topic "${TOPIC}"; then
  echo ""
  echo "[OK] Camera stream OK on ${TOPIC}"
  exit 0
fi

echo ""
echo "[WARN] compressed failed — trying raw ${RAW_TOPIC}"
if check_one_topic "${RAW_TOPIC}"; then
  echo ""
  echo "[OK] Raw stream works. JPEG compressor on robot may be stopped."
  echo "     Robot: ./scripts/launch_t1_realsense.sh  (not realsense_only)"
  exit 0
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "[FAIL] No camera data on laptop."
echo ""
echo "로봇·노트북 둘 다 CycloneDDS (기준선 docs/t1_camera_wifi_baseline.md):"
echo "  export ROS_DOMAIN_ID=210"
echo "  export LAPTOP_IP=\$(hostname -I | awk '{print \$1}')   # 노트북 IP"
echo "  export USE_CYCLONEDDS=1"
echo "  source scripts/setup_ros_env.sh"
echo ""
echo "로봇 카메라 재시작:"
echo "  export ROS_DOMAIN_ID=210 LAPTOP_IP=<노트북IP> USE_CYCLONEDDS=1"
echo "  cd ~/workspace/robot_project && ./scripts/launch_t1_realsense.sh"
echo ""
echo "노트북 원클릭: bash scripts/camera_go.sh"
echo "════════════════════════════════════════════════════════"
exit 1
