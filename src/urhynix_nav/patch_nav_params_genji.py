#!/usr/bin/env python3
# patch_nav_params_genji.py — 젠지(tb3_2, 비-ns 표준 스택) nav2 파라미터 패치. 로봇에서 실행.
# 스톡 burger.yaml(원형 반경 0.105)을 젠지 실측 몸체로 교체: 가로 17.5 × 전장 28cm,
# 바퀴축 기준 앞 18 / 뒤 10cm (2026-07-10 사용자 실측 — 앞 돌출 비대칭).
# + 티원 검증 튜닝 이식(patch_nav_params_ns.py 근거 주석 참조: 속도캡·collision 마진·checker·Smac).
# 사용: python3 patch_nav_params_genji.py [출력경로=$HOME/nav2_tb3_2_params.yaml]
import os
import sys

import yaml

SRC = os.environ.get("NAV_PARAMS_SRC", "/opt/ros/jazzy/share/turtlebot3_navigation2/param/burger.yaml")
DST = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/nav2_tb3_2_params.yaml")

# 몸체(축 기준 앞 0.18 / 뒤 0.10 / 반폭 0.0875) + 마진 — 티원 마진 철학 승계:
# footprint +1cm, PolygonStop +1.5cm(티원 0.105→0.12과 동일 여유), Limit +4cm, Slow +7cm.
# 좌표는 [[앞좌],[앞우],[뒤우],[뒤좌]] — x+가 전방.
FOOTPRINT = "[[0.19, 0.0975], [0.19, -0.0975], [-0.11, -0.0975], [-0.11, 0.0975]]"
STOP = "[[0.195, 0.1025], [0.195, -0.1025], [-0.115, -0.1025], [-0.115, 0.1025]]"
LIMIT = "[[0.22, 0.13], [0.22, -0.13], [-0.14, -0.13], [-0.14, 0.13]]"
SLOW = "[[0.25, 0.16], [0.25, -0.16], [-0.17, -0.16], [-0.17, 0.16]]"

with open(SRC) as f:
    d = yaml.safe_load(f)

gc = d["global_costmap"]["global_costmap"]["ros__parameters"]
lc = d["local_costmap"]["local_costmap"]["ros__parameters"]
for c in (gc, lc):
    # 원형 robot_radius 대신 실측 직사각형 — DWB/collision 체크가 앞 돌출을 실제로 계산
    c["footprint"] = FOOTPRINT
    c.pop("robot_radius", None)
    # 2026-07-10 실주행 피드백 "벽은 좁혀줘": 0.17→0.13 — 벽 인접 통행 완화(inscribed 0.0975 위로 유지).
    # 장애물 쪽 여유 확대는 등방성 inflation으론 불가 → 중앙 장애물 keepout 그라데이션 마스크로 분리 예정
    # (티원 _keepout_filter_up.sh 인프라 재사용, 마스크 서버 동반 기동 필수 — 다음 기동 때 실검증)
    c["inflation_layer"]["inflation_radius"] = 0.13
    for layer in ("obstacle_layer", "voxel_layer"):
        # inf 리턴을 유효 clearing 광선으로 — 유령 장애물 잔존 방지(티원 2026-07-08)
        c[layer]["scan"]["inf_is_valid"] = True

cm = d["collision_monitor"]["ros__parameters"]
# 스톡 PolygonStop은 원형(radius) — 원으로 전장 28cm를 덮으면 회랑에서 상시 하드스톱이라 몸체형 사각으로 교체
cm["PolygonStop"]["type"] = "polygon"
cm["PolygonStop"]["points"] = STOP
cm["PolygonStop"].pop("radius", None)
cm["PolygonSlow"]["points"] = SLOW
cm["PolygonSlow"]["slowdown_ratio"] = 0.35
cm["PolygonLimit"]["points"] = LIMIT
cm["PolygonLimit"]["linear_limit"] = 0.05
cm["PolygonLimit"]["angular_limit"] = 0.2
# 스톡은 PolygonLimit을 정의만 하고 활성 리스트에 안 넣음(티원 2026-07-03 발견)
if "PolygonLimit" not in cm["polygons"]:
    cm["polygons"].append("PolygonLimit")
# Pi 부하 전송지연 0.2~0.36s가 스톡 source_timeout 0.2를 상시 초과 → invalid source 정지(티원 함정#15)
cm["scan"]["source_timeout"] = 1.0

fp = d["controller_server"]["ros__parameters"]["FollowPath"]
fp["max_vel_x"] = 0.12
fp["max_vel_theta"] = 0.4
fp["max_speed_xy"] = 0.12
fp["acc_lim_x"] = 0.5
fp["decel_lim_x"] = -0.5
fp["acc_lim_theta"] = 1.2
fp["decel_lim_theta"] = -1.2
d["controller_server"]["ros__parameters"]["goal_checker"]["xy_goal_tolerance"] = 0.15
# 도착 yaw 강제 해제 — 주차 방향은 bridge Spin 담당(티원 2026-07-09). 전장 28cm 젠지는 회랑 내 회전 불가라 더 중요
d["controller_server"]["ros__parameters"]["goal_checker"]["yaw_goal_tolerance"] = 6.28
d["controller_server"]["ros__parameters"]["progress_checker"]["movement_time_allowance"] = 20.0
d["bt_navigator"]["ros__parameters"]["default_server_timeout"] = 200

# Smac 2D는 설치돼 있을 때만(티원은 별도 apt 설치했음 — 젠지 미확인). 없으면 스톡 NavFn 유지
if os.path.isdir("/opt/ros/jazzy/share/nav2_smac_planner"):
    d["planner_server"]["ros__parameters"]["GridBased"] = {
        "plugin": "nav2_smac_planner::SmacPlanner2D",
        "tolerance": 0.125,
        "downsample_costmap": False,
        "allow_unknown": True,
        "max_iterations": 1000000,
        "max_on_approach_iterations": 1000,
        "max_planning_time": 2.0,
        "cost_travel_multiplier": 1.0,
        "use_final_approach_orientation": False,
        "smoother": {"max_iterations": 1000, "w_smooth": 0.3, "w_data": 0.2, "tolerance": 1.0e-10},
    }
    # Smac 플랜 ~560ms — 스톡 10Hz 재플랜이면 Pi 포화로 제어루프 붕괴(티원 2026-07-09)
    d["planner_server"]["ros__parameters"]["expected_planner_frequency"] = 1.0
else:
    print("경고: nav2_smac_planner 미설치 — NavFn 유지 (원하면: sudo apt install ros-jazzy-nav2-smac-planner)")

with open(DST, "w") as f:
    yaml.safe_dump(d, f, sort_keys=False)

print("written:", DST)
