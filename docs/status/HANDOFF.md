# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-06-24 — **🗺️ 티원 신규 SLAM 맵 `arena_v3` 저장·검증 PASS + Unity 슬롯 등록**. 티원 텔레옵+slam_toolbox 재매핑 → arena_v3(41×42px, res0.05, origin(-0.42,-1.82)) 저장. 품질 PASS(벽25%/자유75%/미지0%, 닫힌 방, 드리프트 없음) — 단 크기 ~2m×2.1m로 경기장 전체 여부 미확정. Mac `docs/evidence/maps/arena_v3/` 복사 + `StreamingAssets/Maps/arena_v3` 슬롯 생성(MapCatalog 자동인식, 기본맵은 아직 "arena"). **다음 액션**: arena_v3 맵에서 ① 로봇 위치 마커(/tf) 표시 ② 좌표설정 goal_pose로 로봇 실이동 — **둘 다 코드 기존(RobotPoseSubscriber/MapMarkerLayer/DispatchPublisher)이라 신규구현 아닌 검증**. 선행조건: 티원 `slam_toolbox` 종료 → Nav2(AMCL+arena_v3 정적맵) 전환(`urhynix-nav2-waypoint-patrol`). 이게 2026-06-23 잔여 블로커(좌표↔맵·heading)를 새 맵으로 해소하는 검증. **로봇 연결**: 젠지 `kim@192.168.10.84`·티원 `t1@192.168.10.250`(무선, alias/mDNS 죽어 직접 IP). **세션종료 시 로봇 셧다운 진행함**. **이전(2026-06-23)**: 젠지 Nav2 순찰 SW PASS, 잔여 좌표↔맵·heading(arena_v3로 해소 시도). **이전(2026-06-23)**: Unity MWE 5 Phase 구현 완료(컴파일 PASS). **이전(2026-06-23)**: git 원격 이관 완료(새 repo). **ROS IP SSOT**: `default_robots.json[0].hostAddress`. **검증**: urhynix-nav2-waypoint-patrol 함정표 + tf2_echo map base_footprint로 heading 확인.

---

## ⚡ Top 1 Action (가장 최신)

**MWE 맵 웨이포인트 에디터 + 로봇 라이브 실주행 검증**

- **배경**: 2026-06-23 Unity ControlRoom에서 맵 클릭 웨이포인트 에디터 5 Phase 전부 구현 완료(컴파일 PASS). 잔여는 실제 로봇+Nav2로 주행 검증.
- **다음 액션**:
  1. 로봇+Nav2 켜고 AMCL로 같은 arena 맵 로드
  2. `scripts/patrol_waypoints_bridge.py --robot tb3_1` (또는 tb3_2) 실행 → 로봇측 subscr 활성
  3. Unity ControlRoom Play → 맵 표시 + 웨이포인트 3~5개 클릭
  4. "▶순찰시작" 버튼 → ros2 action list에서 follow_waypoints 액션 발행 확인
  5. 로봇 주행 (1~2바퀴) → 성공/실패 evidence 기록
- **병렬 작업**:
  - Supabase `patrol_routes.sql` 적용 (로컬 저장+동기화 DB 단계)
  - Unity Play 시각 확인 (맵 north-up 방향 이상 시 MapImageLayer v 반전)
- **선행 조건**: 도메인 210 + AMCL 정상 + ROS-TCP-Endpoint 활성

---

## 📋 First 5 Min Checklist

```bash
# 1. 로봇 진입 (직결/무선 중 선택)
ssh urhynix-robot                    # mDNS (권장)
# 또는
ssh kim@192.168.10.50               # 직결(en5) 사용 시 — 젠지 eth0, bootpd DHCP
# 또는  
ssh kim@192.168.10.87 / t1@192.168.10.250  # 무선 (DHCP drift 정상)

# 2. 센서/하드웨어 5단계 점검 (~5분)
cat /sys/class/power_supply/*/uevent | grep VOLTAGE  # 배터리 11.5V 이상?
ros2 launch turtlebot3_bringup robot.launch.py      # Burger connected, DynamixelSDK error 없나?
ros2 run aruco_parking parking_node                 # 마커 주차 5회 시연

# 3. 양 로봇 토픽 확인 (도메인 210)
ros2 topic list | grep -E "tb3_1|tb3_2|camera|sensor"  # 카메라·센서 토픽 보이나?

# 4. Unity 실행
python3 ~/URHYNIX/unity-smoke/run.sh  # 또는 Unity Hub에서 ControlRoom 실행
```

→ **통과 기준**: bringup OK + 토픽 2개 이상 + Unity 화면 LIVE

---

## 🔧 If Stuck (빠른 복구)

| 증상 | 명령 |
|------|------|
| IP 못 찾음 | `bash .claude/skills/robot-ip-detect-fallback/resync.sh` |
| mDNS `.local` 안 잡힘 | 무선 확인: `ifconfig wlan0` → 192.168.0.x 또는 10.x 범위인가? |
| 무선 끊김 | 임시: `ifconfig en5 down` (직결 비활성) + 무선만 사용 |
| 카메라 토픽 0건 | 젠지 Pi Camera / 티원 RealSense `launch` 명령 재실행 + 15초 대기 |
| Arduino `/dev/tb3_arduino` stale | `ln -sf /dev/ttyACM0 /dev/tb3_arduino` |

---

## 📚 More Info (상세 내용)

| 문서 | 용도 |
|------|------|
| **`HANDOFF-FULL.md`** | 이전 모든 세션 기록(506줄), 하드웨어·센서 설치 상세 |
| **`DECISION-CURRENT.md`** | 최신 결정 5건 — 센서 교체·도메인 통일·무선 통일 |
| **`DECISION-LOG.md`** | 전체 결정 이력 + 근거 |
| **`PROJECT-STATUS.md`** | 한 줄 상태 + 역할 매트릭스 |
| **`../ref/TECH-INDEX.md`** | 작업별 빠른 문서 라우팅 |
| **ROS2-ROBOT.md** | 직결/무선 접속, 센서 핀 매핑 |
| **evidence/** | 센서 교체 / 무선 통일 / YOLO 검증 기록 |

---

## ✅ 한줄정리

**도메인 210 통일 + 젠지 센서 교체(LDR→온도·레이저) + 무선망 안정화 완료. 다음 세션: 양 로봇 부팅 + 시나리오 5종 시연.**
