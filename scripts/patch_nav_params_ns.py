#!/usr/bin/env python3
# patch_nav_params_ns.py — turtlebot3_navigation2 burger.yaml(비-ns 기본값)을 tb3_1 네임스페이스
# 실제 프레임(tb3_1/base_footprint, tb3_1/odom)/스캔 토픽(/tb3_1/scan_fixed)에 맞게 패치.
# 로봇에서 실행: python3 patch_nav_params_ns.py  → /home/t1/nav2_tb3_1_params.yaml 생성.
# [[urhynix-t1-nav2-lifecycle-abi]] 순회 실주행 세션(2026-07-01)에서 검증.
import argparse

import yaml

ap = argparse.ArgumentParser()
# keepout은 마스크 서버(_keepout_filter_up.sh)까지 같이 떠야만 유효 — 서버 없이 filters만 있으면
# "KeepoutFilter mask not received"로 costmap이 영구 미완성(주행 불능, 2026-07-08 실측). 기본 OFF.
ap.add_argument("--keepout", action="store_true", help="keepout filter 주입(마스크 서버 기동 전제)")
args = ap.parse_args()

SRC = "/opt/ros/jazzy/share/turtlebot3_navigation2/param/burger.yaml"
DST = "/home/t1/nav2_tb3_1_params.yaml"
BASE = "tb3_1/base_footprint"
ODOM = "tb3_1/odom"
SCAN = "/tb3_1/scan_fixed"

with open(SRC) as f:
    d = yaml.safe_load(f)

d["bt_navigator"]["ros__parameters"]["robot_base_frame"] = BASE

gc = d["global_costmap"]["global_costmap"]["ros__parameters"]
gc["robot_base_frame"] = BASE
gc["global_frame"] = "map"
for layer in ("obstacle_layer", "voxel_layer"):
    gc[layer]["scan"]["topic"] = SCAN
    # inf 리턴(무반사 표면)을 유효 clearing 광선으로 — false면 그 광선이 버려져
    # 장애물이 비켜도 costmap에 유령으로 잔존(영구 정지 유발, 2026-07-08 웹조사)
    gc[layer]["scan"]["inf_is_valid"] = True

lc = d["local_costmap"]["local_costmap"]["ros__parameters"]
lc["robot_base_frame"] = BASE
lc["global_frame"] = ODOM
for layer in ("obstacle_layer", "voxel_layer"):
    lc[layer]["scan"]["topic"] = SCAN
    lc[layer]["scan"]["inf_is_valid"] = True

bs = d["behavior_server"]["ros__parameters"]
bs["robot_base_frame"] = BASE
bs["local_frame"] = ODOM
bs["global_frame"] = "map"

cm = d["collision_monitor"]["ros__parameters"]
cm["base_frame_id"] = BASE
cm["odom_frame_id"] = ODOM
cm["scan"]["topic"] = SCAN
cm["FootprintApproach"]["footprint_topic"] = "/tb3_1/local_costmap/published_footprint"

d["velocity_smoother"]["ros__parameters"]["enable_stamped_cmd_vel"] = True
d["velocity_smoother"]["ros__parameters"]["odom_topic"] = "odom"

# 소형 아레나(1.9x1.9m) 대비 기본 inflation_radius(0.5m)가 과대 —
# 방 바닥의 25%+ 를 위험지대로 깔아 벽 인접 웨이포인트 planning 실패 유발.
# [[urhynix-t1-nav2-patrol-drive]] 확장, 2026-07-03 (하이쿠 조사 근거: TB3 표준 예시도
# robot_radius 대비 ~3.2배 비율이라 0.35m 자체는 비율상 정상 범위)
for cm_params in (gc, lc):
    cm_params["inflation_layer"]["inflation_radius"] = 0.15  # 2026-07-09: 0.20→0.15 — 중앙장애물↔벽 병목 36cm(맵 거리변환 실측). 반폭 18cm라 0.20이면 회랑 전체 cost~170으로 차서 통과 회피/실패, 0.15면 중심선에 저비용 띠 생김(로봇반경 0.105 대비 4.5cm 여유 유지)

