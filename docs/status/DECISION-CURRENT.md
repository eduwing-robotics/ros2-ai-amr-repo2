# Decision Current — 최신 결정 5건

> **진입용 최신 5건만 모음. 전체 역사는 DECISION-LOG.md 참조.**
> 
> 본 문서는 DECISION-LOG.md의 복사본으로 유지됨. 매 세션 종료 시 업데이트.

---

## 2026-06-16 — Gen.G 센서 스택 교체 + 자동 충전독 제외 확정 + 시나리오 5종 확정

### 변경 1 — Gen.G(젠지/tb3_2) 센서 스택 교체

- **제거**: LDR(조도 센서), 불꽃(flame) 센서
- **추가**: 온도 센서 모듈, 레이저 송신 모듈, 워터 펌프(릴레이 모듈 + Adafruit 3V 수중 펌프, 화재 대응 모의 분사용 액추에이터)
- **유지**: PIR(인체감지), 소형 사운드 모듈, Pi Camera v2 (IMX219), Arduino Nano/Uno USB 시리얼 센서 보드
- **Gen.G ROS2 연결**: RaspberryPi4 →(USB Serial)→ Arduino Nano/Uno → [PIR · 사운드 · 온도 · 레이저] + 릴레이 → 워터 펌프
- **T1(티원/tb3_1) 유지**: RealSense D435, LDS-03 LiDAR, RaspberryPi4, TurtleBot3 Burger (변경 없음)

### 변경 2 — 자동 충전독 완전 제외 확정

- 완전 자동 충전독(포고핀·무선충전 하드웨어 회로)은 검토 결과 난이도 높아 현 단계 제외 확정
- **대체**: 배터리 잔량 모니터링 + **ArUco 마커 기반 정밀 주차** 후 **수동 충전 연결 요청**(Unity 화면에 요청 표시)
- 정밀 주차 실패 시 "긴급 수동 충전 요청" 표시

### 변경 3 — 발표용 시나리오 5종 확정

**위험등급 5단계: SAFE / WATCH / CHECK / DANGER / EVACUATE**

1. **폐관 후 침입자 감지** — PIR+LiDAR → WATCH → Gen.G 출동 → PIR·카메라 재확인 → DANGER 시 112 신고·차단벽 요청
2. **중요 전시품 분실·이동** — T1 YOLO 기준이미지·Depth 불일치 → WATCH → 재촬영(최대 2회) → CHECK → Gen.G 다각도 확인 → DANGER
3. **화재 의심 즉시 대응** — T1 YOLO 화재 감지 → 즉시 DANGER → Gen.G 출동 → **온도·레이저 센서값 + Pi Camera 재확인** → EVACUATE 시 **워터 펌프 분사** + 119 신고·차단벽 요청
4. **개장 중 전시품 접촉** — T1 YOLO 손 감지 → WATCH → 음성 안내 → CHECK → Gen.G 출동·2차 경고 → DANGER 시 관리자 확인 요청
5. **배터리 부족·임무 인계** — T1 배터리 기준 이하 → Gen.G에 남은 waypoint 인계 → T1 충전소 이동 → **ArUco 정밀 주차 → 수동 충전 연결 요청**(자동 충전독 미구현)

**주의**:
- 신고·차단벽 폐쇄는 실제 자동제어가 아니라 Unity 화면에 "요청 상태"로 표시
- YOLO 인식 MVP 클래스 4종: 로봇·사람·중요품·불

### 근거 및 출처

- Confluence SCRUM 스페이스, 2026-06-16 갱신 정본
  - 기획안(UR HYNIX) v18 /pages/327681
  - 하드웨어 아키텍처 v4 /pages/7536649
  - 소프트웨어 아키텍처 v4 /pages/13729806
  - 디지털 트윈 동작 검증 시나리오 /pages/13860874

### 현재 코드/스킬 드리프트 주의

- **코드 상태**: `unity/` + `scripts/`의 현재 코드는 이전 LDR(조도) 기반으로 작성됨 (LuxSubscriber, arduino_bridge 등)
- **스킬 상태**: `.claude/skills/urhynix-sensor-bringup/` 등은 구 LDR 기준 문서화
- **정합 필요**: 후속 세션에서 센서 하드웨어 교체 후 코드/스킬 토픽명·핀 매핑 갱신 필요

### 변경 4 — 레이저 센서 결선 + PIR 연동 (조도 제거) — Arduino as-built

