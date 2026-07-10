#!/bin/bash
# dual_marker_up.sh — odom-only 듀얼 마커 한방 기동(Mac에서 실행). AMCL 없음.
# ★전제: 두 로봇을 충전소에 도킹한 뒤 실행 (odom 원점=충전소=오프셋이라 마커가 충전소에서 시작).
# 하는 일: odom_to_pose.py+_robot_up.sh를 양 로봇에 scp → 티원(왼쪽)·젠지(오른쪽+endpoint) 기동.
# 사용: bash scripts/dual_marker_up.sh [T1_SSH] [GENJI_SSH]   (IP drift 시 인자로 덮어쓰기)
# Unity: ros_endpoint.json = 젠지 IP 여야 함. 마커색 티원=초록#34D98C / 젠지=파랑#4DA3FF.
set -u
T1=${1:-t1@192.168.10.250}
GENJI=${2:-kim@192.168.10.84}
D="$(cd "$(dirname "$0")" && pwd)"
SSH="ssh -o ConnectTimeout=12 -o ControlMaster=no"

echo "== scp odom_to_pose.py + _robot_up.sh =="
for H in "$T1" "$GENJI"; do
  scp -o ConnectTimeout=10 "$D/odom_to_pose.py" "$H":/tmp/ || { echo "scp 실패: $H"; exit 1; }
  scp -o ConnectTimeout=10 "$D/_robot_up.sh"    "$H":/tmp/ || { echo "scp 실패: $H"; exit 1; }
done

# 맵 x축=화면세로, y축=화면가로(+y=왼쪽). 충전소≈(0,0)에 가로로 나란히: 티원 +y(왼), 젠지 -y(오).
echo "== 티원(tb3_1) 왼쪽 + endpoint =="
# 티원 endpoint 필수: Unity RosConnectionManager가 로봇간 AP isolation 때문에 로봇별 전용
# endpoint(.250:10000)에 직접 붙는다. no면 티원 /tb3_1/pose를 Unity가 못 받아 초록 마커가 안 뜬다.
$SSH "$T1"    'bash /tmp/_robot_up.sh tb3_1 0.0 0.1 yes'
echo "== 젠지(tb3_2) 오른쪽 + endpoint =="
$SSH "$GENJI" 'bash /tmp/_robot_up.sh tb3_2 0.0 -0.1 yes'

echo "DONE. Unity Stop→Play → 충전소에 티원(초록,왼)·젠지(파랑,오) 2마커."
