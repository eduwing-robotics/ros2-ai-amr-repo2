#!/bin/bash
# dual_amcl_up.sh — ns 듀얼 AMCL 멀티 endpoint 한방 기동(Mac에서 실행). dual_marker_up.sh(odom)의 AMCL 정본.
#   ★전제: 두 로봇을 충전소에 도킹한 뒤 실행. set_initial_pose로 충전소 좌표를 시드 → 무-teleop 자동 위치추정.
#   ★모션 없음: bringup(gyro캘리)+AMCL은 수동 위치추정만 — 로봇을 움직이지 않는다(주행=별도 teleop).
#   하는 일(로봇별 순차): 비-ns Nav2/이전 ns 스택 정리 → 의존물 scp → bringup_ns → amcl_ns(시드) → pose_ep(yes).
# 사용: bash scripts/dual_amcl_up.sh [T1_SSH] [GENJI_SSH]
#   (기본 ssh alias t1/g1. IP drift로 alias가 안 맞으면 user@ip로 덮어쓰기.)
# 좌표계: office_base_map.json displayRotationDeg=90 → 맵+x=화면아래 / 맵+y=화면오른쪽.
#   시드: 티원(tb3_1) 왼=(0.78,-0.85) / 젠지(tb3_2) 오른=(0.78,-0.45), yaw=-2.46rad 공통.
#   ⚠️ 좌표는 시각배치 기준 provisional — 실라이다 자연수렴 검증(amcl_watch.sh + teleop) 전까지 잠정.
set -u
T1=${1:-t1}
GENJI=${2:-g1}
D="$(cd "$(dirname "$0")" && pwd)"
# ServerAlive*: 연결 establish 후 wifi stall(codelab_robot_team_2_5G 불안정) 시 ~15s에 끊고 넘어감(무한 hang 방지).
SSHO="-o ConnectTimeout=12 -o ServerAliveInterval=5 -o ServerAliveCountMax=3 -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
SSH="ssh $SSHO"
MAP='$HOME/maps/arena_v5/arena_v5.yaml'   # 작은따옴표: 로봇 원격 셸에서 $HOME 확장

# bring_one <id> <ssh_host> <ix> <iy> <iyaw_rad> <ep:yes|no>
bring_one() {
  id="$1"; h="$2"; ix="$3"; iy="$4"; iyaw="$5"; ep="$6"
  echo "===== $id @ $h  seed=($ix,$iy,yaw=$iyaw)  ep=$ep ====="

  # 1) 의존물 최신화: 홈(launch/py) + /tmp(런처). scp hang 시 stdin fallback.
  for f in dual_bringup.launch.py scan_frame_fix.py robot_pose_publisher.py; do
    scp $SSHO "$D/$f" "$h":~/  2>/dev/null || $SSH "$h" "cat > ~/$f"   < "$D/$f"
  done
  for f in _robot_bringup_ns.sh _robot_amcl_ns.sh _pose_ep_up.sh; do
    scp $SSHO "$D/$f" "$h":/tmp/ 2>/dev/null || $SSH "$h" "cat > /tmp/$f" < "$D/$f"
  done

  # 2) 비-ns Nav2(nav_up.sh 계열)·이전 ns 스택 정리 (bracket 트릭: 원격 pkill 자기-kill 회피)
  $SSH "$h" "for p in '[a]mcl' '[m]ap_server' '[g]lobal_costmap' '[l]ocal_costmap' '[c]ontroller_server' '[r]obot.launch.py' '[s]can_frame_fix' '[d]efault_server_endpoint' '[r]obot_pose_publisher'; do pkill -9 -f \"\$p\" 2>/dev/null; done; sleep 2; echo cleaned-$id"

  # 3) 3단 기동 (각 스크립트가 setsid로 백그라운드화 → ssh 반환 후에도 생존)
  $SSH "$h" "bash /tmp/_robot_bringup_ns.sh $id"            2>&1 | tail -2
  $SSH "$h" "bash /tmp/_robot_amcl_ns.sh $id $MAP $ix $iy $iyaw" 2>&1 | tail -4
  $SSH "$h" "bash /tmp/_pose_ep_up.sh $id $ep"              2>&1 | tail -2
  echo
}

echo "== dual_amcl_up: ns 듀얼 AMCL 멀티 endpoint 기동 (t1=$T1 / g1=$GENJI) =="
bring_one tb3_1 "$T1"    0.78 -0.85 -2.46 yes
bring_one tb3_2 "$GENJI" 0.78 -0.45 -2.46 yes

echo "DONE. Unity Stop→Play → 충전소에 티원(초록,왼)·젠지(파랑,오) 2마커."
echo "검증(①): bash scripts/amcl_watch.sh t1 ; bash scripts/amcl_watch.sh g1 로 amcl_pose+cov 수렴 관찰 후 teleop 주행."