# 보호대상 keepout zone(nav2 Costmap Filter) — [[urhynix-t1-nav2-patrol-drive]] 확장, 2026-07-01
# 2026-07-08: --keepout 플래그 뒤로 게이트(기본 OFF) — [[urhynix-t1-nav2-keepout-filter]] 사용 시에만.
if args.keepout:
    FILTER_INFO_TOPIC = "/tb3_1/costmap_filter_info"
    for cm_params in (gc, lc):
        cm_params["filters"] = ["keepout_filter"]
        cm_params["keepout_filter"] = {
            "plugin": "nav2_costmap_2d::KeepoutFilter",
            "enabled": True,
            "filter_info_topic": FILTER_INFO_TOPIC,
        }

# 속도/충돌마진 대폭 하향 — 2026-07-03 젠지와 실충돌(순회 중 정지장애물에 접촉) 후 조치.
# 원인 3중첩: ①max_vel_x=0.3+acc_lim_x=3.0(스톡값)이 1.9x1.9m 방엔 과속·급가속
# ②collision_monitor PolygonStop 반경 0.1m=로봇 몸통 반경과 거의 같아 "닿기 직전"이 아니라
#   "이미 닿는 시점"에야 반응 ③라이다 타임스탬프 스큐(0.2~0.45s)로 안전레이어가 간헐적으로
# 자기 센서를 못 믿고 stop/approach 사이 flapping. 속도·마진을 크게 낮춰 물리적 여유를 확보.
# [[urhynix-t1-nav2-patrol-drive]] 확장.
fp = d["controller_server"]["ros__parameters"]["FollowPath"]
fp["max_vel_x"] = 0.12  # 2026-07-08: 0.08→0.12 — 마진3중+타임스탬프 수정 후 여유 확인, 사고값 0.3의 40%
fp["max_vel_theta"] = 0.4
fp["max_speed_xy"] = 0.12
fp["acc_lim_x"] = 0.5
fp["decel_lim_x"] = -0.5
fp["acc_lim_theta"] = 1.2
fp["decel_lim_theta"] = -1.2

# 2026-07-03 2차 조정: 위 0.30/0.45/0.4m는 이 방(1.9x1.9m) 대비 과대했음 — 충전독 출발점부터
# 벽까지 0.28~0.30m라 PolygonStop(0.30m)이 출발 즉시 벽 자체를 장애물로 오인해 하드스톱
# ("Robot to stop due to PolygonStop polygon" 로그로 확정, 장애물 없이도 0.08m/s로 60초+ 전진 0).
# patrol_safe_clearance.py가 웨이포인트-벽 최소간격을 0.25m로 보장하므로 마진은 그보다 작아야
# 정상 경로를 장애물로 안 봄. 로봇 물리반경 ~0.105m 대비 첫 사고(0.1m)보단 확실히 여유 있고
# 0.25m 벽간격은 안 침범하는 값으로 축소.
cm["PolygonStop"]["radius"] = 0.12  # 2026-07-09: 0.14→0.12 — 병목 36cm 회랑 반폭 18cm에서 0.14는 여유 4cm뿐(AMCL 오차±5cm에 통과 중 상시 하드스톱). 0.12=몸통 0.105+1.5cm; 회랑 내 속도는 PolygonSlow/Limit이 0.024~0.05로 이미 눌러줌
cm["PolygonSlow"]["points"] = "[[0.18, 0.18], [0.18, -0.18], [-0.18, -0.18], [-0.18, 0.18]]"
cm["PolygonSlow"]["slowdown_ratio"] = 0.2
cm["PolygonLimit"]["points"] = "[[0.16, 0.16], [0.16, -0.16], [-0.16, -0.16], [-0.16, 0.16]]"
cm["PolygonLimit"]["linear_limit"] = 0.05
cm["PolygonLimit"]["angular_limit"] = 0.2
# 스톡 TB3 burger.yaml 자체가 PolygonLimit을 정의만 하고 활성 polygons 리스트엔 안 넣어놔서
# (2026-07-03 재검증 중 발견) 위 값들이 지금까지 한 번도 실제로 로드된 적이 없었음 — 추가.
if "PolygonLimit" not in cm["polygons"]:
    cm["polygons"].append("PolygonLimit")

