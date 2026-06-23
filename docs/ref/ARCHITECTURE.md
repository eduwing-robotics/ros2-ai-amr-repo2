# Architecture

## 전체 구조

```text
                        +-----------------------------+
                        |        Unity Digital        |
                        |   Twin Control Dashboard    |
                        |  (관제 UI · 이벤트 마커 ·   |
                        |   카메라 패널 · 운영 KPI)   |
                        +--------------+--------------+
                                       |
                          ROS-TCP-Connector / Bridge
                                       |
   +---------------+        +----------+----------+        +---------------+
   |  Sensor HW    |        |   ROS2  Domain      |        |  Pi Camera    |
   |  (MCU/RPi/    +-------->  /security/event    <--------+  (이미지 토픽) |
   |   OpenCR 후보)|        |                       |        |               |
   |  PIR · 온도 · |        |  /security/dispatch |        |  /tb3_*/      |
   |  소리 · 레이저 |        |  /security/camera_  |        |   camera/     |
   |  + 워터펌프   |        |   confirm           |        |   image_raw   |
   +---------------+        +----+-----------+----+        +---------------+
   [정본 v18: LDR/불꽃 제거]
                                 |           |
                       +---------+           +---------+
                       |                               |
                +------+------+                 +------+------+
                |  tb3_1      |                 |  tb3_2      |
                |  (순찰/감지)|                 |  (출동/확인)|
                |  SLAM/Nav2  |                 |  Nav2 goal  |
                |  LiDAR/odom |                 |  카메라     |
                +------+------+                 +------+------+
                       |                               |
                       +---------------+---------------+
                                       |
                                +------+------+
                                | DB Writer   |
                                | (Supabase/  |
                                | local PG)   |
                                +------+------+
                                       |
                              events · dispatches ·
                              camera_captures · session_meta
                              (planned: pose_logs ·
                               media_artifacts · protected_assets)
```

## 하드웨어 적층 (TurtleBot3 Burger, 한 단 추가 없음)

```text
                  ┌──────────────────────────┐
   최상단 ───────▶│   🔵 LDS LiDAR (360°)    │  시야 양보 X
                  └──────────────────────────┘
                                ↑ LiDAR 받침대 약 30mm (그대로)
                  ┌──────────────────────────┐
   상판 ─────────▶│ 🟢 Raspberry Pi          │  한쪽 치우쳐 마운트
                  │ ───────────────────────  │
                  │ 🟡 Arduino Uno + 미니브  │  반대편 빈 공간 양면테이프 부착
                  │    레드보드 + 센서 4종    │  (점퍼선은 LiDAR 회전 평면 아래로 정리)
                  └──────────────────────────┘
                          │            │
                          │ USB 데이터 │ OpenCR 5V 점퍼 (5V + GND)
                          ▼            ▼
                  ┌──────────────────────────┐
                  │   ⚪ OpenCR              │  주행 펌웨어 그대로
                  └──────────────────────────┘
                  ┌──────────────────────────┐
                  │   ⚫ 배터리 / 모터        │  베이스
                  └──────────────────────────┘
```

**핵심 변경**:
- LiDAR 위 별도 층 추가 X — Burger 상판 빈 공간에 Arduino 배치
- 전원: OpenCR 5V 핀 → Arduino **5V 핀**(Vin 아님!) 직결
- 데이터: USB Type-B 케이블 그대로 RPi에 연결 (이중 전원이지만 P-MOSFET 자동 선택)
- 점퍼선이 LiDAR 회전 평면(받침대 윗면)보다 확실히 아래로 가도록 케이블 타이 정리

**핀 할당 (Arduino Uno R3):**

