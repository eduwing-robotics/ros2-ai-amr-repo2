#!/bin/bash
# t1_drive_ready.sh — 티원(tb3_1) "충전독에서 주행준비" 원버튼 오케스트레이터(로봇에서 실행).
#   bringup(도메인2)→배터리게이트→params 재생성→AMCL+dock 재시딩→scanfix 중복정리→
#   nav2 8노드 lifecycle(configure/activate)→최종 검증까지 한 번에. 끝에 DRIVE-READY PASS/FAIL 1줄.
#   이번(2026-07-09) 세션에 손으로 성공한 명령 시퀀스를 그대로 묶은 것 — 개별 스크립트는 재사용만 함.
# ⚠️ 전제: 로봇이 충전독(arena_shared x=0.038,y=1.405,yaw=0.293)에 물리적으로 놓여 있을 때만 안전
#    (dock 재시딩=위치 선언, amcl 스킬 함정#4 — 손으로 옮긴 직후엔 DX/DY/DYAW 인자를 바꿔 호출).
# 사용: bash ~/t1_drive_ready.sh [ns=tb3_1] [dx] [dy] [dyaw] [domain=2]
# 종료코드: 0=DRIVE-READY, 1=중단(단계별 FAIL 사유 출력)
set +u
NS=${1:-tb3_1}; DX=${2:-0.038}; DY=${3:-1.405}; DYAW=${4:-0.293}; DOM=${5:-2}
USB=/dev/ttyACM0
MIN_V=11.3                                # 이 전압 미만이면 저전압으로 중단(nav2 activate FAIL 회피)
MAP="$HOME/maps/arena_shared/arena_shared.yaml"
NODES="controller_server smoother_server planner_server behavior_server bt_navigator waypoint_follower velocity_smoother collision_monitor"
SRC="source /opt/ros/jazzy/setup.bash; source $HOME/turtlebot3_ws/install/setup.bash 2>/dev/null; export ROS_DOMAIN_ID=$DOM RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET"

say(){ echo "[t1-ready] $*"; }
fail(){ echo "[t1-ready] FAIL: $*"; exit 1; }

# 0. 프리플라이트 — OpenCR
[ -c "$USB" ] || fail "OpenCR $USB 없음 (USB/전원 확인)"

# 1. bringup (도메인 명시) + odom 발행 확인
say "1/6 bringup (도메인 $DOM)"
bash "$HOME/_robot_bringup_ns.sh" "$NS" "$USB" "$DOM" >/dev/null 2>&1
eval "$SRC"
pc=""
for i in $(seq 1 15); do
  pc=$(timeout 4 ros2 topic info /$NS/odom 2>/dev/null | awk '/Publisher/{print $3}')
  [ "$pc" = "1" ] && break; sleep 1
done
[ "$pc" = "1" ] || fail "odom 발행자 없음 (bringup 실패 — /tmp/nsbu_$NS.log 확인)"
grep -qiE "stack smashing|no status packet|TxRxResult" /tmp/nsbu_$NS.log && fail "OpenCR 크래시 시그니처 감지 — 물리연결 점검"

# 2. 배터리 게이트
V=$(timeout 8 ros2 topic echo --once /$NS/battery_state 2>/dev/null | awk '/^voltage:/{print $2}')
if [ -z "$V" ]; then
  say "2/6 배터리 판독 실패 — 게이트 건너뜀(주의: activate 단계에서 저전압이면 드러남)"
else
  say "2/6 배터리 ${V}V (게이트 ${MIN_V}V)"
  awk "BEGIN{exit !($V+0 < $MIN_V)}" && fail "저전압 ${V}V < ${MIN_V}V — 충전 후 재시도(activate FAIL 회피)"
fi

# 3. nav params 재생성 (함정#12: 로봇 배포본 실행해야 반영)
say "3/6 nav params 재생성"
python3 "$HOME/patch_nav_params_ns.py" >/dev/null 2>&1 || fail "patch_nav_params_ns.py 실패"

# 4. AMCL/map_server + scanfix 중복정리 + dock 재시딩
say "4/6 AMCL/map_server + dock 재시딩"
[ -f "$MAP" ] || fail "맵 없음: $MAP"
bash "$HOME/_robot_amcl_ns.sh" "$NS" "$MAP" "" "" "" "$DOM" >/dev/null 2>&1
MPID=$(systemctl --user show -p MainPID --value urhynix-scanfix 2>/dev/null)   # systemd 관리본만 유지
for p in $(pgrep -f "[s]can_frame_fix"); do [ "$p" != "$MPID" ] && kill -9 "$p" 2>/dev/null; done
bash "$HOME/_dock_reseed.sh" "$NS" "$DX" "$DY" "$DYAW" "$DOM" >/dev/null 2>&1
read px py < <(timeout 6 ros2 topic echo --once /$NS/amcl_pose 2>/dev/null | awk '/^      x:/{x=$2} /^      y:/{y=$2} END{print x, y}')
[ -n "$px" ] || fail "amcl_pose 무응답"
awk "BEGIN{exit !(($px+0<-5)||($px+0>5)||($py+0<-5)||($py+0>5))}" && fail "amcl_pose 발산 ($px,$py)"
say "    amcl_pose=($px,$py) — 충전독 수렴"

# 5. nav2 8노드 기동 + lifecycle configure→activate
say "5/6 nav2 8노드 기동 + lifecycle"
bash "$HOME/_restart_nav_ns.sh" >/dev/null 2>&1
for i in $(seq 1 20); do
  n=$(ros2 node list 2>/dev/null | grep -c "/$NS/\(controller_server\|collision_monitor\)")
  [ "$n" = "2" ] && break; sleep 1
done
for n in $NODES; do timeout 12 ros2 lifecycle set /$NS/$n configure >/dev/null 2>&1; done
for n in $NODES; do timeout 12 ros2 lifecycle set /$NS/$n activate  >/dev/null 2>&1; done

# 6. 최종 검증
say "6/6 검증"
bad=0
for n in $NODES; do
  st=$(timeout 6 ros2 lifecycle get /$NS/$n 2>/dev/null | tail -1)
  case "$st" in active*) ;; *) echo "    $n=$st"; bad=1;; esac
done
[ "$bad" = "0" ] || fail "8노드 중 일부 미활성"
timeout 8 ros2 action list 2>/dev/null | grep -q "/$NS/navigate_to_pose" || fail "navigate_to_pose 액션서버 없음"
pr=$(timeout 8 ros2 param get /$NS/collision_monitor PolygonStop.radius 2>/dev/null | grep -oE "[0-9.]+$")
echo ""
echo "===================================================="
echo "  DRIVE-READY: PASS  (배터리 ${V}V · PolygonStop ${pr}m · amcl=($px,$py))"
echo "  → Unity '순찰 시작' 또는 /$NS/patrol_waypoints 발행하면 주행"
echo "===================================================="
exit 0
