#!/usr/bin/env bash
# T1 로봇 — RealSense USB 리셋 (VIDIOC_QBUF / No such device 복구용)
# 로봇에서: sudo ./scripts/reset_realsense_usb.sh
set -eo pipefail

if ! lsusb -d 8086:0b07 >/dev/null 2>&1; then
  echo "[WARN] RealSense D435 (8086:0b07) not found on USB"
  exit 1
fi

PORT=""
for dev in /sys/bus/usb/devices/*; do
  [[ -f "${dev}/idVendor" ]] || continue
  if [[ "$(cat "${dev}/idVendor")" == "8086" && "$(cat "${dev}/idProduct")" == "0b07" ]]; then
    PORT="$(basename "${dev}")"
    break
  fi
done

echo "[INFO] RealSense USB port: ${PORT:-unknown}"

pkill -f realsense2_camera_node 2>/dev/null || true
pkill -f jpeg_compressor 2>/dev/null || true
sleep 1

if [[ -n "${PORT}" ]]; then
  echo "[INFO] USB unbind/bind ${PORT}..."
  echo "${PORT}" | sudo tee /sys/bus/usb/drivers/usb/unbind >/dev/null || true
  sleep 3
  echo "${PORT}" | sudo tee /sys/bus/usb/drivers/usb/bind >/dev/null || true
  sleep 2
fi

if lsusb -d 8086:0b07 >/dev/null 2>&1; then
  echo "[OK] RealSense visible after reset"
else
  echo "[FAIL] RealSense still not visible — USB 케이블·전원(허브) 확인" >&2
  exit 1
fi