- **확정 사실 (2026-06-16 검증 PASS)**:
  - **대상**: Mac USB 연결 Arduino UNO (FQBN `arduino:avr:uno`, 포트 `/dev/cu.usbmodem11101`). 향후 Gen.G(tb3_2) 탑재 예정.
  - **변경**: 조도(LDR/A0) **물리 제거**. PIR(D2 OUT) + LED(D2, +220Ω→GND) 유지.
  - **신규**: 레이저 송신 모듈 추가, 데이터핀 **D8**, 5V=브레드보드 레일, GND=공통 그라운드.
  - **동작**: PIR 감지(HIGH) → LED(D2) + 레이저(D8) **동시 ON**, 해제 → 동시 OFF.
  - **새 스케치**: `sketches/pir_laser/pir_laser.ino` (기존 `sketches/pir_led/pir_led.ino`는 참조용 보존).
  - **컴파일**: 7% flash / 9% RAM. arduino-cli 업로드 무에러.
  - **시리얼 검증 PASS**: 9600 배너 `=== PIR + LASER Test ===` → `Ready.` 수신 확인. 로그 포맷: `[MOTION] detected -> LED+LASER ON` / `[CLEAR ] no motion -> LED+LASER OFF`.
- **함정 & 해결**:
  - 레이저를 처음 **D13에 연결**했더니 업로드 `not in sync: resp=0x00 / programmer is not responding` 반복 실패.
  - **원인**: D13은 **SCK 라인** (부트로더 동기화), 액추에이터 부하가 동기화 방해.
  - **해결**: 데이터핀 **D13→D8로 이동** (또는 업로드 중에만 D13 분리). 자동리셋 안 되면 USB 재꽂기/RESET 버튼.
- **산출물**: `.claude/skills/arduino-flash/SKILL.md` v2→v3 갱신 (레이저 D8 + D13/SCK 함정 추가), `docs/ref/CONTRACT.md` §4.1 핀 표 갱신.

---

## 2026-06-15 (후반) — codelab_robot_team_2_5G 무선 통일 + 양 로봇 카메라/센서 cross-host PASS + 망 불안정 경고

### 결정
- **무선 네트워크 최종 통일 SSID: `codelab_robot_team_2_5G`** (5200MHz). 이전 시도: `codelab_5G` → 로봇 범위 밖(신호 0), fallback. 최종 선택: 로봇 기존 연결 SSID로 Mac도 통일. IP: Mac `192.168.10.101`, 젠지 `192.168.10.87`, 티원 `192.168.10.250` (전부 DHCP drift, 다음 세션 mDNS 재확인 필수).
- **`codelab_robot_team_2_5G`는 multicast 정상** — talker/listener 양방향 검증 PASS. 이전 팀 와이파이와 달라(multicast 차단), STATIC_PEERS 우회법 불필요. robot-camera-bringup §F의 우회법은 multicast 차단 망 대비용으로 보존.

### 검증 (PASS)
- **cross-host DDS multicast**: 젠지 talker → 티원 listener "Hello World" 수신 확인 PASS.
- **양 카메라 + 센서 cross-host 결선**:
  - 티원 RealSense D435 `/tb3_1/camera/color/image_raw/compressed` (30Hz, 로컬)
  - 젠지 Pi Camera v2 `/tb3_2/camera/image_raw/compressed` (30Hz, cross-host multicast)
  - 젠지 센서 `/sensors/ldr` (Int32), `/sensors/pir` (Bool) — arduino_bridge.py cross-host 수신 확인
  - 단일 endpoint(티원 port 10000)이 양 로봇 토픽 모두 수집 → Unity forward 완료. RegisterSubscriber 전부 OK.

### 신규 함정 5건 (이번 세션)
1. **젠지 `~/.bashrc` ROS_STATIC_PEERS 잔재** — `export ROS_STATIC_PEERS=192.168.10.70` → cross-host 토픽 불안정. `sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc`로 제거.
2. **`/dev/tb3_arduino` symlink stale** — Arduino realloc `/dev/ttyACM0` → old `/dev/ttyACM1` 여전히. `ln -sf /dev/ttyACM0 /dev/tb3_arduino` 재링크.
3. **RealSense compressed는 lazy republish** — 구독자 없으면 발행 안 함. ros_tcp_endpoint 먼저, Unity 구독, realsense 재시작 순서 필요.
4. **직결(en5) + 무선(en0) 같은 대역 충돌** — asymmetric routing 재발. `ifconfig en5 down` (직결 제거) → 무선 단일화.
5. **Unity 에디터 background throttle** — `unityctl play` 후 포커스 떨어짐 → 로그 정지. "Run In Background" 켜기 또는 Editor 항상 포그라운드 유지.