# 2026-07-08: 스캔 소스 source_timeout 0.2(스톡)는 Pi 부하 전송지연 0.2~0.36s에 상시 걸려
# "invalid source → stop" 영구 정지(함정#15). 어제 로봇 yaml 직접 수정분을 스크립트에 영속화.
cm["scan"]["source_timeout"] = 1.0

# 2026-07-08: 도착 정밀도 0.25→0.15 (3.5cm 도착 실측 이력, stateful=true라 진동 방어)
d["controller_server"]["ros__parameters"]["goal_checker"]["xy_goal_tolerance"] = 0.15

# 2026-07-09: 순찰은 도착 방향이 무의미한데 Unity 웨이포인트가 전부 theta=0이라 매 도착마다
# 제자리 회전 강제 — 벽 인접(실측 0.21m) 지점에선 회전 스윕을 collision monitor가 눌러 멈추고,
# 회전은 병진 진행률에 안 잡혀 "Failed to make progress" 레그 실패(WP5 실측). 최종 yaw 체크 해제.
d["controller_server"]["ros__parameters"]["goal_checker"]["yaw_goal_tolerance"] = 6.28

# 2026-07-09: bt_navigator 액션 ack 대기 기본 20ms가 Pi 부하 스파이크에 순간 초과 →
# "Timed out ... acknowledge goal request for compute_path_to_pose" 즉시 실패(WP6 실측) → 200ms.
d["bt_navigator"]["ros__parameters"]["default_server_timeout"] = 200

# 2026-07-09: 회랑(36cm)에서 PolygonSlow/Limit이 0.02~0.05m/s로 누르는 동안 정렬회전·감속이
# 겹치면 10초 창을 간헐 초과("Failed to make progress" 3회/1주행 실측, 통과는 함) → 창만 2배.
# 반경 0.1은 유지 — 진짜 스턱 판정 능력은 보존.
d["controller_server"]["ros__parameters"]["progress_checker"]["movement_time_allowance"] = 20.0

# 2026-07-08: 전역 플래너 NavFn→Smac 2D — 협소공간 경로질·속도(2~3배) 우위(웹조사),
# 벽 인접 "경로 없음" 완화 목적. 플러그인 설치 확인됨(ros-jazzy-nav2-smac-planner 1.3.12).
d["planner_server"]["ros__parameters"]["GridBased"] = {
    "plugin": "nav2_smac_planner::SmacPlanner2D",
    "tolerance": 0.125,
    "downsample_costmap": False,
    "allow_unknown": True,
    "max_iterations": 1000000,
    "max_on_approach_iterations": 1000,
    "max_planning_time": 2.0,
    "cost_travel_multiplier": 1.0,  # 2026-07-09: 2.0→1.0 — nav2 공식 가이드: 좁은 통로는 낮춰야 고비용 회랑을 경로로 허용(2.0은 병목 회피 성향)
    "use_final_approach_orientation": False,
    "smoother": {"max_iterations": 1000, "w_smooth": 0.3, "w_data": 0.2, "tolerance": 1.0e-10},
}
# 2026-07-09: Smac 2D는 NavFn(수 ms)보다 플랜이 무거워(부하 시 회당 ~560ms 실측) 스톡 10Hz
# 상시 재플랜이 Pi를 포화 — planner 1.78Hz·control loop 10→1.5Hz 붕괴, compute_path_to_pose
# ack 타임아웃, cmd 스트림 끊겨 "Failed to make progress" 중단(회랑 통과 실패의 실제 원인).
# 0.12m/s에선 1Hz 재플랜(=12cm마다)이면 충분.
d["planner_server"]["ros__parameters"]["expected_planner_frequency"] = 1.0

with open(DST, "w") as f:
    yaml.safe_dump(d, f, sort_keys=False)

print("written:", DST)
