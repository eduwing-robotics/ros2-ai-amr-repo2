# Museum Patrol Robot — Master Specification

> **최우선 가이드라인**
> 노드 설계, 리팩토링, launch 작성, 토픽/파라미터 변경 시 **이 문서를 반드시 먼저 참고**하세요.

---

## 1. 로봇 하드웨어 스펙

### 1호기 T1 — 순찰 로봇

| 항목 | 스펙 |
|------|------|
| 역할 | 박물관 순찰·감시 |
| 메인 카메라 | Intel RealSense D435 |
| 카메라 토픽 | `/tb3_1/camera/color/image_raw` (compressed: `.../compressed`) |
| 아두이노 | **없음** (`arduino_bridge` 노드 실행 불필요) |
| Launch `robot_id` | `t1` (**기본값**) |

### 2호기 Gen.G — 방제·출동 로봇

| 항목 | 스펙 |
|------|------|
| 역할 | 이벤트 현장 출동·방제 대응 |
| 메인 카메라 | 파이카메라 (Pi Camera) |
| 카메라 토픽 | `/camera/image_raw` |
| 아두이노 | USB 시리얼 `/dev/ttyACM0` (115200 baud) |
| 센서 | PIR, 온도 센서, 레이저 모듈 |
| 액추에이터 | 소화 워터펌프 (릴레이 → Adafruit 3V 펌프) |
| Launch `robot_id` | `geng` |

#### Gen.G 시리얼 프로토콜

| 방향 | 포맷 |
|------|------|
| Arduino → ROS | `PIR:0,TEMP:24.5` / `PIR:1,TEMP:24.5` |
| ROS → Arduino | `PUMP:ON\|OFF`, `LASER:ON\|OFF` |

#### Gen.G ROS 2 토픽

| 토픽 | 타입 | 방향 |
|------|------|------|
| `/geng/sensor/pir` | `std_msgs/Bool` | Publish |
| `/geng/sensor/temperature` | `std_msgs/Float32` | Publish |
| `/geng/control/pump` | `std_msgs/Bool` | Subscribe |
| `/geng/control/laser` | `std_msgs/Bool` | Subscribe |

---

## 2. 위험 등급 정의 (Risk Level)

| 등급 | 색상 | 의미 | 대표 조치 |
|------|------|------|-----------|
| **SAFE** | 초록 | 이상 없음 | 순찰·대기 |
| **WATCH** | 노랑 | 이상 징후 최초 감지 | T1 재촬영 및 서버 분석 |
| **CHECK** | 주황 | 두 번째 확인 필요 | Gen.G 현장 출동 및 확인 |
| **DANGER** | 빨강 | 위험 가능성 높음 | 관리자 확인, 신고·차단벽 요청 |
| **EVACUATE** | 진한 빨강 | 즉시 대피 필요 | 위험구역 설정, 워터펌프 분사, 로봇 대기 |

> 노드 구현 시 `MuseumState` 또는 후속 메시지에 `risk_level` 필드 추가를 권장합니다.

---

## 3. 핵심 5대 마스터 시나리오

| # | 시나리오 | 트리거·흐름 | 주 담당 | 위험 등급 흐름 |
|---|---------|------------|---------|---------------|
| **#1** | 폐관 후 침입자 감지 | YOLO로 **사람 지속 감지** → Gen.G 출동 | T1 감지 → Gen.G 대응 | WATCH → CHECK → DANGER |
| **#2** | 중요 전시품 분실·이동 | T1 **기준 이미지 대비 불일치** → Gen.G 출동 | T1 비교 → Gen.G 확인 | WATCH → CHECK |
| **#3** | 화재 의심 즉시 대응 | T1 **불꽃/연기 감지** → 즉시 DANGER → Gen.G 출동 → 온도·레이저 확인 → **EVACUATE** → 펌프 가동 | T1 감지 → Gen.G 방제 | DANGER → EVACUATE |
| **#4** | 개장 중 전시품 접촉 | 보호 구역 진입 시 **1차 안내** → 지속 시 Gen.G 출동·**2차 경고** | T1 안내 → Gen.G 경고 | WATCH → CHECK |
| **#5** | 배터리 부족·임무 인계 | T1 배터리 부족 → Gen.G에 **Waypoint 인계** → T1 **ArUco 정밀 주차** | T1 → Gen.G | SAFE (운영) |

