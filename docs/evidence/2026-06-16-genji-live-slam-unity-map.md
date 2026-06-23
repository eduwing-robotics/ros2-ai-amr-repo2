<!--
2026-06-16 evidence: 젠지 단독 경기장 SLAM + /map 라이브 스트리밍 → Unity ControlRoom MapPanel 1:1 렌더(경로 B) 검증.
환경 갱신(도메인210/192.168.10) + bringup + cartographer + MapSubscriber 신규 구현 + 목업 제거 + 맵 저장/평가까지.
-->

# [evidence] 젠지 라이브 SLAM → Unity 맵뷰 1:1 (경로 B)

- **일자**: 2026-06-16
- **기체**: 젠지 단독 (`kim@192.168.10.87`, TurtleBot3 burger, LDS-03). 티원은 팀원 사용으로 제외.
- **망**: codelab_robot_team_2_5G (192.168.10.x), `ROS_DOMAIN_ID=210`
- **목표**: 2×2m 가벽 경기장 SLAM + `/map`을 Unity ControlRoom MapPanel에 실시간 1:1 렌더
- **결과**: ✅ 라이브 스트리밍 작동(Unity `🟢 first /map frame 57×58 @0.05m` 수신) + 맵 저장(occupied 8.5%, unknown 0%, 발표 적합)

## 1. 환경 갱신 (구 56/192.168.0 → 210/192.168.10)

- `scripts/tb3.sh`: `ROS_DOMAIN_ID` 56→210 (7곳), fallback `192.168.0`→`192.168.10`
- `scripts/urhynix_robot_up.sh`: 도메인 56→210 (2곳)
- `.claude/skills/slam-nav2-arena-survey/SKILL.md`: 명령 도메인/망 갱신
- `~/.tb3rc`: 이미 192.168.10망으로 갱신돼 있었음. LDS-03은 헬퍼·로봇 일치(수정 불필요)
- 로봇 탐지: `tb3-ip` → `192.168.10.87` 자동(MAC 2c:cf:67:47:38:03 패턴)

## 2. bringup + SLAM (함정 2건 해결)

| 단계 | 결과 |
|---|---|
| `tb3-up` 1차 | ❌ `tmux: command not found` → 젠지에 tmux 미설치 |
| tmux 설치 | `sudo apt-get install -y tmux` (3.4) |
| `tb3-up` 2차 | ✅ bringup+ros_tcp 세션. `/scan` 10Hz, `/odom` 20Hz, `/tf` 정상 |
| `tb3-slam` 1차 | ❌ `cartographer.launch.py` FileNotFoundError |
| 원인 | `~/turtlebot3_ws`가 symlink-install인데 `src/turtlebot3_cartographer` 삭제됨 → install의 launch가 **깨진 심볼릭 링크** |
| 해결 | **apt판으로 실행**: ws 오버레이 source 없이 `/opt/ros/jazzy`만 source → `ros2 launch turtlebot3_cartographer cartographer.launch.py` |
| `/map` | ✅ `cartographer_occupancy_grid_node` 1.0Hz 발행 (RELIABLE + TRANSIENT_LOCAL) |

## 3. Unity 라이브 맵뷰 구현 (경로 B)

신규/수정 파일:
- **`Ros/TopicRegistry.cs`**: `Map = "/map"` 추가
- **`Ros/MapSubscriber.cs`** (신규): `OccupancyGridMsg` 구독 → `Texture2D`(RGBA32, Point filter) 변환. 셀값 -1 unknown(반투명회색)/0 free(흰)/≥65 occupied(검정). 맵 크기 변하면 텍스처 재생성. static 이벤트 `OnMapUpdated` + `LatestMap` 보관(늦은 View 즉시 반영). 카메라 구독과 동일 패턴.
- **`UI/MapPanelView.cs`**: `OnMapUpdated` 구독 → `Image`(ScaleToFit, 절대배치 fill) 레이어에 렌더. 첫 수신 시 "수신 대기…" 힌트 숨김.
- **`App/ControlRoomApp.cs`**: `CreateRosSubscribers()`로 `MapSubscriber` GameObject 코드 부착(씬 YAML 비편집).
- **`Resources/RobotConfig/default_robots.json`**: 젠지를 `robots[0]`으로(오늘 단독) → `ConfigureRos`가 endpoint를 `.87`로 지정.
- **`UI/Parts/MapPanel.uxml`**: 목업(격자/액자/웨이포인트/로봇점/구역라벨) **전부 제거**, 라이브 맵만. 진짜 마커는 Phase 4/5 pose 오버레이로 재도입.

검증 체인:
- 컴파일 `scriptCompilationFailed: false`
- `[ControlRoomApp] ROS IP set: 192.168.10.87:10000`
- endpoint `RegisterSubscriber(/map, nav_msgs/OccupancyGrid) OK`
- Unity `[MapSubscriber:SLAM 맵] 🟢 first /map frame 52×51 @ 0.05m`
- cartographer 1Hz → DDS → ros_tcp_endpoint → TCP → MapSubscriber → MapPanel Texture2D

## 4. 맵 산출/평가

- 저장: `tb3-slam-save genji_arena_v1` → `tb3-fetch-map` → `docs/evidence/maps/genji_arena_v1/{pgm,yaml,png}`
- 크기 57×58 = 2.85×2.90m, resolution 0.05, origin [-2.142, -0.892, 0]
- 품질(`map-quality-eval`): **Occupied 8.5% / Free 91.5% / Unknown 0.0%** → "회전+이동 OK, 외곽 다 닿음", 발표·Nav2 적합
- 시각: 벽이 닫힌 사각형 형태(루프 클로저 성공)

## 5. 함정/학습 (영구 자산화 대상)

| # | 증상 | 원인 | 해결 |
|---|---|---|---|
| 1 | `tb3-up` tmux not found | 젠지 tmux 미설치 | `apt-get install -y tmux` |
| 2 | cartographer launch FileNotFound | ws symlink-install인데 src 삭제 → 깨진 심볼릭 | `/opt/ros/jazzy`만 source해 apt판 실행 |
| 3 | Unity가 /map 못 받고 끊김 | codelab WiFi `Broken pipe`(핑 75~136ms 변동) | ROS-TCP 자동 재연결로 회복(링크 안정 시 수신). 안정 시연은 codelab_5G 근접 배치 필요 [[urhynix-wifi-codelab-status]] |
| 4 | Game View 스크린샷 검정 | Unity 백그라운드 시 렌더 정지 | 기능 무관. 시각 확인은 Unity 창 직접/포그라운드 |
| 5 | 첫 프레임 로그 안 보임 | `RaiseLogAdded`는 인앱 로그 패널 전용(Editor.log 미기록) | 검증용 `Debug.Log` 별도 추가 |
| 6 | 정지 중 `/map hz` 0 | daemon 재시작 워밍업 + 발행 뜸 | daemon stop/start 후 재측정 → 1.0Hz |

## 6. 다음

- 실제 웨이포인트/로봇 위치 마커를 pose(`/odom`,`/tf`) 기반 오버레이로 재도입 (Phase 4/5)
- 맵 origin↔Unity 좌표 정합(현재는 ScaleToFit 시각 정렬만)
- 안정 시연 위해 codelab_5G 공유기를 로봇 근처로 이동
