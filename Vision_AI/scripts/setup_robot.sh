#!/usr/bin/env bash
# T1 로봇 최초 1회 환경 설정 (RealSense + YOLO)
set -eo pipefail

WS_DIR="${1:-/home/t1/workspace/robot_project}"
cd "${WS_DIR}"

source /opt/ros/jazzy/setup.bash

if ! python3 -c "import ultralytics" 2>/dev/null; then
  echo "[ACTION REQUIRED] ultralytics not installed on this machine."
  echo "  sudo apt install -y python3-pip python3.12-venv"
  echo "  python3 -m venv ros_env --system-site-packages"
  echo "  source ros_env/bin/activate && pip install ultralytics 'numpy<2' opencv-python"
  exit 1
fi

if [[ -f ros_env/bin/activate ]]; then
  # shellcheck source=/dev/null
  source ros_env/bin/activate
fi

colcon build --packages-select museum_patrol_system
# shellcheck source=/dev/null
source install/setup.bash

echo "[OK] Robot setup complete: ${WS_DIR}"
echo "Run: ./scripts/launch_t1_realsense.sh"
