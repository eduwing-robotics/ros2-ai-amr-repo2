# 2026-06-23 젠지 Nav2 순찰 실측 테스트

실측 날짜: 2026-06-23 | 목적: Nav2 웨이포인트 순찰 소프트웨어 스택 실주행 검증

## 목적

텔레옵으로 캡처한 웨이포인트(waypoints_tb3_1_final.yaml)를 젠지(tb3_2)에서 Nav2 액션 기반 실주행 + Unity ControlRoom 디지털트윈 관찰 동시 진행.

## 셋업

**로봇 환경**: 젠지 .84(또는 .82), 도메인210, RMW fastrtps, SUBNET 통일

**구동 명령**:
```bash
# 1. 젠지 bringup (turtlebot3_bringup)
ros2 launch turtlebot3_bringup robot.launch.py

# 2. Nav2 navigation2 (save된 맵 로드)
ros2 launch turtlebot3_navigation2 navigation2.launch.py map:=/home/kim/maps/map.yaml

# 3. 순찰 스크립트 시작
python3 run_waypoints.py --dynamic-start
```

**ROS 통신**:
- ros_tcp_endpoint 1개 가동 위치: .84 또는 .82
- Unity ControlRoom 타깃: Resources/RosConfig/ros_endpoint.json의 endpointIp

## ✅ PASS — 소프트웨어 전 과정

- Nav2 풀스택 active 상태 확인: amcl/planner/controller/BehaviorTree 모두 정상
- localize 성공: 기존 AMCL 추정 그대로 사용 (--dynamic-start)
- FollowWaypoints 액션 수락 및 진행 확인
- Unity ControlRoom 로봇 마커 실시간 표시 (map 화면 내 ▲마커)
- 맵 좌표계 회전 270° 적용 후 화면상 north-up 정렬
- 모터 정상 작동 (제자리 회전 확인)

## 🔴 잔여 블로커 2건

### 1) 플래너 경로 실패 (planner_server GridBased plugin)

**증상**:
```
planner_server: GridBased plugin failed to plan...
"Failed to create plan with tolerance 0.5"
```

**원인**:
- 캡처 당시 라이브맵(cartographer)과 저장 map.pgm(57×58, origin -0.734,-2.161) 불일치
- 저장된 map.pgm의 자유공간(free)과 웨이포인트 좌표가 점유(occupied) 또는 미탐색(unknown) 셀에 걸침
- 캡처 이후 로봇이 움직여 실제 위치와 맵 레지스트레이션이 어긋남

### 2) 방향(heading/yaw) 오류

**증상**:
- 로봇이 실제 방향과 반대로 이동 시도
- --dynamic-start로 기존 AMCL 추정값을 그대로 쓸 때 heading이 180° 틀어짐

**주의**:
- Unity 맵 270° 회전은 **화면 표시 전용**이며 로봇 주행 각도와 무관
- 혼동하지 말 것: 웨이포인트 좌표 자체는 world frame이며, heading 오류는 별도 원인

## 도출 함정 및 해결 기록

**함정 목록** (스킬 `.claude/skills/urhynix-nav2-waypoint-patrol`에 정리):

1. **Nav2 localize 전 띄우면 costmap 타임아웃** → 초기위치 연속발행으로 회피
2. **nav2_simple_commander amcl_pose 무한대기** → initial_pose_received=True 우회
3. **ROS_AUTOMATIC_DISCOVERY_RANGE 통일** → SUBNET 필수
4. **pkill -f 자기-kill 방지** → [r]un 괄호 트릭 + kill/launch 분리
5. **python3 버퍼링 지연** → python3 -u 플래그
6. **수동 lifecycle activate 금지** → finalized 상태에서는 재활성 불가

## 자산 목록

- **.claude/skills/urhynix-nav2-waypoint-patrol/SKILL.md** — 전체 구동·함정 가이드
- **scripts/patrol_waypoints_bridge.py** — geometry_msgs/PoseArray → Nav2 FollowWaypoints 액션 브리지
- **scripts/pgm_to_map_slot.py** — PGM 저장맵을 Unity StreamingAssets 슬롯으로 변환
- **run_waypoints.py** (--dynamic-start 추가) — 웨이포인트 순차 실행
- **Unity 맵 슬롯 시스템** — StreamingAssets/Maps/(mapId).png + (mapId).json

## 젠지 현재 상태

**잔존 파일 및 프로세스**:
- ~/maps/map.pgm + map.yaml (저장맵)
- ~/waypoints_tb3_1_final.yaml (캡처된 웨이포인트)
- ~/run_waypoints.py (순찰 스크립트)
- Nav2 구동 중일 수 있음 (다음 세션 시 cleanup 필요)

## 다음 권장 액션

### 권장: 새 SLAM 매핑 → 웨이포인트 재캡처 → 순찰 실행

1. **현재 공간 새 SLAM 매핑**: cartographer로 신규 맵 생성 (기존 map.pgm 대체)
2. **웨이포인트 재캡처**: 스킬 `urhynix-teleop-waypoint-capture`로 새 맵 기준 다시 캡처
3. **순찰 실행**: 같은 맵 + localize에서 웨이포인트 좌표 일치 → planner 경로실패 + 방향오류 동시 해결

### 대안: 빠른 재시도 (한계 있음)

1. RViz 2D Pose Estimate로 실제 위치 + 실제 방향(heading) 정확히 입력
2. 재-localize 후 run_waypoints.py --dynamic-start 재실행
3. **단, 웨이포인트 좌표가 자유공간에 들어야 플래너 경로 성공 가능**

## 검증 방법

**함정표 확인**:
- urhynix-nav2-waypoint-patrol 스킬 README 참조

**localize 상태 확인**:
```bash
ros2 run tf2_ros tf2_echo map base_footprint
```
실제 로봇 위치·방향과 tf 출력값 비교로 heading 오차 판단.
