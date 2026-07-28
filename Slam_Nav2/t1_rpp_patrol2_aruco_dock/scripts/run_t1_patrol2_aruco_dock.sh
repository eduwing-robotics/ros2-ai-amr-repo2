#!/usr/bin/env bash
# T1: patrol x2 -> ArUco stage -> JPEG ArUco align -> 180° -> rear-wall dock.
# Known-good path uses ROS JPEG (not H.264 UDP). H.264 aligner does not sweep-search
# when the marker is off-center / out of view.
set -Eeo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

export ROBOT=t1
# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"

# Defaults from aruco_markers/markers.yaml (T1 = ID 11).
eval "$(
  PYTHONPATH="${ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}" python3 - <<'PY'
from aruco_marker_config import marker_for_robot
c = marker_for_robot("t1")
print(f'MARKER_ID={c["marker_id"]}')
print(f'MARKER_SIZE={c["marker_size_m"]}')
print(f'TARGET_BEARING_DEG={c.get("target_bearing_deg", 3.9)}')
print(f'IMAGE_TOPIC={c["image_topic"]!r}')
print(f'CAMERA_INFO_TOPIC={c["camera_info_topic"]!r}')
PY
)"

IMAGE_TOPIC="${IMAGE_TOPIC:-/tb3_1/camera/color/image_raw/compressed}"
CAMERA_INFO_TOPIC="${CAMERA_INFO_TOPIC:-/tb3_1/camera/color/camera_info}"
MARKER_ID="${MARKER_ID:-11}"
MARKER_SIZE="${MARKER_SIZE:-0.05}"
TARGET_BEARING_DEG="${TARGET_BEARING_DEG:-3.9}"

stop_robot() {
  timeout 2 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
  timeout 2 ros2 topic pub -r 20 /cmd_vel_nav geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
}

failed() {
  status=$?
  echo "[FAIL] 연속 순찰/도킹 중단 (exit=${status})" >&2
  stop_robot
  exit "${status}"
}
trap failed ERR INT TERM

echo "===== 1/6 순찰 1회차 ====="
python3 scripts/run_patrol.py
echo "===== 2/6 순찰 2회차 ====="
python3 scripts/run_patrol.py
echo "===== 3/6 ArUco 대기장소 이동 ====="
python3 scripts/park_t1.py --aruco-stage

echo "===== 4/6 ArUco 몸체 각도 정렬 (JPEG ROS, ID ${MARKER_ID}) ====="
echo "    image=${IMAGE_TOPIC}"
echo "    target_bearing=${TARGET_BEARING_DEG}deg"
echo "    (ArUco/H.264 뷰어가 열려 있으면 먼저 닫으세요)"
# Preflight: one compressed frame must arrive
if ! timeout 6 ros2 topic echo "${IMAGE_TOPIC}" --once >/tmp/t1_aruco_cam_once.txt 2>&1; then
  echo "[FAIL] 카메라 토픽 없음: ${IMAGE_TOPIC}" >&2
  echo "       T1에서 RealSense JPEG 스트림을 켠 뒤 다시 실행하세요." >&2
  tail -8 /tmp/t1_aruco_cam_once.txt >&2 || true
  exit 2
fi
python3 scripts/aruco_align_t1.py \
  --marker-id "${MARKER_ID}" \
  --marker-size "${MARKER_SIZE}" \
  --target-bearing-deg "${TARGET_BEARING_DEG}" \
  --cmd-topic /cmd_vel_nav \
  --image-topic "${IMAGE_TOPIC}" \
  --camera-info-topic "${CAMERA_INFO_TOPIC}"

echo "===== 5/6 정밀 180도 회전 ====="
python3 scripts/rotate_t1_precise.py --ros-args -r /cmd_vel:=/cmd_vel_nav

echo "===== 6/6 후방 라이다 저속 도킹 ====="
python3 scripts/dock_t1_rear_wall_long.py --ros-args -r /cmd_vel:=/cmd_vel_nav

stop_robot
trap - ERR INT TERM
echo "[OK] 순찰 2회 및 T1 도킹 완료"
