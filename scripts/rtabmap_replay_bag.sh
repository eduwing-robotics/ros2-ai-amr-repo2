#!/bin/bash
# rtabmap_replay_bag.sh — 우분투(네이티브 ROS2)에서 티원 D435 bag을 RTAB-Map으로 재처리.
#   3D 맵이 rtabmap_viz 창에 실시간으로 쌓이고, bag이 끝나면 컬러 점군 PLY를 자동 저장한다.
#   launch 인자는 URHYNIX팀이 Docker에서 ground-truth로 검증한 값(데이터·stamp 정렬 확인). 네이티브 우분투면 동작.
#   ※ Docker-on-Mac은 message_filters 이미지 sync가 막혀 불가 — 네이티브 우분투에서만 쓸 것.
# 사용: bash rtabmap_replay_bag.sh <bag_디렉토리> [ros_distro] [cam_ns] [duration_sec]
#   cam_ns: 카메라 토픽 prefix (기본값: /tb3_1/camera/camera  ← 신규 bag)
#           구 검증 bag은 /tb3_1/camera 로 지정
#   duration_sec: 재생을 N초 만에 강제 종료(로봇이 실제로 움직인 구간만 처리하고 싶을 때). 생략 시 끝까지 재생.
#   예) bash rtabmap_replay_bag.sh ~/bags/mapping_20260630_1658  jazzy  /tb3_1/camera/camera  230
set +u
BAG="$1"; ROS="${2:-${ROS_DISTRO:-jazzy}}"; CAM="${3:-/tb3_1/camera/camera}"; DURATION="$4"
if [ -z "$BAG" ] || [ ! -d "$BAG" ]; then
  echo "usage: bash rtabmap_replay_bag.sh <bag_디렉토리> [ros_distro] [cam_ns]"; echo "  bag 폴더 안에 *.mcap + metadata.yaml 이 있어야 함"; exit 1
fi
source /opt/ros/$ROS/setup.bash
OUT="$(cd "$(dirname "$BAG")" && pwd)/rtabmap_out"
mkdir -p "$OUT"; rm -f "$OUT/rtabmap.db"
echo "==> RTAB-Map 시작"

# 0) compressed→raw 변환 노드 (bag에 color/raw가 없고 compressed만 있는 경우 대응)
#    -p in_transport/out_transport 명시 필요 (CLI 위치인자는 파싱 순서 버그 있음)
ros2 run image_transport republish \
  --ros-args \
  -p in_transport:=compressed -p out_transport:=raw \
  -r in/compressed:="$CAM/color/image_raw/compressed" \
  -r out:="$CAM/color/image_raw" \
  >> "$OUT/rtabmap.log" 2>&1 &
REPUB_PID=$!
sleep 3

# 1) rtabmap (RGB-D, 외부 wheel odom, loop closure)
ros2 launch rtabmap_launch rtabmap.launch.py \
  rgb_topic:="$CAM/color/image_raw" \
  depth_topic:="$CAM/aligned_depth_to_color/image_raw" \
  camera_info_topic:="$CAM/aligned_depth_to_color/camera_info" \
  odom_topic:=/tb3_1/odom \
  frame_id:=tb3_1/base_footprint odom_frame_id:=tb3_1/odom \
  rgb_image_transport:=raw approx_sync:=true approx_sync_max_interval:=2.0 visual_odometry:=false \
  topic_queue_size:=100 sync_queue_size:=100 \
  use_sim_time:=false rtabmap_viz:=false \
  database_path:="$OUT/rtabmap.db" >> "$OUT/rtabmap.log" 2>&1 &
RTPID=$!

# 1b) base_link -> camera_link static tf (원본 녹화에 이 연결이 빠져있어 rtabmap이 TF를 못 찾음)
ros2 run tf2_ros static_transform_publisher --x 0.04 --z 0.10 \
  --frame-id tb3_1/base_link --child-frame-id camera_link \
  >> "$OUT/rtabmap.log" 2>&1 &
STPID=$!
sleep 8

# 2) bag 재생 (실시간). 끝나면 다음 단계로.
echo "==> bag 재생: $BAG  (창에서 맵이 자라는 걸 보세요)"
# /tf_static이 replay 중 volatile durability로 나가 늦게 붙는 구독자(rtabmap)가 놓치는 문제 우회
QOS_OVERRIDE="$(dirname "$BAG")/qos_override.yaml"
PLAY_CMD="ros2 bag play \"$BAG\""
if [ -f "$QOS_OVERRIDE" ]; then
  PLAY_CMD="$PLAY_CMD --qos-profile-overrides-path \"$QOS_OVERRIDE\""
fi
if [ -n "$DURATION" ]; then
  eval "timeout ${DURATION}s $PLAY_CMD"
else
  eval "$PLAY_CMD"
fi

# 3) 재생 끝 → rtabmap 정상 종료(DB 저장) → 컬러 점군 PLY export
echo "==> 재생 끝. 맵 저장 중..."
kill -INT "$RTPID" 2>/dev/null; kill "$REPUB_PID" 2>/dev/null; kill "$STPID" 2>/dev/null; sleep 8
rtabmap-export --cloud "$OUT/rtabmap.db" 2>&1 | tail -4
echo ""
echo "==> 완료. 결과:"
echo "    DB : $OUT/rtabmap.db"
ls "$OUT"/*.ply 2>/dev/null && echo "    PLY: 위 파일 (CloudCompare/MeshLab로 열기)" || echo "    PLY 없으면 rtabmap_viz 창 File>Export 3D clouds 로 저장"
echo "    문제 시 로그: tail -40 $OUT/rtabmap.log"
