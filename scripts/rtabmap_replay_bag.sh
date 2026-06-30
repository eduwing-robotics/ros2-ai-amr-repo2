#!/bin/bash
# rtabmap_replay_bag.sh — 우분투(네이티브 ROS2)에서 티원 D435 bag을 RTAB-Map으로 재처리.
#   3D 맵이 rtabmap_viz 창에 실시간으로 쌓이고, bag이 끝나면 컬러 점군 PLY를 자동 저장한다.
#   launch 인자는 URHYNIX팀이 Docker에서 ground-truth로 검증한 값(데이터·stamp 정렬 확인). 네이티브 우분투면 동작.
#   ※ Docker-on-Mac은 message_filters 이미지 sync가 막혀 불가 — 네이티브 우분투에서만 쓸 것.
# 사용: bash rtabmap_replay_bag.sh <bag_디렉토리> [ros_distro]
#   예) bash rtabmap_replay_bag.sh ~/urhynix_bags/d435_rot_1782453993
set +u
BAG="$1"; ROS="${2:-${ROS_DISTRO:-jazzy}}"
if [ -z "$BAG" ] || [ ! -d "$BAG" ]; then
  echo "usage: bash rtabmap_replay_bag.sh <bag_디렉토리> [ros_distro]"; echo "  bag 폴더 안에 *.mcap + metadata.yaml 이 있어야 함"; exit 1
fi
source /opt/ros/$ROS/setup.bash
OUT="$(cd "$(dirname "$BAG")" && pwd)/rtabmap_out"
mkdir -p "$OUT"; rm -f "$OUT/rtabmap.db"
echo "==> RTAB-Map 시작 (3D 창이 뜨고, 맵이 실시간으로 쌓입니다)"

# 1) rtabmap (RGB-D, 외부 wheel odom, loop closure). rtabmap_viz=실시간 3D 뷰.
ros2 launch rtabmap_launch rtabmap.launch.py \
  rgb_topic:=/tb3_1/camera/color/image_raw \
  depth_topic:=/tb3_1/camera/aligned_depth_to_color/image_raw \
  camera_info_topic:=/tb3_1/camera/aligned_depth_to_color/camera_info \
  odom_topic:=/tb3_1/odom \
  frame_id:=tb3_1/base_footprint odom_frame_id:=tb3_1/odom \
  rgb_image_transport:=compressed approx_sync:=true visual_odometry:=false \
  topic_queue_size:=50 sync_queue_size:=50 \
  use_sim_time:=false rtabmap_viz:=true \
  database_path:="$OUT/rtabmap.db" > "$OUT/rtabmap.log" 2>&1 &
RTPID=$!
sleep 8

# 2) bag 재생 (실시간). 끝나면 다음 단계로.
echo "==> bag 재생: $BAG  (창에서 맵이 자라는 걸 보세요)"
ros2 bag play "$BAG"

# 3) 재생 끝 → rtabmap 정상 종료(DB 저장) → 컬러 점군 PLY export
echo "==> 재생 끝. 맵 저장 중..."
kill -INT "$RTPID" 2>/dev/null; sleep 8
rtabmap-export --cloud "$OUT/rtabmap.db" 2>&1 | tail -4
echo ""
echo "==> 완료. 결과:"
echo "    DB : $OUT/rtabmap.db"
ls "$OUT"/*.ply 2>/dev/null && echo "    PLY: 위 파일 (CloudCompare/MeshLab로 열기)" || echo "    PLY 없으면 rtabmap_viz 창 File>Export 3D clouds 로 저장"
echo "    문제 시 로그: tail -40 $OUT/rtabmap.log"
