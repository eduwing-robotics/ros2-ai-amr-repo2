---
name: live-map-pull-from-domain
description: 팀원에게 파일을 안 받고, 운영 중인 ROS2 도메인에서 현재 /map을 읽기 전용으로 직접 떠오는 표준. map info(해상도/크기/origin) 즉시 확인 + map_saver로 .pgm/.yaml 저장 + 프레임 안정성 판정(Cartographer 라이브=drift 위험 vs 정적맵+AMCL=고정). 웨이포인트/디지털트윈 좌표의 기준맵을 확보할 때. URHYNIX 도메인 210. 2026-06-23 도출.
user_invocable: true
tags: [ros2, map, nav2, cartographer, amcl, urhynix]
version: 1
---

# Live Map Pull from Domain

다른 PC가 운영 중인 ROS2 도메인에서 **현재 맵을 우리가 직접(읽기 전용) 떠온다.** 파일 주고받기보다 빠르고, 구동 측이 *지금* 쓰는 프레임과 100% 일치한다. 비침습 원리는 [[ros2-noninvasive-pose-tap]].

## Use When

- 웨이포인트 좌표의 기준맵이 필요한데 로컬 맵이 레거시일 때
- 팀원 맵과 내 좌표 프레임이 맞는지 확인할 때
- 디지털트윈 맵뷰([[unity-live-map-twin]])의 정합 기준이 필요할 때

## 1) 맵 info 즉시 확인 (저장 없이)

```bash
ssh -o ControlMaster=no t1@<IP> 'source /opt/ros/jazzy/setup.bash; \
 export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
 timeout 8 ros2 topic echo /map --field info --once'
```
→ `resolution / width / height / origin`. 좌표 범위 = x∈[ox, ox+w·res], y∈[oy, oy+h·res].

## 2) 맵 저장 (.pgm/.yaml)

```bash
ssh -o ControlMaster=no t1@<IP> 'source /opt/ros/jazzy/setup.bash; \
 export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; \
 cd ~/maps && ros2 run nav2_map_server map_saver_cli -f live_$(date +%s) --ros-args -p save_map_timeout:=20.0'
# 이후 scp로 Mac으로 가져옴
```
map_saver는 /map을 구독만 하므로 비침습.

## 3) ⚠️ 프레임 안정성 판정 (가장 중요)

좌표가 깨지지 않으려면 **map 프레임이 고정**돼야 한다.

| 상태 | /map publisher | 좌표 유효성 | 권고 |
|---|---|---|---|
| 라이브 SLAM | `cartographer_node`/`occupancy_grid_node` | loop closure마다 origin 미세 이동 → **좌표 어긋남 위험** | 매핑 끝내고 맵 저장 후 정적 모드로 |
| 정적맵+위치추정 | `map_server` + `/amcl` | 프레임 고정 → **좌표 영구 유효** | 이 상태에서 좌표 확정·구동 |

판정: `ros2 node list`에 `cartographer_node`가 살아있으면 라이브 SLAM(주의), `map_server`+`amcl`만이면 정적(안전).

## 함정표

| 함정 | 회피 |
|---|---|
| 빈 도메인/RMW | [[ros2-noninvasive-pose-tap]] 함정표와 동일(도메인·RMW·SUBNET 명시) |
| 레거시 맵 혼동 | origin 비교로 현재맵 확인(예 arena_depth origin -3.544 ≠ 현재 -2.161) |
| 저장 타임아웃 | `save_map_timeout` 늘리고 /map 발행 중인지 먼저 확인 |

## 검증

- 떠온 origin/size가 라이브 `/map --field info`와 일치.
- 로봇 실측 pose([[ros2-noninvasive-pose-tap]])가 맵 좌표 범위 안에 들어오면 프레임 정합 OK.

관련: [[ros2-noninvasive-pose-tap]] · [[urhynix-teleop-waypoint-capture]] · [[map-pgm-waypoint-autogen]] · [[unity-live-map-twin]] · [[map-quality-eval]]
