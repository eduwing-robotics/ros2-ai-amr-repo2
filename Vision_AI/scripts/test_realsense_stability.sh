#!/usr/bin/env bash
# Quick RealSense stability test on robot (30s)
set -eo pipefail
pkill -f realsense2_camera_node 2>/dev/null || true
pkill -f jpeg_compressor 2>/dev/null || true
sleep 2
cd ~/workspace/robot_project
export ROS_DOMAIN_ID=210 USE_CYCLONEDDS=1 REALSENSE_USB_RESET=0
LOG=/tmp/rs_test.log
rm -f "${LOG}"
timeout 30 ./scripts/launch_t1_realsense.sh >"${LOG}" 2>&1 || true
echo "=== disconnect errors: $(grep -c 'No such device' "${LOG}" || echo 0) ==="
echo "=== disconnected msg: $(grep -c 'disconnected' "${LOG}" || echo 0) ==="
grep 'RealSense Node Is Up' "${LOG}" || echo "NOT UP"
grep 'Open profile' "${LOG}" || true
tail -20 "${LOG}"
