#!/usr/bin/env bash
# 노트북 1회 설치 (sudo 필요)
set -euo pipefail
sudo apt-get update
sudo apt-get install -y ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-ros2topic
echo "[OK] Laptop ROS vision deps installed."
