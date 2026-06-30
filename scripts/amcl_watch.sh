#!/bin/bash
# amcl_watch.sh — ns AMCL 위치추정 ground-truth 모니터(Mac에서 실행 → 로봇 ssh). teleop 주행 중 amcl_pose가
#   실제 위치로 자연수렴하는지(① 검증) 수치로 본다: position(x,y) + covariance[0]=σ²xx.
#   판정: 주행하면 x/y가 실제 이동과 같은 방향으로 변하고 cov_xx가 줄면 정상수렴. 좌표가 시드에서 안 변하거나
#   180° 대칭점(부호 반전)으로 점프하면 대칭-락(거짓수렴).
# 사용: bash scripts/amcl_watch.sh <t1|g1|user@ip> [tb3_1|tb3_2] [count] [interval_s]
#   id 생략 시 host로 추정(t1→tb3_1, g1→tb3_2). count 기본 20, interval 기본 3s.
set -u
H="${1:-}"
if [ -z "$H" ]; then echo "usage: amcl_watch.sh <t1|g1|user@ip> [tb3_1|tb3_2] [count] [interval]"; exit 1; fi
ID="${2:-}"
if [ -z "$ID" ]; then case "$H" in t1*|*250*) ID=tb3_1;; g1*|*84*) ID=tb3_2;; *) ID=tb3_1;; esac; fi
CNT="${3:-20}"; INT="${4:-3}"
SSH="ssh -o ConnectTimeout=10 -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

$SSH "$H" "bash -lc '
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
echo \"[amcl_watch $ID] cnt=$CNT int=${INT}s  (position x,y / cov_xx=σ²)\"
for i in \$(seq 1 $CNT); do
  POS=\$(timeout 8 ros2 topic echo --once --field pose.pose.position /$ID/amcl_pose 2>/dev/null | grep -E \"x:|y:\" | tr \"\\n\" \" \")
  CXX=\$(timeout 8 ros2 topic echo --once --field pose.covariance /$ID/amcl_pose 2>/dev/null | grep -oE \"[-0-9.eE]+\" | head -1)
  if [ -z \"\$POS\" ]; then echo \"  t\$i: (no amcl_pose — bringup/amcl/scan 확인)\"; else echo \"  t\$i: \$POS cov_xx=\${CXX:-?}\"; fi
  sleep $INT
done
echo \"--- tf map -> $ID/base_footprint (수렴 시 latch) ---\"
timeout 4 ros2 run tf2_ros tf2_echo map $ID/base_footprint 2>/dev/null | grep -A1 Translation | head -2 || echo no-tf
'"
