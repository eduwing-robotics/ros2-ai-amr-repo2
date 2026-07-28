#!/usr/bin/env bash
# Gen.G camera+JPEG remote start (self-contained in robot_project).
# Defaults: 1280x720 YUYV, JPEG max_fps=15 quality=45, DOMAIN=1.
# Overrides: CAMERA_WIDTH CAMERA_HEIGHT JPEG_MAX_FPS JPEG_QUALITY
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${ROOT}/scripts/start_geng_camera.py" "$@"