### 소프트웨어 시나리오 ID 매핑 (`task_manager` 연동용)

| 마스터 # | `scenario_id` (현재 코드) | 비고 |
|----------|---------------------------|------|
| #1 | `night_intruder` | `night_mode=true` + person 감지 |
| #2 | `exhibit_loss` | 기준 이미지 비교 로직 추후 구현 |
| #3 | `fire_response` | YOLO fire/smoke + Gen.G 온도·펌프 |
| #4 | `exhibit_contact` | 개장 중 person 감지 |
| #5 | `battery_handoff` | `/museum/battery/level` 연동 |

---

## 4. Launch 가이드

### 기본 실행 (1호기 T1 모드)

```bash
ros2 launch museum_patrol_system museum_patrol.launch.py
```

- `robot_id=t1` (기본)
- 카메라: `/tb3_1/camera/color/image_raw` (RealSense, namespace tb3_1)
- 팀 `arduino_bridge.py`: **실행 안 함**

### 2호기 Gen.G 모드

```bash
ros2 launch museum_patrol_system museum_patrol.launch.py robot_id:=geng
```

- 카메라: `/camera/image_raw` (파이카메라)
- 팀 `arduino_bridge.py`: **별도 실행** (`python3 scripts/arduino_bridge.py`)

### Launch 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `robot_id` | **`t1`** | `t1` (순찰) 또는 `geng` (방제) |
| `image_topic` | `auto` | `auto` → `robot_id` 프로필 카메라 토픽 |
| `launch_arduino` | `auto` | `auto` → T1: off, Gen.G: on |
| `serial_port` | `/dev/ttyACM0` | Gen.G 아두이노 포트 |
| `baud_rate` | `115200` | Gen.G 시리얼 보레이트 |
| `night_mode` | `false` | 시나리오 #1 야간 순찰 모드 |

#### `robot_id` 프로필 자동 설정

| 설정 | T1 (`t1`) | Gen.G (`geng`) |
|------|-----------|----------------|
| `image_topic` | `/tb3_1/camera/color/image_raw` | `/tb3_2/camera/image_raw` |
| `launch_arduino` | `false` | `true` |

#### 오버라이드 예시

```bash
# T1이지만 카메라 토픽만 변경
ros2 launch museum_patrol_system museum_patrol.launch.py image_topic:=/camera/color/image_raw

# Gen.G 프로필, 아두이노 없이 소프트웨어만 테스트
ros2 launch museum_patrol_system museum_patrol.launch.py robot_id:=geng launch_arduino:=false

# T1 + 야간 침입 시나리오 (#1)
ros2 launch museum_patrol_system museum_patrol.launch.py robot_id:=t1 night_mode:=true
```

---

## 5. 공통 소프트웨어 스택

| 노드 | 역할 |
|------|------|
| `yolo_detector` | 불꽃·연기·사람 비전 감지 (T1/Gen.G 공통) |
| `task_manager` | 5대 시나리오·위험 등급 중앙 제어 |
| `scripts/arduino_bridge.py` | Gen.G 전용 — 팀 스크립트 (PIR/LDR + Supabase) |
| Unity ControlRoom | 팀 `unity/` + ROS-TCP + `patrol_waypoints_bridge.py` |

| 토픽 | 설명 |
|------|------|
| `/museum/task/state` | `MuseumState` 통합 상태 |
| `/museum/task/command` | `MuseumCommand` 외부 명령 |
| `/detect/image_raw` | YOLO 결과 영상 |
| `/detect/status` | YOLO 상태 문자열 |

---

## 6. 개발 체크리스트

- [ ] 대상 로봇이 **T1**인지 **Gen.G**인지 확인했는가?
- [ ] 카메라 토픽이 해당 로봇 스펙과 일치하는가?
- [ ] T1 실행 시 팀 `arduino_bridge.py`가 **꺼져 있는가**?
- [ ] 시나리오 흐름이 위험 등급(SAFE→EVACUATE) 정의와 맞는가?
- [ ] Gen.G 출동·펌프 가동이 마스터 시나리오 #3 규격을 따르는가?