| 센서 | 출력 형태 | Arduino 핀 | 회로 비고 |
|---|---|---|---|
| PIR (HC-SR501) | 디지털 HIGH/LOW | **D2** | 모듈 자체 풀업, 신호 3.3V (Uno OK) |
| 온도 (온도 센서 모듈) | 아날로그 | **A0** | [제안 핀 매핑 — 정본 v18엔 핀 미명시, 구 LDR 슬롯 재사용 추정] |
| 소리 (KY-038) | 디지털 D-out | **D3** | A-out 대체 가능 시 A1 |
| 레이저 송신 | 디지털 D-out | **D4** | [제안 핀 매핑 — 정본 v18엔 핀 미명시, 구 Flame 슬롯 재사용 추정] |
| 릴레이 (워터 펌프 제어) | 디지털 | **D5** | [제안 핀 매핑 — 정본 v18엔 핀 미명시, 새 액추에이터] |

**브레드보드 권장 크기**: TurtleBot3 Burger는 하프사이즈(83×55mm), Waffle Pi는 풀사이즈(165×55mm) 가능.

## 듀얼 로봇 역할

### tb3_1 (별명 **티원**) — 순찰/감지 (Patrol) · **비전 중심**

- **탑재 카메라**: Intel RealSense D435 (RGB-D + IR, IMU 없음) — 3층 정면 부착
- **호스트**: `t1@192.168.0.250` (hostname `rb`) — 동료 작업 머신, 사용자명 `t1` = 티원
- 사전 정의된 waypoint를 SLAM 맵 위에서 순찰
- LiDAR/odom + D435 RGB-D로 위치/장애물 파악
- 박물관/미술관 구역의 액자형 사진 타깃을 `protected_asset`으로 보고, 순찰 중 D435 RGB + YOLO 인식 결과를 DB에 남김
- 이벤트 발생 시 `(robot_id="tb3_1", event_type, pose, severity, timestamp)`를 `/security/event` 발행
- D435 Depth는 가벽 매핑 보완(LDS-03 192mm 평면이 못 잡는 낮은 가벽 detect) + 액자 3D 위치 식별에 사용
- 발행 후에도 순찰 지속 또는 대기 상태로 전환

### tb3_2 (별명 **젠지**) — 출동/확인 (Responder) · **센서 중심**

- **탑재 카메라**: Raspberry Pi Camera Module v2 (Sony IMX219, 8MP, 3280×2464)
- **탑재 센서**: Arduino Nano/Uno + PIR/온도/소리/레이저+워터펌프 4종 [정본 v18 변경: LDR/불꽃 제거→온도/레이저/워터펌프 추가]. 핀 매핑: PIR=D2, 온도=A0, 소리=D3, 레이저=D4, 릴레이(워터펌프)=D5 [제안: 정본 v18엔 핀 미명시, 구 슬롯 재사용 추정]
- **호스트**: `urhynix-robot` (kim@192.168.0.82) — 우리 작업 머신
- 평상시 대기 위치 또는 별도 구역 순찰. Arduino 센서 4종 감시 — PIR/온도/소리/레이저 임계값 → `/security/event` 발행
- `/security/event` 구독 → `/security/dispatch` 발행 → Nav2 goal로 감지 좌표 근처 waypoint 이동
- 도착 후 Pi Camera 캡처/스트림을 `/security/camera_confirm`으로 발행
- 화재 대응 시나리오: 온도 상승 + 레이저 거리 감지 → `/security/confirm_fire` → **워터 펌프 분사** (릴레이 D5 제어)
- 출동 소요 시간, 확인 결과, 사진/영상/사운드 저장 경로를 DB에 기록

## 박물관/미술관 보호 컨셉

- 보호 대상은 액자형 사진 타깃 또는 중요물품이며 `protected_assets`에 `asset_id`, 이름, 전시 위치, 보조 마커(AprilTag/QR/프레임 색상)를 등록한다.
- 카메라 인식은 1차로 보조 마커/고대비 프레임을 사용하고, S3 이후 AI 라벨링으로 `asset_seen`/`asset_missing`/`unverified` 결과를 보강한다.
- 외부자는 단일 센서로 단정하지 않고 PIR 이벤트 + LiDAR 거리 변화 + pose/waypoint 맥락을 함께 DB에 남긴다.
- 화재 의심 이벤트는 실제 불꽃 대신 모의 입력으로 발생시키고, 액자/중요물품 주변 카메라 확인과 영상 클립 저장을 데모 핵심 장면으로 둔다.

