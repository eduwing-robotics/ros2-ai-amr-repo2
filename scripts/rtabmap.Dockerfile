# rtabmap.Dockerfile — URHYNIX 티원 D435 bag 재처리용 RTAB-Map 이미지(arm64).
# introlab3it/rtabmap_ros:jazzy 에 compressed_image_transport만 추가
#   (우리 컬러가 /image_raw/compressed로만 녹화돼서 rgb_image_transport:=compressed에 필요).
# 빌드: docker build --platform linux/arm64 -f scripts/rtabmap.Dockerfile -t urhynix/rtabmap:jazzy .
FROM introlab3it/rtabmap_ros:jazzy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ros-jazzy-image-transport-plugins \
      ros-jazzy-rmw-cyclonedds-cpp && \
    rm -rf /var/lib/apt/lists/*