### 미해결 / 다음 세션 높음 우선
- **`codelab_robot_team_2_5G` 간헐 끊김 심각**: 10회 ping 중 2~3회 100% loss, 회복 1초 내, 빈번 반복 → **시연 신뢰성 낮음**. 임시 우회: 공유기를 로봇 근처로 옮겨 `codelab_5G` 사용 가능한지 확인, 또는 직결(Mac ↔ 젠지 eth0) 복귀 + mDNS 충돌 회피.
- **세션 종료 상태**: 젠지 안전 종료(poweroff) 완료, ping 100% loss 확인. 티원은 망 끊김으로 ssh 셧다운 실패 → **물리 전원 OFF 필요**.
- **다음 진입 5단계**: ① DHCP IP 재확인 ② `/dev/ttyACM*` 재확인 + symlink 갱신 ③ ROS_DOMAIN_ID=210 확인 ④ bringup 실행 ⑤ ros_tcp_endpoint + arduino_bridge.py + Unity 구독 시작.
- **evidence**: `docs/evidence/2026-06-15-wireless-codelab-team-crosshost-camera-sensor.md`

---

## 2026-06-15 — 무선 통일 + ROS_DOMAIN_ID 210 통일 + Unity 듀얼 로봇 전환 검증

### 결정
- **ROS_DOMAIN_ID 230 → 210 전면 통일.** 젠지(kim-desktop)는 팀원이 이미 210으로 변경한 상태였고, 티원(rb)도 `~/.bashrc` 230→210으로 맞춤. namespace 분리(`/tb3_1`=티원, `/tb3_2`=젠지)는 유지 → "도메인 통일 + namespace 분리"가 정본. SSOT 6개 문서 갱신 완료(ARCHITECTURE/CONTRACT/ROS2-ROBOT/VISION-CAMERA/PROJECT-PLAN + unity Ros/CLAUDE.md).
- **개발 접속을 무선으로 통일** — 직결(Mac en5 ↔ 젠지 eth0)을 제거하고 팀 와이파이(`192.168.10.x`)로 양 로봇 접근.

### 네트워크 (무선 통일 트러블슈팅)
- 팀 와이파이는 **AP isolation 아님** (Mac↔티원 SSH 통과). 이전 세션의 격리망과 다른 망.
- 젠지 무선이 안 닿던 원인 = **asymmetric routing**: 젠지가 eth0(직결)+wlan0 동시 보유 + default route가 eth0로 잡혀, wlan0(.87)로 온 요청의 응답을 직결로 내보냄 → Mac엔 안 옴. **직결 랜선 물리 제거**로 eth0 down → `default via 192.168.10.1 dev wlan0`로 정상화.
- 현재: 젠지=`192.168.10.87`(wlan0), 티원=`192.168.10.250`(wlan0). 둘 다 무선 + 210. (IP는 DHCP drift — [[project_robot_ip_dynamic]])

### 검증 (PASS)
- **cross-discovery PASS**: 양 로봇이 같은 210 도메인에서 `/chatter` 상호 발견 확인 (티원 talker → 젠지·티원 양쪽 topic list에 `/chatter`).
- **Unity 듀얼 로봇 전환 (코드+Scene)**: 카메라·배터리는 두 로봇 Subscriber 배치 + 탭(`tab-tb3_1`/`tab-tb3_2`)→`OnRobotChanged`→즉시 전환 완비(모델 B: 동시 구독 + robotId 필터). cross-host 가시성은 단일 ros_tcp_endpoint(티원)가 210에서 양 로봇 토픽 forward하는 구조에 의존 → 도메인 통일이 전제.

### 역할 분담 (갭 아님 — 설계대로)
- **티원(tb3_1) = RealSense 비전 전용**(role:vision), **젠지(tb3_2) = Pi Camera + 센서 전용**(role:sensor). 조도/PIR/가스는 젠지 단독이 **설계대로**이며 티원엔 물리 센서가 없다. Unity에서 티원 탭 선택 시 센서 카드 `--` 표시가 정상 동작. TopicRegistry `tb3_1` 센서 null도 정상. → "두 로봇 모두 카메라"는 둘 다 OK, "센서"는 젠지 탭에서만(정상).

### 미해결 갭 (다음 작업)
1. **런타임 토픽 0** — 두 로봇 bringup/카메라 노드 미실행. Unity 켜도 데이터 안 옴. 실제 화면 확인은 양 로봇 bringup + 카메라(젠지 Pi Camera / 티원 RealSense) 기동 필요.
2. **ControlRoomApp IP 하드코딩** (`192.168.0.250` fallback + `t1@192.168.10.250`) — IP drift 위반, hostname/mDNS 전환 검토.
3. **젠지 센서 토픽 `/sensors/*` namespace 미분리** — Phase 3에서 `/tb3_2/sensor/*`로 정합 예정.
- evidence: `docs/evidence/2026-06-15-wireless-unify-domain210-unity-dualrobot-check.md`

---

## 2026-06-10 — Mac MPS + T1 RealSense → YOLOv8n 라이브 PASS + 영상 끊김 정량 진단 + 자산 5종 영구화

### 비전 트랙(Mac 절반) 검증 완료

