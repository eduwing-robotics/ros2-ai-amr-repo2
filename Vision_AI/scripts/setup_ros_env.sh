#!/usr/bin/env bash
# Museum Patrol — ROS 2 + ros_env 올바른 활성화 순서
#
# 문제 원인 요약:
#   1) ros-jazzy-ros2topic 미설치 → `ros2 topic` 서브커맨드 없음 (가장 흔한 원인)
#   2) venv를 ROS보다 먼저 activate → PYTHONPATH 충돌 가능
#
# 사용법 (새 터미널마다):
#   source ~/workspace/robot_project/scripts/setup_ros_env.sh
#
# 주의: source 한 스크립트에서는 exit / set -e 사용 금지 (터미널이 같이 닫힘)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

_sourced=0
[[ "${BASH_SOURCE[0]}" != "${0}" ]] && _sourced=1

_fail() {
  echo "$@" >&2
  if [[ "${_sourced}" -eq 1 ]]; then
    return 1
  fi
  exit 1
}

# 1) 시스템 ROS 2 Jazzy (반드시 먼저)
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  _fail "[ERROR] /opt/ros/jazzy/setup.bash not found. Install ROS 2 Jazzy first."
fi
# shellcheck source=/dev/null
source /opt/ros/jazzy/setup.bash

# 2) 워크스페이스 overlay
if [[ -f "${WS_DIR}/install/setup.bash" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/install/setup.bash"
else
  echo "[WARN] ${WS_DIR}/install/setup.bash not found. Run colcon build first." >&2
fi

# 3) YOLO용 venv (ROS 환경 이후에 activate)
if [[ -f "${WS_DIR}/ros_env/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${WS_DIR}/ros_env/bin/activate"
  # OpenCV Qt viewer: broken cv2/qt/fonts → blank imshow window
  if python3 -c "from museum_patrol_nodes.cv2_display_env import patch_after_cv2_import; import cv2; patch_after_cv2_import()" 2>/dev/null; then
    :
  fi
else
  export PATH="${HOME}/.local/bin:${PATH}"
  if python3 -c "import ultralytics" 2>/dev/null; then
    echo "[INFO] Using system/user ultralytics (no ros_env venv)." >&2
  else
    echo "[WARN] ros_env not found. Run scripts/setup_robot.sh on this machine." >&2
  fi
fi

# 4) ros2 topic 확장 패키지 설치 여부 점검
if command -v ros2 >/dev/null 2>&1 && ! ros2 topic list --help >/dev/null 2>&1; then
  echo "────────────────────────────────────────────────────────" >&2
  echo "[ACTION REQUIRED] ros2 topic CLI is NOT installed." >&2
  echo "  Run:  sudo apt install ros-jazzy-ros2topic" >&2
  echo "  Optional (more CLI tools): sudo apt install ros-jazzy-ros2interface ros-jazzy-ros2node ros-jazzy-ros2service" >&2
  echo "────────────────────────────────────────────────────────" >&2
fi

echo "[OK] ROS env ready — workspace: ${WS_DIR}"
echo "     ros2 topic list   (after installing ros-jazzy-ros2topic)"
echo "     ./scripts/view_yolo.sh   (view /detect/image_raw)"

# 5) 멀티머신 DDS — 반드시 jazzy/install source 이후 (덮어쓰기 방지)
if [[ "${SKIP_ROS_MULTIMACHINE:-0}" != "1" ]]; then
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/ros_multimachine_env.sh"
fi
