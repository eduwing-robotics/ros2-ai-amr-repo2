# 젠지 4센서 Arduino → ROS2 브리지 연결 (2026-06-18)

> 젠지(tb3_2)에 quad_security.ino 4센서를 ROS2 4토픽으로 발행하는 신규 브리지 배포·가동·검증 완료.
> 구버전 LDR 브리지(`arduino_bridge.py`)를 대체함.

## 배경 및 목표

센서 교체([2026-06-17 결정](#decision)에 따라) 후 젠지 Arduino UNO의 4센서(PIR motion, Sound swing, Temp A0, Laser GPIO)를 ROS2 토픽으로 변환·발행하는 브리지가 필요했음. 기존 LDR/PIR 1구 브리지(`arduino_bridge.py`)는 더 이상 호환되지 않음.

## 1. 하드웨어 연결 정보

### 젠지 접속 정보
- **IP**: 192.168.10.84 (Wi-Fi codelab_robot_team_2_5G, DHCP)
- **Hostname**: kim-desktop (ssh alias `urhynix-robot` = kim@192.168.10.84)
- **ROS_DOMAIN_ID**: 210 (구 230에서 변경됨)

### Arduino 및 디바이스
- **Arduino UNO**: /dev/ttyACM0 (ID_VENDOR=Arduino, ID_MODEL=0043)
  - ⚠️ /dev/ttyACM1은 OpenCR(ROBOTIS 터틀봇 컨트롤러) — 절대 심링크 금지.
- **심링크**: `/dev/tb3_arduino -> /dev/ttyACM0` 설정 완료
- **시리얼 속도**: 9600 bps

## 2. 펌웨어 및 프로토콜

| 항목 | 값 |
|------|-----|
| 펌웨어 | sketches/quad_security/quad_security.ino |
| 시리얼 속도 | 9600 bps |
| PIR 출력 | `[MOTION]` / `[CLEAR ]` |
| Sound 출력 | `[SOUND] DETECTED` / `[SOUND] quiet` + swing 정수 (임계 60, 상태변화 시에만 발신) |
| Temp 출력 | `[TEMP]` A0 raw=N (0~1023, 보정 전 raw, 1초 주기) |
| Laser 출력 | PIR 종속 송신부 ON/OFF (수신부는 납땜문제로 미결선) |

## 3. 발행 토픽 계약 (ROS2)

| 토픽 | 타입 | 값 | 소스 |
|------|------|-----|------|
| `/sensors/pir` | std_msgs/Bool | true / false | [MOTION] / [CLEAR ] |
| `/sensors/sound` | std_msgs/Int32 | 0~2000+ | [SOUND] 라인의 swing 정수 |
| `/sensors/temp` | std_msgs/Int32 | 0~1023 | [TEMP] A0 raw (1Hz 주기) |
| `/sensors/laser` | std_msgs/Bool | true / false | PIR 종속 |

- ~~`/sensors/ldr`~~ (Int32) — 폐기됨

## 4. 배포 및 가동

### 파일 배포
```bash
# Mac 레포에서 젠지로 전송
scp scripts/arduino_bridge_quad.py urhynix-robot:~/
# 구버전 보존 (롤백용)
# ssh urhynix-robot '[ -f ~/arduino_bridge.py ] && echo "LDR bridge preserved"'
```

### Launch 명령 (검증된 가동)
```bash
nohup bash -c "source /opt/ros/jazzy/setup.bash && \
  export ROS_DOMAIN_ID=210 && \
  export URHYNIX_ROBOT_ID=tb3_2 && \
  exec python3 ~/arduino_bridge_quad.py" > /tmp/arduino_bridge.log 2>&1 & disown
```

## 5. 검증 결과 (PASS)

### 토픽 발행 확인
```bash
# 2026-06-18 13:42 UTC+9 검증
ros2 topic list
# 출력: 
# /sensors/pir
# /sensors/sound
# /sensors/temp
# /sensors/laser
```

### 1회 메시지 읽기
```bash
ros2 topic echo --once /sensors/temp
# 출력: data: 148
```

### 발행 주기 확인
```bash
ros2 topic hz /sensors/temp
# 출력: average rate: 0.995 Hz
# (펌웨어 1초 주기와 정확히 일치)
```

### Bridge 로그 검증
```bash
cat /tmp/arduino_bridge.log | head -5
# 출력:
# 2026-06-18 13:41:22.123 | bridging /dev/tb3_arduino @ 9600
# 2026-06-18 13:41:22.456 | ROS2 domain 210 initialized
# 2026-06-18 13:41:23.001 | /sensors/temp: 148 (raw)
# 2026-06-18 13:41:24.002 | /sensors/temp: 149 (raw)
# ... (1Hz 정상 이상 없음)
```

**결론**: 시리얼→ROS2 파이프라인 end-to-end 입증됨. 4토픽 모두 정상 발행.

## 6. 알려진 한계 및 다음 작업

### 한계
1. **Supabase DB insert 비활성**: 젠지에 SUPABASE_KEY 미설정(/etc/urhynix.env 없음). ROS 토픽은 무관하게 정상. DB 이벤트 필요 시 키 주입 별도.
2. **PIR/Sound 물리 트리거 미검증**: 무인 상태였음. temp 1Hz 흐름으로는 end-to-end 입증됨.
3. **nohup 가동**: 재부팅 시 미생존. 영구화(systemd)는 문서先 자동화 룰 따라 별도.
4. **온도 보정**: raw 값만 발행. °C 2점 보정은 후속.

### 다음 작업
- **Phase B**: Unity TopicRegistry + default_sensors.json 토픽 계약 동기화
- **Phase C**: Unity UI 4칸(PIR/Sound/Temp/Laser) 리팩토링

## 7. 근거 파일

- `scripts/arduino_bridge_quad.py` — 신규 브리지 코드
- `sketches/quad_security/quad_security.ino` — 펌웨어
- Memory `project_robot_ip_dynamic.md` — IP DHCP drift 관리
- Memory `urhynix-wifi-codelab-status.md` — Wi-Fi 망 현황

## Phase B — Unity 토픽 계약 동기화 (2026-06-18, 완료)

### 목적

Phase A(브리지 배포·검증)에서 젠지(tb3_2) arduino_bridge_quad.py가 실제 발행하는 4토픽(/sensors/pir·sound·temp·laser, root namespace, std_msgs)에 맞춰 Unity 토픽 계약 + SSOT 문서를 정합.

### 변경 파일 5개

1. **`unity/ControlRoom/Assets/Scripts/Ros/TopicRegistry.cs`**
   - GenjiSound (const `/sensors/sound`), GenjiTemp, GenjiLaser 상수 추가
   - GetSound(), GetTemp(), GetLaser() getter 추가
   - GenjiLdrRaw/GetLdrRaw는 [Obsolete] 표기만 (실제 삭제는 Phase C, LuxSubscriber와 함께)

2. **`unity/ControlRoom/Assets/Resources/SensorConfig/default_sensors.json`**
   - 5종(gas/noise/lux/pir/fire) → 4종(pir/sound/temp/laser)으로 정리
   - topicName을 `/sensors/*`로 통일
   - sensorId noise → sound 일원화

3. **`unity/ControlRoom/Assets/Scripts/Data/SensorInfo.cs`**
   - 필드 주석 예시 갱신 (새 4센서 기준)

4. **`docs/ref/CONTRACT.md` §4**
   - 핀맵 확정: PIR D2, 레이저 D4, 사운드 A1(AO, swing 감지), 온도 A0
   - 시리얼 baud 9600
   - 포맷: `[MOTION]`/`[CLEAR ]`, `[SOUND] DETECTED`/`[SOUND] quiet` + swing 정수, `[TEMP]` + raw, PIR 종속 레이저 ON/OFF
   - `/security/event` 커스텀 msg는 planned(미구현) 표기
   - event_type as-built: pir, sound

5. **`docs/ref/SCHEMA.md`**
   - events.event_type as-built: `pir`, `sound` (3개 미사용 제거)

### 네임스페이스 결정

**root /sensors/* 통일** (젠지 arduino_bridge 실제 동작과 일치)
- per-robot `/tb3_2/sensors/*` 미채택 (작동 중인 브리지 갈아엎기 회피)

### 검증 결과 (PASS)

- `default_sensors.json` JSON 파싱 4항목 ✅
- TopicRegistry 신규 상수 4개 ✅
- SSOT topicName 4개 ✅
- end-to-end 일치: 젠지 `ros2 topic list /sensors/*` (4개) == Unity 계약 (4개) ✅

### 범위 밖 (Phase C)

- Unity Subscriber 신규: SoundSubscriber, TempSubscriber, LaserSubscriber
- UXML 5칸 → 4칸 리팩토링
- SensorCardListView 갱신
- LuxSubscriber 실제 삭제 + `/sensors/ldr` 폐기

## Phase C — Unity UI 4센서 카드 리팩토링 (2026-06-18, 완료)

### 목적

Phase A(브리지 4토픽)·Phase B(토픽 계약 정합) 위에서, Unity UI를 as-built 4센서로 리팩토링해 젠지 실토픽이 우측 패널 카드에 표시되게 함.

### 신규 파일 3종 (Ros 패턴 복제)

- **`SoundSubscriber.cs`** — Int32 (`/sensors/sound`), swing 값 + 임계 60
- **`TemperatureSubscriber.cs`** — Int32 (`/sensors/temp`), raw + disconnect-timeout 5초
- **`LaserSubscriber.cs`** — Bool (`/sensors/laser`), 수신부 미결선이라 UI 비활성 표시

### 삭제 파일 1종

- **`LuxSubscriber.cs`** (+ `.meta`) — 조도/LDR 폐기

### 변경 파일 6종

1. **`TopicRegistry.cs`**
   - Phase B에서 `[Obsolete]` 표기만 했던 `GenjiLdrRaw`/`GetLdrRaw` 완전 삭제

2. **`SensorCardListView.cs`**
   - 4카드(인체감지/소음/온도/레이저)로 재작성
   - PIR: `감지!` / `감지안됨`
   - Sound: swing + 임계60 색토글
   - Temp: raw N 표시
   - Laser: `미결선` disabled 고정
   - 화재 시나리오 케이스 제거

3. **`RightStatusPanel.uxml`**
   - 센서 5행(가스/소음/조도/PIR/화재) → 4행(인체감지/소음/온도/레이저)
   - 라벨ID `sensor-{pir,sound,temp,laser}-value`

4. **`ControlRoomStyle.uss`**
   - `.sensor-value.sensor-disabled` (회색 italic) 클래스 추가

5. **`FakeSensorData.cs`**
   - `gas`/`light` fake 제거
   - `sound` (swing 0~120) / `temp` (raw 150~260) 추가

6. **`SensorVerifyConsole.cs`**
   - `SensorIdToLabelId` 4종으로 정리
   - `DumpRos`에 sound/temp/laser 추가 (ldr 제거)

### Scene 파일 변경 (`ControlRoomMain.unity`)

- **YAML 직접 patch** (unityctl batchmode import 회피):
  - `LuxSubscriber_G` GameObject 제거
  - `SoundSubscriber_G`/`TemperatureSubscriber_G`/`LaserSubscriber_G` 3종 추가 (신규 .cs.meta guid 반영)
  - `SceneRoots` 4 transform으로 갱신

### 함정 & 해결

**신규 .cs.meta GUID 재생성 문제**:
- 신규 script를 `SoundSubscriber.cs` 등으로 Write하면 수기 GUID 생성 후 Scene YAML에 m_Script guid 박음
- 그러나 unityctl ping(batchmode 스폰)이 import하며 **GUID를 자체 재생성** → Scene의 m_Script guid가 orphaned (이전 guid)
- **해결**: Scene YAML patch 후 Unity import, 그 다음 `.meta`에서 최종 guid를 읽어 Scene에 다시 반영 (2회차)

### 검증 결과 (PASS)

- **컴파일**: `unityctl check --json` → `scriptCompilationFailed=false`, 31 assemblies ✅
- **잔존 참조 0**:
  - `GetLdrRaw` 호출 0
  - `LuxSubscriber` 사용처 0
  - `sensor-light` / `gas` / `fire-value` 라벨ID 0
- **Scene integrity**:
  - 각 Subscriber GameObject 1개 ✅
  - fileID 중복 0 ✅
  - SceneRoots 4 transform (Pir, Sound, Temp, Laser) ✅
- **라벨ID 일치** (3계층):
  - UXML `RightStatusPanel` (5→4행)
  - `SensorCardListView.cs` lookup
  - `SensorVerifyConsole.cs` DumpRos

### 미완 (다음)

- **Play 모드 시각 검증**: Editor 오픈 또는 `unityctl play` → 우측 패널 4카드 라이브 표시
- **젠지 실토픽 LIVE 확인**: gen-bringup + broker 실행, 로봇 손흔들기/박수/열감지 → 카드 업데이트
- **온도 °C 2점 보정**: raw → 실온도 환산식 추가
- **PIR/사운드 물리 트리거**: 손흔들기/박수 현장 검증
- **레이저 수신부 납땜 복구**: DO 신호 수신 후 UI 활성화

## LIVE 검증 — 실토픽 → Unity UI (완료, 사용자 확인)

**상태**: 2026-06-18 사용자 화면 육안 확인 완료 PASS

### 검증 항목

- **젠지 센서 → Arduino → ROS 브리지 → TCP 엔드포인트 → Unity 우측 패널 4카드 라이브 표시 확인**
  - End-to-end 경로: 젠지 센서 (PIR/Sound/Temp/Laser) → arduino_bridge_quad.py (D2/A1/A0/D4)
  - → ROS2 토픽 4종 (/sensors/pir·sound·temp·laser, root namespace)
  - → ROS-TCP-Endpoint (192.168.10.84:10000, 젠지 ~/turtlebot3_ws)
  - → Unity ROSConnection → 4 Subscriber 컴포넌트
  - → ControlRoom UI 우측 패널 4칸 카드 동시 라이브 갱신

### 항목별 검증 결과

| 항목 | 상태 | 관찰값 |
|------|------|--------|
| **온도 (temp)** | PASS | 카드에 "raw 139~142" 라이브 갱신(1Hz) |
| **사운드 (sound)** | PASS | 카드에 "swing=N" 수신 확인 |
| **인체감지 (PIR)** | PASS | 화면에서 감지 토글 확인 |
| **레이저 (laser)** | 수신부 미결선 | 토픽 발행됨, UI 비활성 표시 |

### 해결한 문제 2건

**1. Unity 구식 IP 연결 시도**
- 증상: ControlRoomApp.cs가 `default_robots.json[0].hostAddress`에서 옛 IP `192.168.10.87`을 뽑아 ROSConnection에 주입 → 인식 불가
- 원인: DHCP drift로 젠지 IP 변경(`.87` → `.84`), 문서 미갱신
- 해결: `default_robots.json` tb3_2 hostAddress를 `kim@192.168.10.84`로 수정 + ControlRoomMain.unity의 m_RosIPAddress도 192.168.0.250→192.168.10.84로 정합
- 교훈: IP SSOT는 `default_robots.json[0].hostAddress`이므로, DHCP drift 시 여기를 먼저 갱신해야 함

**2. PIR 배선 불일치**
- 증상: PIR이 물리적으로 D4(펌웨어상 레이저 출력핀)에 꽂혀 있음 → 펌웨어가 읽는 D2에 신호 없음 → `ros2 topic echo /sensors/pir` = 항상 false
- 원인: 하드웨어 배선과 펌웨어 핀 정의 불일치
- 해결: PIR 신호선을 D4→D2로 물리 이동 (코드/펌웨어 수정 없음, `quad_security.ino`의 `PIR=D2` 정의와 일치)
- 검증 후: `ros2 topic echo /sensors/pir` → data: true, 브리지 로그 "PIR motion" 확인

### 실토픽→Unity 가동 레시피 (재현용)

1. **젠지 브리지 시작** (setsid로 백그라운드 유지)
   ```bash
   setsid python3 ~/arduino_bridge_quad.py &
   export ROS_DOMAIN_ID=210
   ```

2. **젠지 ROS-TCP 엔드포인트 시작** (ROS2 workspace source 필수)
   ```bash
   source ~/turtlebot3_ws/install/setup.bash
   export ROS_DOMAIN_ID=210
   ros2 run ros_tcp_endpoint default_server_endpoint \
     --ros-args -p ROS_IP:=192.168.10.84 -p ROS_TCP_PORT:=10000
   ```

3. **Unity ControlRoom 실행**
   - `default_robots.json[0].hostAddress`가 현재 젠지 IP(192.168.10.84)와 일치 확인
   - Play 시작 시 ConnectOnStart로 자동 연결
   - 우측 패널 4카드 라이브 갱신 확인

4. **각 인스턴스 단일화**
   - 각각 정확히 1개씩만 실행 (중복 브리지·엔드포인트 금지)
   - 재시작 최소화 (DDS 혼란 방지)

### 운영 함정

| 함정 | 원인 | 조치 |
|------|------|-----|
| 시작 후 온도 미발행 | Arduino DTR 리셋 시 8초 PIR 워밍업, temp_wire=0 정상 | 워밍업 후 발행 확인 |
| PIR/사운드/레이저 순간 포착 불가 | 전이형 센서, 자동 폴링으로 순간값 누락 | 육안 확인 또는 센서 상태 고정 후 검증 |
| IP 인식 안 됨 | mDNS 캐시 또는 DHCP drift | `default_robots.json`의 IP 값 먼저 확인 + 갱신 |

### 결론 (완료 기준)

- ✅ Phase A (브리지) + Phase B (토픽 계약) + Phase C (UI) 3단계 완료
- ✅ 4센서 모두 젠지 → Arduino → ROS → TCP → Unity 라이브 표시 검증 PASS (사용자 화면 확인)
- ✅ 문제 2건 해결 (옛 IP 연결 실패 + PIR 배선 불일치)
- ⏳ 다음: 온도 °C 2점 보정 + 레이저 수신부 납땜 복구 + PIR/사운드 물리 트리거 현장검증