- **결정**: 박물관 시연 비전 트랙은 **라즈베리(T1)는 영상 publish만, Mac MPS가 YOLO 추론**의 분업 구조를 본선 후보로 채택. 라즈베리에서 YOLO 안 돌림(CPU 한계).
- **결과**:
  - Mac MPS + cv2 + YOLOv8n: **26.0 fps headless / 16~17 fps GUI imshow**
  - 탐지: person 0.89 / keyboard 0.91 / cup 0.86 / tv 0.79 / laptop / mouse / cell phone 등 안정
  - 결과 이미지: `test/realsense_yolo_result.jpg`
- **데이터 경로**: T1 RealSense D435 → `realsense2_camera` (compressed 29Hz 2.17MB/s) → `web_video_server` (port 8080, MJPEG HTTP) → Mac `cv2.VideoCapture(http://...)` → YOLO(mps) → cv2.imshow
- **병렬 다리 3개**: `web_video_server` (8080, cv2/브라우저) + `foxglove_bridge` (8765, Foxglove Studio) + `ros_tcp_endpoint` (10000, Unity). 모두 같은 T1 토픽 별도 TCP 구독.

### 영상 끊김 정량 진단 (8지표) + compressed 전환

- **원인 진단**: raw `/camera/.../image_raw` = 11.27 Hz × 14.24 MB/s = **114 Mbps** → Wi-Fi link rate 65 Mbps의 **1.75배 초과** → publish/transmit 둘 다 못 따라가 끊김 누적.
- **해결**: Foxglove Image 패널 토픽을 `.../image_raw/compressed` (29.22 Hz × 2.17 MB/s = 17 Mbps)로 1줄 변경.
- **효과**:
  - 라즈베리 `realsense_node` CPU **87.5% → ~0%** (-87%p, raw subscribe 없어진 효과)
  - 네트워크 외부 흐름 **14.24 → 2.17 MB/s** (-85%)
  - 발행률 **11.27 → 29.22 Hz** (×2.6)
  - Foxglove 클라이언트 drop/error 0건

### 박제된 자산 (스킬 3종 + 메모리 1종 + 코드 1종 + evidence 1건)

- 🆕 **`.claude/skills/robot-ip-detect-fallback/SKILL.md`** — mDNS 깨졌을 때 ARP 라즈베리 OUI(`d8:3a:dd`/`2c:cf:67`/`dc:a6:32`/`b8:27:eb`/`e4:5f:01`) + `known_hosts` ed25519 host key 매칭으로 신원 추적. 2026-06-10 사례: Wi-Fi 대역 `0.x`→`10.x` 점프, `rb.local` 실패했지만 ed25519 매칭으로 T1=`192.168.10.250` 확정.
- 🆕 **`.claude/skills/robot-camera-stream-diag/SKILL.md`** — 카메라 영상 끊김 6대축 8지표 한 ssh 호출 동시 측정 + raw vs compressed 비교 + 해결 옵션 표. 박물관 시연 dry-run 매 회 첫 검증.
- ✏️ **`.claude/skills/robot-camera-bringup/SKILL.md`** §C/§D/§E + 함정 #19 추가
  - **§C** `ssh -fn` 표준 detach 패턴 (기존 `nohup ... & disown` heredoc 안에서 SSH session 종료 시 로그조차 안 생기는 케이스 회피)
  - **§D** `foxglove_bridge` 통합 (port 8765, Foxglove Studio dmg 클라이언트)
  - **§E** compressed 우선 정책 (Wi-Fi 65Mbps 환경 표준)
  - **함정 #19** `nohup ... & disown` heredoc detach 실패 사례
- ✏️ **메모리 `project_robot_ip_dynamic.md`** — "mDNS 자체가 깨졌을 때 fallback" 한 줄 추가 (다음 세션 자동 로드)
- 🆕 **`test/detect_realsense.py`** — Mac MPS RealSense YOLO. env: `FRAMES` `HEADLESS` `SAVE_LAST` `T1_IP` `T1_PORT` `T1_TOPIC`
- ✏️ **`test/CLAUDE.md`** — Y5 진입 한 줄 추가, Y0~Y4 PASS 마크
- 🆕 **evidence**: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`

### T1 시스템 변경 (apt install 3종)

- `ros-jazzy-foxglove-bridge` 3.2.6
- `ros-jazzy-realsense2-camera` 4.57.7 (+ msgs, description)
- `ros-jazzy-web-video-server` 3.1.0

### 다음 트랙 후보 (이번 세션 종료 시점)

1. 젠지(Pi Camera) 동시 추론 — 이중 카메라 YOLO
2. depth 토픽 결합 — 박스 중심 픽셀 거리 표시
3. Unity ControlRoom 통합 — Mac 추론 결과를 ROS2 `/yolo/detections` 토픽으로 publish
4. realsense 15Hz + depth off 최적화 (박물관 시연 안정성)

---
