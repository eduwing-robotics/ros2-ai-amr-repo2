#!/bin/bash
# rtabmap_setup_ubuntu.sh — 동료 우분투에 RTAB-Map(ROS2) 설치. URHYNIX 티원 D435 bag 재처리용.
#   Ubuntu 24.04→Jazzy / 22.04→Humble 자동 매핑. ROS2 없으면 apt repo 추가 후 desktop+rtabmap+mcap 설치.
#   bag(rosbag2 mcap)을 RGB-D로 재처리해 loop-closure 적용 컬러 3D를 만드는 게 목적.
# 사용: bash rtabmap_setup_ubuntu.sh   (sudo 비번 물어봄)
set -e
UB=$(lsb_release -rs 2>/dev/null || echo unknown)
case "$UB" in
  24.04) ROS=jazzy ;;
  22.04) ROS=humble ;;
  *) echo "지원 안 함: Ubuntu '$UB' (24.04→jazzy / 22.04→humble 필요). URHYNIX팀에 알려주세요."; exit 1 ;;
esac
echo "==> Ubuntu $UB → ROS2 $ROS 설치"

# ROS2 apt 저장소 (ros2 없고 repo 없을 때만 추가)
if ! command -v ros2 >/dev/null 2>&1 && [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
  echo "==> ROS2 apt 저장소 추가"
  sudo apt update
  sudo apt install -y software-properties-common curl
  sudo add-apt-repository -y universe
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null
fi

echo "==> 패키지 설치 (시간 좀 걸림)"
sudo apt update
sudo apt install -y \
  ros-$ROS-desktop \
  ros-$ROS-rtabmap-ros \
  ros-$ROS-rosbag2-storage-mcap \
  ros-$ROS-image-transport-plugins

echo ""
echo "==> 완료. 확인:"
echo "    source /opt/ros/$ROS/setup.bash && ros2 pkg list | grep -E 'rtabmap|storage_mcap'"
echo "    (rtabmap_ros + rosbag2_storage_mcap 보이면 성공)"
echo "ROS_DISTRO=$ROS"
