#!/usr/bin/env bash
# Laptop → Gen.G: stop remote Pi camera + JPEG (SSH).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_GENJI="${SSH_GENJI:-${ROOT}/scripts/ssh_genji.py}"
if [[ ! -f "${SSH_GENJI}" ]]; then
  echo "[FAIL] ssh_genji.py 없음: ${SSH_GENJI}" >&2
  exit 1
fi
echo "==> Gen.G 카메라 원격 종료 (SSH)"
python3 - <<PY
import base64, sys
from pathlib import Path
sys.path.insert(0, str(Path("${SSH_GENJI}").resolve().parent))
import ssh_genji
remote = r"""
set +e
pkill -9 -f camera_ros 2>/dev/null || true
pkill -9 -f camera_node 2>/dev/null || true
pkill -9 -f raspberrypi_ipa 2>/dev/null || true
pkill -9 -f geng_jpeg_throttle 2>/dev/null || true
rm -f /tmp/geng_camera_node.pid /tmp/geng_jpeg_throttle.pid
sleep 1
echo "[OK] Gen.G camera stopped on robot"
"""
b64 = base64.b64encode(remote.encode()).decode("ascii")
raise SystemExit(int(ssh_genji.ssh_run(f"echo {b64} | base64 -d | bash", timeout=60) or 0))
PY
