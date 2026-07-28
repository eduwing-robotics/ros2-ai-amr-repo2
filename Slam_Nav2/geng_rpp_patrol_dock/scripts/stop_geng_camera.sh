#!/usr/bin/env bash
# Laptop → Gen.G: stop remote Pi camera (SSH, no file copy).
#
# Usage:
#   cd ~/workspace/museum_nav_ws
#   ./scripts/stop_geng_camera.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT_PROJECT="${ROBOT_PROJECT:-/home/hc/workspace/robot_project}"
SSH_GENJI="${SSH_GENJI:-${ROBOT_PROJECT}/scripts/ssh_genji.py}"

if [[ ! -f "${SSH_GENJI}" ]]; then
  echo "[FAIL] ssh_genji.py 없음: ${SSH_GENJI}" >&2
  exit 1
fi

echo "==> Gen.G 카메라 원격 종료 (SSH)"

# Same base64 path as start_geng_camera.sh — avoid quote breakage.
python3 - <<PY
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path("${SSH_GENJI}").resolve().parent))
import ssh_genji  # type: ignore

remote = r"""
set +e
pkill -9 -f camera_ros 2>/dev/null || true
pkill -9 -f camera_node 2>/dev/null || true
pkill -9 -f raspberrypi_ipa 2>/dev/null || true
pkill -9 -f geng_jpeg_throttle 2>/dev/null || true
rm -f /tmp/geng_camera_node.pid
sleep 1
if pgrep -af 'camera_ros|camera_node' >/tmp/geng_cam_left.txt 2>/dev/null; then
  echo "[WARN] still running:"
  cat /tmp/geng_cam_left.txt
  exit 1
fi
echo "[OK] Gen.G camera stopped on robot"
"""
b64 = base64.b64encode(remote.encode()).decode("ascii")
code = ssh_genji.ssh_run(f"echo {b64} | base64 -d | bash", timeout=60)
raise SystemExit(int(code or 0))
PY

echo ""
echo "==> 노트북 토픽 확인 (없어야 정상)"
export ROBOT=geng
# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"
if timeout 3 ros2 topic echo /tb3_2/camera/image_raw --once >/dev/null 2>&1; then
  echo "[WARN] /tb3_2/camera/image_raw 아직 보임 — 잠시 후 다시 확인"
  exit 2
fi
echo "[OK] 카메라 토픽 없음"
