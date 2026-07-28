#!/usr/bin/env bash
# T1 로봇 — RealSense 카메라만 (YOLO 없음, Pi 4 부하 최소화)
#
# 로봇에서 실행:
#   ./scripts/launch_t1_realsense.sh
#
# 노트북에서 YOLO:
#   ./scripts/launch_robot_test.sh run
#
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# DDS 멀티머신: setup_ros_env 보다 먼저 (로봇에서 LAPTOP_IP 오설정 방지)
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-2}"
export LAPTOP_IP="${LAPTOP_IP:-$(ip -4 route get "${ROBOT_IP}" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')}"
export ROBOT_IP="${ROBOT_IP:-192.168.20.101}"
export ROBOT_NS="${ROBOT_NS:-tb3_1}"
export USE_CYCLONEDDS="${USE_CYCLONEDDS:-1}"
if [[ "${LAPTOP_IP}" == "${ROBOT_IP}" ]]; then
  echo "[ERROR] LAPTOP_IP must be the laptop IP (not ${ROBOT_IP}). Example: export LAPTOP_IP=\$(hostname -I | awk '{print \$1}')" >&2
  exit 1
fi

if [[ -f "${SCRIPT_DIR}/setup_ros_env.sh" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/setup_ros_env.sh"
elif [[ -f "${HOME}/workspace/robot_project/scripts/setup_ros_env.sh" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/workspace/robot_project/scripts/setup_ros_env.sh"
  SCRIPT_DIR="${HOME}/workspace/robot_project/scripts"
else
  echo "[ERROR] setup_ros_env.sh 없음. T1 로봇의 robot_project 에서 실행하세요:" >&2
  echo "  cd ~/workspace/robot_project && ./scripts/launch_t1_realsense.sh" >&2
  exit 1
fi

echo "[INFO] Host: $(hostname) — RealSense camera only (no YOLO)"
echo "[INFO] ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "[INFO] RMW=${RMW_IMPLEMENTATION:-?} robot=${ROBOT_IP} laptop=${LAPTOP_IP}"

if ! ros2 pkg prefix museum_patrol_system >/dev/null 2>&1; then
  echo "[ERROR] 패키지 museum_patrol_system 을 찾을 수 없습니다." >&2
  echo "" >&2
  echo "  로봇 최초 1회 (노트북에서 코드 동기화 후):" >&2
  echo "    노트북: export ROBOT_SSH_PASSWORD='...' && ./scripts/sync_to_robot.sh" >&2
  echo "    로봇:   cd ~/workspace/robot_project && ./scripts/build_robot_package.sh" >&2
  echo "" >&2
  echo "  이후 카메라 실행:" >&2
  echo "    ./scripts/launch_t1_realsense.sh" >&2
  echo "" >&2
  echo "  ※ ros2 launch ... 직접 실행 시 install/setup.bash 가 안 잡힐 수 있습니다." >&2
  exit 1
fi

if lsusb 2>/dev/null | grep -q '8086:0b07'; then
  echo "[INFO] RealSense D435 detected (USB)"
else
  echo "[ERROR] RealSense D435 not found on this PC. Run on robot with USB connected." >&2
  exit 1
fi

# Pi 4: 기본 ultra(424x240) — USB 대역폭·전원 부담 최소화
if [[ -z "${CAMERA_QUALITY:-}" ]] && [[ "$(uname -m)" == "aarch64" ]]; then
  export CAMERA_QUALITY=ultra
  echo "[INFO] Pi detected — default CAMERA_QUALITY=ultra (424x240x6)"
fi

if [[ "$(uname -m)" == "aarch64" ]] && [[ ! -f /etc/udev/rules.d/99-realsense-usb.rules ]]; then
  echo "[WARN] Pi USB tuning 미적용 — 1회 실행 권장:"
  echo "       sudo ./scripts/setup_pi_usb_realsense.sh && sudo reboot"
fi

for pattern in webcam_publisher.py realsense_compressed.launch.py \
  realsense_only.launch.py realsense2_camera_node jpeg_compressor; do
  if pgrep -f "${pattern}" >/dev/null 2>&1; then
    echo "[INFO] Stopping: ${pattern}"
    pkill -f "${pattern}" || true
    sleep 1
  fi
done

if [[ "${REALSENSE_USB_RESET:-1}" == "1" ]] && [[ -x "${SCRIPT_DIR}/reset_realsense_usb.sh" ]]; then
  echo "[INFO] USB reset (REALSENSE_USB_RESET=0 to skip)..."
  sudo "${SCRIPT_DIR}/reset_realsense_usb.sh" || echo "[WARN] USB reset skipped/failed — 케이블·전원 확인"
  sleep 2
fi

# RealSense D435 RGB 지원 fps: 424x240 → 6/15/30 (5·10fps 없음 → 640x480x30 fallback)
# CAMERA_QUALITY: detect | ultra | low | medium | high
case "${CAMERA_QUALITY:-detect}" in
  detect|high)
    COLOR_PROFILE="${COLOR_PROFILE:-640x480x6}"
    ;;
  ultra)
    COLOR_PROFILE="${COLOR_PROFILE:-424x240x6}"
    ;;
  low)
    COLOR_PROFILE="${COLOR_PROFILE:-424x240x6}"
    ;;
  medium)
    COLOR_PROFILE="${COLOR_PROFILE:-424x240x15}"
    ;;
  *)
    COLOR_PROFILE="${COLOR_PROFILE:-640x480x6}"
    ;;
esac

# JPEG_STREAM=1 (기본): raw 대신 /compressed 토픽으로 Wi-Fi 전송 (~1/10 대역폭)
JPEG_STREAM="${JPEG_STREAM:-1}"
JPEG_QUALITY="${JPEG_QUALITY:-50}"
JPEG_MAX_FPS="${JPEG_MAX_FPS:-30}"
JPEG_TOPIC="${JPEG_TOPIC:-/camera/color/image_detect/compressed}"

echo "[INFO] Request profile: ${COLOR_PROFILE}"
echo "[INFO] JPEG stream: ${JPEG_STREAM} (quality=${JPEG_QUALITY}, max_fps=${JPEG_MAX_FPS})"
echo "[INFO] JPEG topic: ${JPEG_TOPIC}"
echo "[INFO] 화재 인식: CAMERA_QUALITY=detect (640x480x6)"
echo "[INFO] Wi-Fi 최소: CAMERA_QUALITY=ultra (424x240x6)"
echo "[INFO] 노트북: ./scripts/launch_robot_test.sh run"
if [[ "${JPEG_STREAM}" == "1" ]]; then
  echo "[INFO] Publish topic: ${JPEG_TOPIC} (JPEG)"
else
  echo "[INFO] Publish topic: /${ROBOT_NS}/camera/color/image_raw (raw)"
fi

if [[ "${JPEG_STREAM}" == "1" ]]; then
  exec ros2 launch museum_patrol_system realsense_compressed.launch.py \
    robot_namespace:="${ROBOT_NS}" \
    realsense_color_profile:="${COLOR_PROFILE}" \
    jpeg_quality:="${JPEG_QUALITY}" \
    jpeg_max_fps:="${JPEG_MAX_FPS}" \
    compressed_image_topic:="${JPEG_TOPIC}" \
    "$@"
fi

exec ros2 launch museum_patrol_system realsense_only.launch.py \
  robot_namespace:="${ROBOT_NS}" \
  realsense_color_profile:="${COLOR_PROFILE}" \
  "$@"
