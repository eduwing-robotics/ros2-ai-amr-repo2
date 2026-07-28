#!/usr/bin/env bash
# T1 Pi 4 — RealSense USB 전원/절전 안정화 (1회 실행, sudo 필요)
# 로봇: sudo ./scripts/setup_pi_usb_realsense.sh
set -eo pipefail

if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "[WARN] aarch64(Pi)가 아닙니다 — 건너뛰어도 됩니다."
fi

UDEV_FILE="/etc/udev/rules.d/99-realsense-usb.rules"
echo "[INFO] udev: USB autosuspend off for Intel RealSense"
sudo tee "${UDEV_FILE}" >/dev/null <<'EOF'
# Intel RealSense — Pi 4 USB 끊김 방지 (VIDIOC_QBUF / No such device)
SUBSYSTEM=="usb", ATTR{idVendor}=="8086", ATTR{idProduct}=="0b07", ATTR{power/control}="on", ATTR{power/autosuspend}="-1"
EOF
sudo udevadm control --reload-rules
sudo udevadm trigger

if [[ -w /sys/module/usbcore/parameters/autosuspend ]]; then
  echo "[INFO] usbcore autosuspend=0 (현재 세션)"
  echo 0 | sudo tee /sys/module/usbcore/parameters/autosuspend >/dev/null || true
fi

CMDLINE="/boot/firmware/cmdline.txt"
if [[ ! -f "${CMDLINE}" ]]; then
  CMDLINE="/boot/cmdline.txt"
fi
if [[ -f "${CMDLINE}" ]] && ! grep -q 'usbcore.autosuspend=-1' "${CMDLINE}"; then
  echo "[INFO] cmdline에 usbcore.autosuspend=-1 추가 (재부팅 후 적용)"
  sudo sed -i 's/$/ usbcore.autosuspend=-1/' "${CMDLINE}"
fi

CONFIG="/boot/firmware/config.txt"
if [[ ! -f "${CONFIG}" ]]; then
  CONFIG="/boot/config.txt"
fi
if [[ -f "${CONFIG}" ]]; then
  if ! grep -q '^max_usb_current=1' "${CONFIG}"; then
    echo "[INFO] config.txt에 max_usb_current=1 추가 (재부팅 후 적용)"
    echo 'max_usb_current=1' | sudo tee -a "${CONFIG}" >/dev/null
  else
    echo "[OK] max_usb_current=1 already set"
  fi
fi

echo ""
echo "[OK] Pi USB tuning applied."
echo "     재부팅 권장: sudo reboot"
echo "     전원 있는 USB3 허브 사용 시 안정성이 크게 좋아집니다."
