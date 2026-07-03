#!/usr/bin/env python3
# patch_nav_params_ns.py — turtlebot3_navigation2 burger.yaml(비-ns 기본값)을 tb3_1 네임스페이스
# 실제 프레임(tb3_1/base_footprint, tb3_1/odom)/스캔 토픽(/tb3_1/scan_fixed)에 맞게 패치.
# 로봇에서 실행: python3 patch_nav_params_ns.py  → /home/t1/nav2_tb3_1_params.yaml 생성.
# [[urhynix-t1-nav2-lifecycle-abi]] 순회 실주행 세션(2026-07-01)에서 검증.
import yaml

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

lc = d["local_costmap"]["local_costmap"]["ros__parameters"]
lc["robot_base_frame"] = BASE
lc["global_frame"] = ODOM
for layer in ("obstacle_layer", "voxel_layer"):
    lc[layer]["scan"]["topic"] = SCAN

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
    cm_params["inflation_layer"]["inflation_radius"] = 0.35

# 보호대상 keepout zone(nav2 Costmap Filter) — [[urhynix-t1-nav2-patrol-drive]] 확장, 2026-07-01
FILTER_INFO_TOPIC = "/tb3_1/costmap_filter_info"
for cm_params in (gc, lc):
    cm_params["filters"] = ["keepout_filter"]
    cm_params["keepout_filter"] = {
        "plugin": "nav2_costmap_2d::KeepoutFilter",
        "enabled": True,
        "filter_info_topic": FILTER_INFO_TOPIC,
    }

with open(DST, "w") as f:
    yaml.safe_dump(d, f, sort_keys=False)

print("written:", DST)
