#!/usr/bin/env python3
"""Laptop → Gen.G: start Pi camera + JPEG throttle over SSH (no permanent file copy).

Usage:
  cd ~/workspace/robot_project
  ./scripts/start_geng_camera.sh
  ./scripts/stop_geng_camera.sh   # camera + jpeg only
  ROBOT=geng ./scripts/stop_all.sh  # Nav2+camera+bringup

Topics (camera_ros __ns:=/tb3_2 → node /tb3_2/camera):
  /tb3_2/camera/image_raw
  /tb3_2/camera/image_raw/compressed   (geng_jpeg_throttle, BEST_EFFORT)
  /tb3_2/camera/camera_info

Env overrides (smooth live view over Wi-Fi):
  CAMERA_WIDTH / CAMERA_HEIGHT   default 1280x720 YUYV (FOV-friendly; not 640x480 crop)
  CAMERA_FORMAT                  default YUYV
  JPEG_MAX_FPS                   default 15
  JPEG_QUALITY                   default 45 (40–50 is the live-view sweet spot)
  Full sensor FOV (heavier):     CAMERA_WIDTH=1640 CAMERA_HEIGHT=1232 JPEG_QUALITY=40

NOTE: Do not inherit laptop ROS_DOMAIN_ID (often 2 for T1). Gen.G is domain 1.
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # robot_project
ROBOT_PROJECT = Path(os.environ.get("ROBOT_PROJECT", str(ROOT)))
SSH_GENJI = Path(os.environ.get("SSH_GENJI", str(ROBOT_PROJECT / "scripts" / "ssh_genji.py")))
JPEG_SRC = Path(__file__).resolve().parent / "geng_jpeg_throttle.py"

# IMX219: 640x480 often selects a *cropped* sensor mode → looks digitally zoomed.
# Default 1280x720: wider FOV than 640 crop, much lighter than 1640x1232 over Wi-Fi JPEG.
# Full FOV if needed: CAMERA_WIDTH=1640 CAMERA_HEIGHT=1232 JPEG_QUALITY=40
WIDTH = os.environ.get("CAMERA_WIDTH", "1280")
HEIGHT = os.environ.get("CAMERA_HEIGHT", "720")
FORMAT = os.environ.get("CAMERA_FORMAT", "YUYV")
# Gen.G domain — never inherit laptop ROS_DOMAIN_ID=2 from T1 sessions.
DOMAIN = os.environ.get("GENJI_ROS_DOMAIN_ID", "1")
# Throttled BEST_EFFORT JPEG for laptop YOLO / live view.
JPEG_MAX_FPS = os.environ.get("JPEG_MAX_FPS", "15")
JPEG_QUALITY = os.environ.get("JPEG_QUALITY", "45")


def remote_body(jpeg_b64: str) -> str:
    # Runs on Gen.G. Keep __ns:=/tb3_2 so topics match markers.yaml / YOLO.
    # Remap camera_ros builtin compressed (RELIABLE@30Hz) out of the way so
    # geng_jpeg_throttle owns /image_raw/compressed (BEST_EFFORT, throttled).
    return f"""
set -eo pipefail
export ROS_DOMAIN_ID={DOMAIN}
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset ROS_LOCALHOST_ONLY
unset CYCLONEDDS_URI
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export LIBCAMERA_LOG_LEVELS='*:WARN'
export LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${{LD_LIBRARY_PATH:-}}"
export LIBCAMERA_IPA_PROXY_PATH="/usr/local/libexec/libcamera"
export LIBCAMERA_IPA_MODULE_PATH="/usr/local/lib/aarch64-linux-gnu/libcamera/ipa"
source /opt/ros/jazzy/setup.bash
export LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${{LD_LIBRARY_PATH}}"

pkill -9 -f camera_ros 2>/dev/null || true
pkill -9 -f camera_node 2>/dev/null || true
pkill -9 -f raspberrypi_ipa 2>/dev/null || true
pkill -9 -f geng_jpeg_throttle 2>/dev/null || true
sleep 2

: > /tmp/geng_camera_node.log
nohup env \\
  LD_LIBRARY_PATH="/usr/local/lib/aarch64-linux-gnu:${{LD_LIBRARY_PATH}}" \\
  LIBCAMERA_IPA_PROXY_PATH="/usr/local/libexec/libcamera" \\
  LIBCAMERA_IPA_MODULE_PATH="/usr/local/lib/aarch64-linux-gnu/libcamera/ipa" \\
  LIBCAMERA_LOG_LEVELS='*:WARN' \\
  ROS_DOMAIN_ID={DOMAIN} \\
  RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \\
  ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET \\
  ros2 run camera_ros camera_node --ros-args \\
    -r __ns:=/tb3_2 \\
    -r /tb3_2/camera/image_raw/compressed:=/tb3_2/camera/image_raw/compressed_builtin \\
    -p width:={WIDTH} \\
    -p height:={HEIGHT} \\
    -p format:={FORMAT} \\
  >/tmp/geng_camera_node.log 2>&1 &
