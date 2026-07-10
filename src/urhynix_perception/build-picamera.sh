#!/bin/bash
# Pi Camera Module v2 (Sony IMX219) user-space build for Ubuntu 24.04 LTS
# Reason: Ubuntu 24.04 ports repo doesn't ship rpicam-apps / Pi-fork libcamera.
# Builds: github.com/raspberrypi/libcamera + github.com/raspberrypi/rpicam-apps
# Target time: 30~60 min on Pi 4 (4GB).
#
# Usage (안전한 패턴):
#   ssh urhynix-robot
#   sudo -v                    # 비번 1회
#   nohup bash ~/build-picamera.sh > ~/picam-build.log 2>&1 < /dev/null &
#   disown
#   exit                       # ssh 끊어도 빌드 살아있음
#
# Progress: ssh urhynix-robot 'tail -f ~/picam-build.log'
# Done check: ssh urhynix-robot 'grep "BUILD COMPLETE" ~/picam-build.log'
set -euo pipefail
LOG=~/picam-build.log
exec > >(tee -a "$LOG") 2>&1

echo "=== [$(date +%T)] BUILD START ==="

# ----------------------------------------------------------------------
# sudo keeper — sudo 캐시를 빌드 끝까지 유지 (5분 timeout 우회)
# ----------------------------------------------------------------------
sudo -n -v 2>/dev/null || { echo "[FATAL] sudo -v 먼저 실행 필요"; exit 1; }
( while true; do sleep 50; sudo -n -v 2>/dev/null || exit; done ) &
SUDO_KEEPER=$!
trap 'kill $SUDO_KEEPER 2>/dev/null || true' EXIT INT TERM

# ----------------------------------------------------------------------
echo "=== [$(date +%T)] 1/4 deps install ==="
# ----------------------------------------------------------------------
sudo apt update
sudo apt install -y \
  git python3-pip python3-jinja2 python3-yaml python3-ply \
  meson cmake ninja-build pkg-config \
  libboost-dev libgnutls28-dev openssl libtiff-dev pybind11-dev \
  libdrm-dev libexif-dev libjpeg-dev libpng-dev libgles2-mesa-dev \
  qtbase5-dev libqt5core5a libqt5gui5 libqt5widgets5 \
  libavcodec-dev libavdevice-dev libavformat-dev libswresample-dev \
  libudev-dev libyaml-dev libevent-dev libepoxy-dev \
  v4l-utils

# ----------------------------------------------------------------------
echo "=== [$(date +%T)] 2/4 libcamera Pi fork build ==="
# ----------------------------------------------------------------------
cd ~
[ -d libcamera ] || git clone --depth=1 https://github.com/raspberrypi/libcamera.git
cd libcamera
if [ ! -d build ]; then
  meson setup build --buildtype=release \
    -Dpipelines=rpi/vc4 \
    -Dipas=rpi/vc4 \
    -Dv4l2=true -Dgstreamer=disabled -Dtest=false -Dlc-compliance=disabled \
    -Dcam=disabled -Dqcam=disabled -Ddocumentation=disabled
fi
ninja -C build -j2
sudo ninja -C build install
sudo ldconfig

# ----------------------------------------------------------------------
echo "=== [$(date +%T)] 3/4 rpicam-apps build ==="
# ----------------------------------------------------------------------
cd ~
[ -d rpicam-apps ] || git clone --depth=1 https://github.com/raspberrypi/rpicam-apps.git
cd rpicam-apps
if [ ! -d build ]; then
  # Note: enable_libav=disabled — Ubuntu 24.04 ports의 libavcodec 60.31.x가
  # rpicam-apps master의 libav encoder에 비해 API too old (#error).
  # 박물관 시연에서 mp4 인코딩은 별도 ffmpeg(record_bag_mp4.sh)에서 처리하므로
  # rpicam-apps 자체 libav encoder는 불필요.
  meson setup build --buildtype=release \
    -Denable_libav=disabled \
    -Denable_drm=enabled \
    -Denable_egl=enabled \
    -Denable_qt=enabled \
    -Denable_opencv=disabled \
    -Denable_tflite=disabled
fi
ninja -C build -j2
sudo ninja -C build install
sudo ldconfig

# ----------------------------------------------------------------------
echo "=== [$(date +%T)] 4/4 verify ==="
# ----------------------------------------------------------------------
rpicam-hello --version
rpicam-hello --list-cameras

echo ""
echo "=== BUILD COMPLETE [$(date +%T)] ==="
echo "Next: rpicam-still -n -t 2000 -o ~/cam_test.jpg"
