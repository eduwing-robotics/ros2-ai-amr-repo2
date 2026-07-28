#!/usr/bin/env bash
# debug_camera_frame.py 래퍼 — ROS 환경 자동 로드
set -eo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=/dev/null
source "${SCRIPT_DIR}/ros_multimachine_env.sh"
source /opt/ros/jazzy/setup.bash
# shellcheck source=/dev/null
source "${WS_DIR}/install/setup.bash"
# shellcheck source=/dev/null
source "${WS_DIR}/ros_env/bin/activate" 2>/dev/null || true

echo "[INFO] Topics now:"
timeout 5 ros2 topic list 2>/dev/null | grep -E 'camera|detect' || echo "  (no camera/detect topics yet)"

exec python3 "${SCRIPT_DIR}/debug_camera_frame.py" "$@"
