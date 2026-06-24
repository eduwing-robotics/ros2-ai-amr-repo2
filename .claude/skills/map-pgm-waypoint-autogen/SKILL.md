---
name: map-pgm-waypoint-autogen
description: 저장된 점유격자맵(.pgm/.yaml)을 분석해 벽에서 안전거리(클리어런스)만큼 띄운 자유공간에 순찰 웨이포인트 N개를 자동 생성하는 표준. 클리어런스 침식 + farthest-point sampling 분포 + 폴라 정렬 루프 + yaw(다음점 향함)+쿼터니언 → Nav2 FollowWaypoints YAML + ASCII 오버레이 검증. 텔레옵이 불가하거나 빠른 초안이 필요할 때. URHYNIX arena 맵. 2026-06-23 도출.
user_invocable: true
tags: [nav2, waypoint, map, occupancy-grid, urhynix]
version: 1
---

# Map PGM Waypoint Autogen

저장된 점유격자맵에서 **장애물을 피해 안전한 순찰 웨이포인트**를 자동으로 뽑는다. 로봇을 직접 몰 수 없거나([[urhynix-teleop-waypoint-capture]] 불가), 빠른 초안이 필요할 때.

## Use When

- `.pgm/.yaml` 맵은 있는데 순찰 좌표가 없을 때
- 텔레옵 캡처 전에 후보 경로를 미리 그려보고 싶을 때
- 맵이 바뀌어 좌표를 다시 깔아야 할 때

## 입력 / 출력

- 입력: `map.pgm` + `map.yaml`(origin·resolution), 점 개수 N, 클리어런스(m), 시작 좌표(선택)
- 출력: `waypoints_<robot>.yaml`(frame_id:map + position + orientation 쿼터니언) + ASCII 오버레이

## One-Liner

```bash
python3 .claude/skills/map-pgm-waypoint-autogen/gen_waypoints.py \
  --pgm map.pgm --yaml map.yaml --n 8 --clearance 0.15 \
  --start 0.0,0.0 --robot tb3_1 --out waypoints_tb3_1.yaml
```

## 알고리즘 (gen_waypoints.py)

1. **분류:** PGM 값 ≥250=free, ≤50=occupied, 그 외=unknown.
2. **클리어런스 침식:** free 셀 중 반경 R(=clearance/res)칸 안에 occupied가 없는 셀만 "안전셀". (로봇 반경 회피)
3. **좌표 변환:** `x = origin_x + (col+0.5)*res`, `y = origin_y + (h-1-row+0.5)*res` (PGM 맨 아래행이 origin).
4. **분포:** start에서 가까운 안전셀을 seed로 **farthest-point sampling**으로 N점 고름(고르게 퍼짐).
5. **루프 정렬:** 무게중심 기준 폴라각 정렬 → 경로 교차 최소화.
6. **방향:** 각 점 yaw = 다음 점을 바라보는 각 → 쿼터니언(z,w)로 변환.

## 함정표

| 함정 | 회피 |
|---|---|
| y축 뒤집힘 | ROS map은 PGM 맨 아래행=origin → `y=origin_y+(h-1-row)*res` |
| 클리어런스 과대 | 작은 방(예 2.85×2.9m)은 R=3(0.15m) 권장, R↑면 안전셀 0 위험 |
| 벽 붙은 점 | 침식으로 거른 안전셀만 후보 → occupied 인접 자동 배제 |
| 칸막이 가로지름 | waypoint는 자유공간이면 유효, 경로는 Nav2가 알아서 우회 |

## 검증

- ASCII 오버레이에서 S/1~N이 전부 `.`(free) 위에 있고 `#`(벽)에 안 붙는지 확인.
- 안전셀 수가 충분(>N×10)한지 로그 확인.

## ⚠️ 프레임 안정성

생성 좌표는 그 맵 origin 기준 → 구동 측도 **같은 저장맵 + AMCL**이어야 함([[live-map-pull-from-domain]]). 실측이 필요하면 [[urhynix-teleop-waypoint-capture]]로 대체/보정.

관련: [[urhynix-teleop-waypoint-capture]] · [[map-quality-eval]] · [[slam-nav2-arena-survey]]
