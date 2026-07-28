#!/usr/bin/env bash
# RealSense USB 진단 (로봇에서 실행)
set -eo pipefail

echo "=== Host ==="
hostname
uname -a

echo ""
echo "=== USB RealSense ==="
lsusb -d 8086:0b07 || echo "NOT FOUND"

echo ""
echo "=== sysfs port / power ==="
for dev in /sys/bus/usb/devices/*; do
  [[ -f "${dev}/idVendor" ]] || continue
  vid="$(cat "${dev}/idVendor" 2>/dev/null || true)"
  pid="$(cat "${dev}/idProduct" 2>/dev/null || true)"
  if [[ "${vid}" == "8086" && "${pid}" == "0b07" ]]; then
  port="$(basename "${dev}")"
  power="$(cat "${dev}/power/control" 2>/dev/null || echo n/a)"
  autosuspend="$(cat "${dev}/power/autosuspend" 2>/dev/null || echo n/a)"
  echo "port=${port} power=${power} autosuspend=${autosuspend}"
  fi
done

echo ""
echo "=== video4linux ==="
ls -la /dev/video* 2>/dev/null || echo "no /dev/video*"

echo ""
echo "=== recent kernel USB errors (dmesg) ==="
sudo dmesg 2>/dev/null | tail -80 | grep -iE 'usb|realsense|disconnect|over-current|reset|error|8086' || echo "(no matches or no sudo)"

echo ""
echo "=== camera processes ==="
pgrep -af 'realsense|jpeg_compressor' || echo "none"

echo ""
echo "=== Pi USB config ==="
for f in /boot/firmware/config.txt /boot/config.txt; do
  [[ -f "${f}" ]] && grep -E 'max_usb_current|usb_max' "${f}" 2>/dev/null && break
done || echo "max_usb_current not found in config.txt"
