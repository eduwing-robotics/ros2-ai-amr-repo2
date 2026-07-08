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

# 속도/충돌마진 대폭 하향 — 2026-07-03 젠지와 실충돌(순회 중 정지장애물에 접촉) 후 조치.
# 원인 3중첩: ①max_vel_x=0.3+acc_lim_x=3.0(스톡값)이 1.9x1.9m 방엔 과속·급가속
# ②collision_monitor PolygonStop 반경 0.1m=로봇 몸통 반경과 거의 같아 "닿기 직전"이 아니라
#   "이미 닿는 시점"에야 반응 ③라이다 타임스탬프 스큐(0.2~0.45s)로 안전레이어가 간헐적으로
# 자기 센서를 못 믿고 stop/approach 사이 flapping. 속도·마진을 크게 낮춰 물리적 여유를 확보.
# [[urhynix-t1-nav2-patrol-drive]] 확장.
fp = d["controller_server"]["ros__parameters"]["FollowPath"]
fp["max_vel_x"] = 0.08
fp["max_vel_theta"] = 0.4
fp["max_speed_xy"] = 0.08
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
cm["PolygonStop"]["radius"] = 0.18
cm["PolygonSlow"]["points"] = "[[0.22, 0.22], [0.22, -0.22], [-0.22, -0.22], [-0.22, 0.22]]"
cm["PolygonSlow"]["slowdown_ratio"] = 0.2
cm["PolygonLimit"]["points"] = "[[0.20, 0.20], [0.20, -0.20], [-0.20, -0.20], [-0.20, 0.20]]"
cm["PolygonLimit"]["linear_limit"] = 0.05
cm["PolygonLimit"]["angular_limit"] = 0.2
# 스톡 TB3 burger.yaml 자체가 PolygonLimit을 정의만 하고 활성 polygons 리스트엔 안 넣어놔서
# (2026-07-03 재검증 중 발견) 위 값들이 지금까지 한 번도 실제로 로드된 적이 없었음 — 추가.
if "PolygonLimit" not in cm["polygons"]:
    cm["polygons"].append("PolygonLimit")

with open(DST, "w") as f:
    yaml.safe_dump(d, f, sort_keys=False)

print("written:", DST)