## 모듈 경계

### M1. 백엔드 DB / ROS-TCP 라벨링 / AI (김주영, 김선일)

- DB Writer 노드 (`/security/*` 구독 → `events`, `dispatches`, `camera_captures` insert)
- pose logger (`/tb3_*/pose` 샘플링 → `pose_logs` insert, SCRUM-23 예정)
- media writer (사진/영상/사운드 파일 저장 후 `media_artifacts` path insert, SCRUM-23 예정)
- protected asset registry (`protected_assets`)와 카메라 인식 결과 라벨링 (SCRUM-21/23 예정)
- 데이터 라벨링 파이프라인 (이미지 + 메타데이터)
- AI 분류 보조 모델 (PIR 오탐 vs 실탐, 소리 노이즈 분류)
- 발표용 KPI 집계 쿼리

### M2. 아두이노 메인 보드·통신 (박태진, 임현찬, 김주영)

- MCU 펌웨어 (센서 → 시리얼/UART)
- ROS 측 시리얼 브릿지 노드 → `/security/event` 발행
- 보드별 ID 부여 및 robot_id 매핑

### M3. Unity 관제UI · ROS-TCP 통신 · 영상 스트리밍 (김선일, 박태진)

- Unity 씬: 박물관/미술관 실내 맵 + 액자형 중요물품 + 듀얼 로봇 모델 + 이벤트 마커 + 카메라 패널 + 운영 대시보드
- ROS-TCP-Connector를 통해 `/tb3_*/pose`, `/security/*` 구독
- Pi Camera 스트림 표시 (`RawImage`)
- 보호 대상 상태(`정상`, `확인 필요`, `미확인`)와 저장된 사진/영상/사운드 링크 표시

### M4. 아두이노 센서 (김주영, 임현찬, 박태진)

- PIR(사람), 조도(야간 모드), 소리(이상 소음), 불꽃(화재 의심·모의)
- 회로 + 임계값 보정 + 센서별 메시지 포맷
- **연결 방식 확정**: 별도 Arduino Uno R3 + 브레드보드 → Raspberry Pi USB serial. OpenCR/RPi GPIO 직접 연결 후보는 폐기.
- 시연 직전 광량/노이즈 환경에서 재캘리브레이션

### M5. 터틀봇 — LiDAR · 카메라 · SLAM · 네비게이션 (임현찬, 김선일)

- ROS2 노드: bringup, SLAM, Nav2, LiDAR, 카메라 드라이버
- waypoint follower (`tb3_1`)와 dispatch follower (`tb3_2`)
- Pi Camera 토픽 발행

## 중요한 원칙

