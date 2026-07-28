#!/bin/bash
# Gen.G ArUco camera on robot — matching RPi libcamera IPA proxy.
set -eo pipefail
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-1}"
export RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}"
unset ROS_LOCALHOST_ONLY
export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}"
export LIBCAMERA_LOG_LEVELS="*:WARN"
export LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${LD_LIBRARY_PATH:-}"
export LIBCAMERA_IPA_PROXY_PATH="/usr/local/libexec/libcamera"
export LIBCAMERA_IPA_MODULE_PATH="/usr/local/lib/aarch64-linux-gnu/libcamera/ipa"
source /opt/ros/jazzy/setup.bash
export LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${LD_LIBRARY_PATH}"

WIDTH="${CAMERA_WIDTH:-640}"
HEIGHT="${CAMERA_HEIGHT:-480}"
FORMAT="${CAMERA_FORMAT:-YUYV}"

pkill -9 -f camera_ros 2>/dev/null || true
pkill -9 -f raspberrypi_ipa 2>/dev/null || true
pkill -9 -f geng_jpeg_throttle 2>/dev/null || true
sleep 2

: > /tmp/geng_camera_node.log
nohup env \
  LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${LD_LIBRARY_PATH}" \
  LIBCAMERA_IPA_PROXY_PATH="/usr/local/libexec/libcamera" \
  LIBCAMERA_IPA_MODULE_PATH="/usr/local/lib/aarch64-linux-gnu/libcamera/ipa" \
  LIBCAMERA_LOG_LEVELS="*:WARN" \
  ROS_DOMAIN_ID="${ROS_DOMAIN_ID}" \
  RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION}" \
  ros2 run camera_ros camera_node --ros-args \
    -r __ns:=/tb3_2 \
    -p width:="${WIDTH}" \
    -p height:="${HEIGHT}" \
    -p format:="${FORMAT}" \
  >/tmp/geng_camera_node.log 2>&1 &
echo $! > /tmp/geng_camera_node.pid
sleep 6
echo "[OK] camera pid=$(cat /tmp/geng_camera_node.pid)"
tail -n 15 /tmp/geng_camera_node.log || true
timeout 5 ros2 topic hz /tb3_2/camera/image_raw --window 5 || true