echo $! > /tmp/geng_camera_node.pid
sleep 6
echo "[OK] camera pid=$(cat /tmp/geng_camera_node.pid) DOMAIN={DOMAIN}"
tail -n 20 /tmp/geng_camera_node.log || true
pgrep -af camera_node || echo "[WARN] camera_node process not found"
timeout 5 ros2 topic hz /tb3_2/camera/image_raw --window 5 || true

# Install + start JPEG throttle from laptop bytes (no permanent robot copy).
echo {jpeg_b64} | base64 -d > /tmp/geng_jpeg_throttle.py
: > /tmp/geng_jpeg_throttle.log
nohup env \\
  ROS_DOMAIN_ID={DOMAIN} \\
  RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \\
  ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET \\
  python3 /tmp/geng_jpeg_throttle.py \\
    --max-fps {JPEG_MAX_FPS} \\
    --jpeg-quality {JPEG_QUALITY} \\
  >/tmp/geng_jpeg_throttle.log 2>&1 &
echo $! > /tmp/geng_jpeg_throttle.pid
sleep 3
echo "[OK] jpeg pid=$(cat /tmp/geng_jpeg_throttle.pid)"
tail -n 10 /tmp/geng_jpeg_throttle.log || true
pgrep -af geng_jpeg_throttle || echo "[WARN] geng_jpeg_throttle not found"
timeout 5 ros2 topic hz /tb3_2/camera/image_raw/compressed --window 5 || true
""".strip()


def ssh_run_script(remote_script: str) -> int:
    if not SSH_GENJI.is_file():
        print(f"[FAIL] ssh_genji.py 없음: {SSH_GENJI}", file=sys.stderr)
        return 1
    sys.path.insert(0, str(SSH_GENJI.parent))
    import ssh_genji  # type: ignore

    # Avoid nested-quote breakage in ssh_genji's command!r path:
    # send the script as base64 and decode on the robot.
    b64 = base64.b64encode(remote_script.encode("utf-8")).decode("ascii")
    cmd = f"echo {b64} | base64 -d | bash"
    return int(ssh_genji.ssh_run(cmd, timeout=180) or 0)


def laptop_check() -> int:
    env = os.environ.copy()
    env["ROS_DOMAIN_ID"] = DOMAIN
    env["RMW_IMPLEMENTATION"] = "rmw_cyclonedds_cpp"
    env["ROS_AUTOMATIC_DISCOVERY_RANGE"] = "SUBNET"
    env.pop("CYCLONEDDS_URI", None)
    env.pop("ROS_LOCALHOST_ONLY", None)
    check = r"""
set -euo pipefail
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID="%s"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
unset CYCLONEDDS_URI ROS_LOCALHOST_ONLY
if timeout 8 ros2 topic echo /tb3_2/camera/image_raw/compressed --once >/tmp/geng_cam_once.txt 2>&1; then
  echo "[OK] /tb3_2/camera/image_raw/compressed 수신"
  exit 0
fi
if timeout 5 ros2 topic echo /tb3_2/camera/image_raw --once >/tmp/geng_cam_raw_once.txt 2>&1; then
  echo "[OK] /tb3_2/camera/image_raw 수신 (compressed 없음)"
  exit 0
fi
echo "[FAIL] 카메라 토픽 없음" >&2
tail -15 /tmp/geng_cam_once.txt 2>/dev/null || true
exit 2
""" % DOMAIN
    return subprocess.call(["bash", "-lc", check], env=env)


def main() -> int:
    if not JPEG_SRC.is_file():
        print(f"[FAIL] JPEG throttle 없음: {JPEG_SRC}", file=sys.stderr)
        return 1
    jpeg_b64 = base64.b64encode(JPEG_SRC.read_bytes()).decode("ascii")
    print("==> Gen.G 카메라+JPEG 원격 기동 (SSH)")
    print(f"    ns=/tb3_2  {WIDTH}x{HEIGHT} {FORMAT}  DOMAIN={DOMAIN}")
    print(f"    jpeg max_fps={JPEG_MAX_FPS} quality={JPEG_QUALITY}")
    code = ssh_run_script(remote_body(jpeg_b64))
    if code != 0:
        print(f"[FAIL] SSH 원격 기동 실패 (exit={code})", file=sys.stderr)
        return code
    print("")
    print("==> 노트북에서 토픽 확인")
    time.sleep(1)
    return laptop_check()


if __name__ == "__main__":
    raise SystemExit(main())
