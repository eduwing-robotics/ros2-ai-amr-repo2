#!/usr/bin/env bash
# Gen.G: ArUco stage -> JPEG bearing align (검증된) -> odom 180° -> rear dock.
# Requires: ROBOT=geng ./scripts/go_nav2_geng_rpp.sh + camera on /tb3_2/camera/...
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROBOT=geng
# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"

# Defaults from aruco_markers/markers.yaml (Gen.G = ID 12).
eval "$(
  PYTHONPATH="${ROOT}/scripts${PYTHONPATH:+:${PYTHONPATH}}" python3 - <<'PY'
from aruco_marker_config import marker_for_robot
c = marker_for_robot("geng")
print(f'DEFAULT_MARKER_ID={c["marker_id"]}')
print(f'DEFAULT_MARKER_SIZE={c["marker_size_m"]}')
print(f'DEFAULT_TARGET_BEARING_DEG={c.get("target_bearing_deg", 0.0)}')
print(f'DEFAULT_IMAGE_TOPIC={c["image_topic"]!r}')
print(f'DEFAULT_CAMERA_INFO_TOPIC={c["camera_info_topic"]!r}')
print(f'MARKER_5CM={c["image_5cm_path"]!r}')
print(f'MARKER_A4={c["image_a4_path"]!r}')
PY
)"

IMAGE_TOPIC="${IMAGE_TOPIC:-${DEFAULT_IMAGE_TOPIC}}"
CAMERA_INFO_TOPIC="${CAMERA_INFO_TOPIC:-${DEFAULT_CAMERA_INFO_TOPIC}}"
MARKER_ID="${MARKER_ID:-${DEFAULT_MARKER_ID}}"
MARKER_SIZE="${MARKER_SIZE:-${DEFAULT_MARKER_SIZE}}"
TARGET_BEARING_DEG="${TARGET_BEARING_DEG:-${DEFAULT_TARGET_BEARING_DEG}}"

stop_robot() {
  timeout 2 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
  timeout 2 ros2 topic pub -r 20 /cmd_vel_nav geometry_msgs/msg/TwistStamped \
    "{header: {frame_id: base_footprint}, twist: {}}" >/dev/null 2>&1 || true
}

failed() {
  status=$?
  echo "[FAIL] Gen.G ArUco 도킹 중단 (exit=${status})" >&2
  stop_robot
  exit "${status}"
}
trap failed ERR INT TERM

echo "==> Gen.G marker assets"
echo "    5cm: ${MARKER_5CM}"
echo "    A4:  ${MARKER_A4}"
echo "    id=${MARKER_ID} size=${MARKER_SIZE}m target_bearing=${TARGET_BEARING_DEG}deg"
echo "    image=${IMAGE_TOPIC}"

echo "==> 1/4 Gen.G ArUco 대기장소 이동"
python3 "${ROOT}/scripts/park_geng_aruco_stage.py"

echo "==> 2/4 Gen.G ArUco 몸체 각도 정렬 (Gen.G 전용 정렬 알고리즘, ID ${MARKER_ID})"
echo "    (ArUco 뷰어가 열려 있으면 먼저 닫으세요)"
if ! timeout 6 ros2 topic echo "${IMAGE_TOPIC}" --once >/tmp/geng_aruco_cam_once.txt 2>&1; then
  echo "[FAIL] 카메라 토픽 없음: ${IMAGE_TOPIC}" >&2
  echo "       Gen.G에서 카메라(__ns:=/tb3_2)를 켠 뒤 다시 실행하세요." >&2
  tail -8 /tmp/geng_aruco_cam_once.txt >&2 || true
  exit 2
fi
python3 "${ROOT}/scripts/aruco_align_geng_bearing.py" \
  --marker-id "${MARKER_ID}" \
  --marker-size "${MARKER_SIZE}" \
  --target-bearing-deg "${TARGET_BEARING_DEG}" \
  --cmd-topic /cmd_vel_nav \
  --image-topic "${IMAGE_TOPIC}" \
  --camera-info-topic "${CAMERA_INFO_TOPIC}"

echo "==> 3/4 Gen.G 정밀 180도 회전 (odom 상대, Gen.G 정밀 제어)"
python3 "${ROOT}/scripts/rotate_geng_precise.py" --ros-args -r /cmd_vel:=/cmd_vel_nav

echo "==> 4/4 후방 라이다 저속 도킹"
python3 "${ROOT}/scripts/dock_geng_rear_wall_long.py" --ros-args -r /cmd_vel:=/cmd_vel_nav

stop_robot
trap - ERR INT TERM
echo "[OK] Gen.G ArUco 도킹 완료"