- 실제 주행 안전 판단은 ROS/Nav2(터틀봇 노드) 기준. Unity는 시각화·관제 중심.
- 모든 메시지는 `robot_id`를 포함 — 한 토픽이 두 로봇 모두를 다룬다 (`/security/event` 등).
- ROS2 도메인 기준은 `ROS_DOMAIN_ID=210`으로 통일한다. 젠지/티원/ROS-TCP-Endpoint 내부 ROS 노드는 같은 도메인에서 토픽을 확인한다. (2026-06-15 210으로 통일, cross-discovery PASS)
- 카메라 인식은 보호 대상 확인과 출동 확인을 위한 보조 데이터. 실시간 사람 추적은 범위 밖.
- Google Teachable Machine + TensorFlow/Keras 스파이크 클래스(빈공간/박스/마우스 검정·흰색/손)는 카메라 객체 분류 경로 검증용이다. 발표용 큰 범위 인식 기준은 YOLO/OpenCV의 로봇/사람/중요품/불 흐름을 유지한다.
- 외부자 판단은 PIR 단독 판정 금지. PIR + LiDAR 변화 + pose log를 함께 남겨 사람이 해석할 수 있게 한다.
- 조도 센서가 어두움으로 진입하면 LiDAR 자체를 새로 켜는 것이 아니라, 저속 순찰/스캔 로그 저장/이벤트 확인 빈도를 높이는 방식으로 "LiDAR 강화 모드"를 구현한다.
- 화재 이벤트는 모의 입력. 실제 불꽃 테스트는 안전상 금지.
- 센서 연결은 **Arduino Uno R3 → Raspberry Pi USB serial 경로로 확정**. OpenCR 펌웨어 영향 0, 분리된 시스템이라 디버깅이 쉬움.
- **별도 층 추가 없음**. Arduino + 미니 브레드보드는 Burger 상판 빈 공간(라즈베리파이 반대편)에 **양면테이프로 부착**. LiDAR 받침대는 기존 그대로 유지하며 점퍼선은 LiDAR 회전 평면 아래로 정리한다.
- Confluence 1540099(브레인스토밍) → Confluence 1605636(역할 분배 보드) → 본 ARCHITECTURE.md가 정합 체인.

## 외부 시스템

| 시스템 | 역할 |
|---|---|
| Supabase 또는 로컬 Postgres | 현재: events / dispatches / camera_captures / session_meta 저장. 예정: pose_logs / media_artifacts / protected_assets |
| Supabase Storage 또는 로컬 media 폴더 | 예정: 사진 / 짧은 영상 / 사운드 원본 저장, DB에는 path와 메타데이터 저장 |
| ROS-TCP-Endpoint (Unity 측) | Unity ↔ ROS2 양방향 통신 (TCP 10000, NAT 통과 OK) |
| Arduino IDE / serial | Uno R3 펌웨어 빌드 + `pyserial`로 RPi에서 수신 |
| Pi Camera Module v2 (Sony IMX219, 8MP, 3280×2464) | **tb3_2 (젠지) 위** 일반 RGB 카메라 노드. 호스트 `urhynix-robot`(kim@192.168.0.82). Ubuntu 24.04에서는 libcamera Pi fork + rpicam-apps 소스 빌드 필수 (DECISION-LOG 2026-06-01 참조) |
| Intel RealSense D435 (USB 3.2, Depth+RGB+IR, IMU 없음) | **tb3_1 (티원) 위** 3D 깊이 카메라. 호스트 `t1@192.168.0.250`(hostname `rb`). RGB-D SLAM(RTAB-Map) + 가벽 detection + 액자 3D 위치 식별 + YOLO 4 클래스 인식 |

## SLAM/Nav2 처리 위치 (2026-05-29 확정)

| 컴포넌트 | 위치 | 이유 |
|---|---|---|
| **cartographer (SLAM)** | **Robot 라즈베리파이** | macOS Docker host networking이 inbound NAT 미라우팅으로 DDS 분산 통신 부적합 (tcpdump 검증). Multipass/UTM의 QEMU bridged도 hang. Linux native 호스트(동료 Ubuntu)가 fallback. |
| **nav2 (path planning)** | **Robot 라즈베리파이** | cartographer와 같은 머신에서 `/map` localhost 통신. |
| **nav2_map_server (map_saver_cli)** | **Robot 라즈베리파이** | 1회성 저장, robot의 `~/maps/<name>.{pgm,yaml}`에 산출 |
| **맵 결과 시각화** | **Mac (Unity Editor)** | `.pgm → .png` PIL 변환 + Plane scale 자동 계산. ROS-TCP-Connector는 별개로 5채널 LIVE 대시보드. |
| 워크스페이스 빌드 | Robot 라즈베리파이 | `colcon build --symlink-install --parallel-workers 1 --executor sequential` (RPi 4 메모리 4GB + SD swap thrash 회피) |

→ 자세히: `docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md` §6.5 (macOS Docker 한계 진단), `.claude/skills/slam-nav2-arena-survey/SKILL.md` (결정 트리)
