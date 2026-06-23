---
name: slam-nav2-arena-survey
description: TurtleBot3 + LDS-03으로 경기장 SLAM 맵을 산출하고, Nav2 1-waypoint 베이스라인 검증 후, 결과 맵을 Unity 디지털 트윈 씬에 임포트하는 6 Phase 흐름.
when_to_use:
  - 새 경기장/실내 공간에 처음 진입해서 점유 그리드를 만들 때
  - SLAM 품질(드리프트·루프클로저·해상도)을 정량 평가할 때
  - 산출된 맵을 Unity Plane 텍스처 + 좌표축 변환까지 옮길 때
inputs:
  - 로봇 부팅 + Wi-Fi 동일 LAN (192.168.10.0/24)
  - macOS/Ubuntu 호스트 + tb3.sh source 완료 + tb3-key-setup 1회 완료
outputs:
  - docs/evidence/maps/<map_name>/{*.pgm, *.yaml, *.png, eval.md}
  - docs/evidence/<YYYY-MM-DD>-slam-arena.md (재현 가능한 측정 기록)
  - unity-smoke/Assets/Maps/<map_name>.png (텍스처)
references:
  - https://emanual.robotis.com/docs/en/platform/turtlebot3/slam/
  - https://emanual.robotis.com/docs/en/platform/turtlebot3/navigation/
  - http://wiki.ros.org/map_server  # pgm + yaml 포맷 정의
exit_criteria:
  - /map 토픽 hz ≥ 0.5 확인됨
  - Nav2 goal 1개 → 도착 거리 오차 ≤ 30cm
  - Unity Plane에 맵 텍스처가 1u=1m 스케일로 표시됨
---

# slam-nav2-arena-survey

## 무엇

TurtleBot3 Burger + LDS-03 LiDAR로 경기장을 SLAM(cartographer) 매핑하고 Nav2 1-waypoint를 통해 베이스라인을 검증한 뒤, 산출 맵을 Unity 디지털 트윈 씬에 임포트한다.

> **2026-06-16 환경 갱신**: 본 스킬의 명령은 `ROS_DOMAIN_ID=210` + `192.168.10.x` 망 기준으로 업데이트됨(이전 56 / 192.168.0.x). 대상 기체 = 젠지(`kim@192.168.10.87`, LDS-03). 헬퍼 `scripts/tb3.sh`도 동일 갱신.
> **신규 목표(검증 중)**: Unity 임포트를 기존 정적 PNG 텍스처(경로 A) 대신 **`/map` OccupancyGrid 라이브 구독 → ControlRoom MapPanel Texture2D 렌더(경로 B)**로 확장. 근거·플랜: `docs/evidence/2026-06-16-unity-live-occupancygrid-slam-research.md`.

## 결정 트리 — Robot 직접 vs Mac 외부 (2026-05-29 검증)

```
Q. cartographer를 어디에서 실행할 것인가?

  A1. 로봇 자체 (RPi 4)        ← ✅ 권장 (검증됨)
       - 5분 안에 결과
       - 디스크 >= 800MB 확보돼 있어야 (tb3-disk-cleanup으로 회복 가능)
       - RPi 4 + LDS-03은 5×5m 환경에 충분
       - 환경 변수는 multicast 모드만 (ROS_DISCOVERY_SERVER 사용 금지)

  A2. Mac Docker / VM       ← ❌ 비추 (오늘 모든 경로 실패)
       - macOS Docker host networking: outbound NAT만, inbound UDP 미라우팅 → DDS 발견 실패
       - Multipass on Apple Silicon: QEMU cloud-init hang
       - UTM QEMU bridged: efi_vars.fd 좀비 lock 빈발
       - 향후 Mac에서 진짜 필요하면 → OrbStack 또는 동료 Ubuntu native

  A3. 동료 Ubuntu native      ← ✅ A1 디스크 부족·CPU 부담 시 fallback
       - native Linux는 host networking + multicast 정상
       - 우리 helpers cross-platform 그대로 작동
       - SLAM 결과 git push → Mac이 git pull + Unity 임포트
```

**오늘 가장 시간 효율 좋았던 경로: A1 (로봇 직접)**. Mac VM/Docker는 macOS hypervisor 한계라 본 use case에 부적합.

## 왜 (Why)

- 박물관/미술관 액자 보호 경비 시나리오 — 사전 정의된 waypoint 순찰을 위해 점유 그리드가 SCRUM-10/16의 전제 조건.
- 맵 품질을 정량적으로 측정해야 다음 Sprint(추가 매핑 vs 부분 보강) 판단이 가능.
- Unity 디지털 트윈은 ROS `/map` 토픽을 실시간으로 받는 형태가 아니라, **사전 매핑 결과 PNG + yaml 메타데이터**를 정적으로 깔고 실시간 토픽은 그 위에 오버레이하는 구조 (`tb3_1/tb3_2` 다중 로봇 확장 대비).

## 사전 준비 (한 번만)

```bash
# 호스트 (Mac/Ubuntu)
source ~/URHYNIX/scripts/tb3.sh   # rc에 이미 source되어 있으면 skip
tb3-help                          # 7개 SLAM helper 표시 확인
tb3-pkg-check                     # 로봇 측 4개 패키지 확인

# 로봇 측 누락된 경우:
tb3-ssh
sudo apt update
sudo apt install -y ros-jazzy-turtlebot3-cartographer \
                    ros-jazzy-turtlebot3-navigation2 \
                    ros-jazzy-nav2-map-server \
                    ros-jazzy-teleop-twist-keyboard \
                    imagemagick   # pgm → png 변환용
```

호스트(Mac/Ubuntu) PNG 변환 도구 — **둘 중 하나만 있으면 됨**:
- ImageMagick: `brew install imagemagick` (macOS) 또는 `sudo apt install imagemagick` (Ubuntu)
- Python PIL: `pip3 install Pillow` (이미 설치된 경우 그대로)

`tb3-fetch-map`이 자동으로 둘 다 시도하므로 어떤 것이 있어도 OK.

---

## Phase 0 — 연결 (5분)

```bash
tb3-go                # bringup + ros_tcp_endpoint + arduino_bridge + verify
tb3-port              # TCP 10000 LISTEN 확인
tb3-unity             # Unity Editor 자동 Play → 5채널 LIVE 확인 (선택)
```

검증:
- `tb3-myip` 결과가 `192.168.10.x` ✅
- `tb3-ip` 결과가 로봇 IP 1개 반환 ✅
- `tb3-port` 결과: `Connection succeeded`

실패 시 → `tb3-restart` 후 다시. 그래도 안 되면 `tb3-logs`.

---

## Phase 1 — SLAM 시작 (5분)

```bash
tb3-slam              # cartographer tmux 세션 시작 (multicast 모드)
sleep 8
ssh kim@$(tb3-ip) 'bash -c "source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && ros2 daemon stop >/dev/null; ros2 daemon start; sleep 3; timeout 8 ros2 topic hz /map"'
```

검증:
- `/map` 토픽 publish rate ≥ 0.5 Hz (1.0Hz가 cartographer 기본)
- `/scan` 10Hz 정상 publish

문제 발생:
- **`/map`이 안 나오는데 `/scan`은 보임** ← bringup과 cartographer의 ROS 모드 불일치 가능성. 둘 다 multicast(SUBNET) 또는 둘 다 Discovery Server. 섞이면 통신 안 됨. urhynix_robot_up.sh에 `ROS_DISCOVERY_SERVER`이 있으면 제거. (2026-05-29 학습)
- `/map` 자체가 안 나옴 → `tb3-ssh` 후 `tmux a -t slam`으로 cartographer 로그 직접 확인. lua 설정 로드 메시지 + `Added trajectory with ID '0'`이 보여야 정상.
- TF 트리 깨짐 → `bringup`이 죽었을 가능성. `tb3-logs`로 bringup 로그 확인.
- 워크스페이스 setup.bash 깨짐(`Package not found`) → `~/turtlebot3_ws/build`를 누군가 지웠음. `colcon build --symlink-install --parallel-workers 1 --executor sequential`로 재빌드 (sequential은 OOM 회피). (2026-05-29 학습)

---

## Phase 2 — 매핑 주행 (15-25분)

원칙:
- **천천히** (Burger 권장 0.10 m/s, 회전 0.5 rad/s).
- **시계 또는 반시계 한 방향 루프** — 작은 8자 금지 (드리프트 누적).
- **루프 클로저** 위해 출발점으로 돌아와 일부 구간을 한 번 더 통과.
- **벽 가까이** 통과해 LiDAR가 충분히 닿게 (Burger LDS-03은 0.16-3.5m 권장).

```bash
# 새 터미널에서:
tb3-teleop            # i/j/k/l/, 키 (k=정지, q/z=속도)

# RViz 확인 (별도 터미널):
tb3-vnc               # robot RViz 화면 모니터링
```

기록(필수):
- 시작 시각, 경기장 대략 치수(가로×세로 m), 출발-종료점 동일 여부
- 잘 못 잡힌 구간 사진 (전화기)

종료 신호:
- 출발점 ±30cm 내 복귀
- RViz 점유 그리드의 회색 영역이 더 이상 확장되지 않음
- 또는 25분 경과

---

## Phase 3 — 맵 저장 (1분)

```bash
tb3-slam-save arena_v1        # robot ~/maps/arena_v1.{pgm, yaml}
tb3-fetch-map arena_v1        # → docs/evidence/maps/arena_v1/
ls docs/evidence/maps/arena_v1/
```

산출물:
- `arena_v1.pgm` — 회색조 점유 그리드 이미지 (P5 PGM, 8비트)
- `arena_v1.yaml` — 메타데이터

`yaml` 내용 예시:
```yaml
image: arena_v1.pgm
mode: trinary
resolution: 0.050000    # 1 픽셀 = 5cm
origin: [-10.0, -10.0, 0.0]   # 픽셀(0,0) = 월드(-10,-10) m
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
```

⚠️ `resolution`과 `origin`은 다음 Phase에서 모두 사용. 절대 잃어버리지 말 것.

---

## Phase 4 — 평가 (10분)

`docs/evidence/maps/<map_name>/eval.md`를 다음 템플릿으로 작성:

```markdown
# SLAM arena 평가 — <map_name>

- 일시: YYYY-MM-DD HH:MM
- 장소: <경기장 이름 / 룸 번호>
- 경기장 대략 치수: 가로 W m × 세로 H m
- 매핑 시간: M 분
- 주행 거리(추정): D m

## 정량 지표
| 지표 | 측정 | 목표 | PASS/FAIL |
|---|---|---|---|
| resolution (m/pixel) | 0.05 | 0.05 | |
| 점유 그리드 너비(px) | | | |
| 점유 그리드 높이(px) | | | |
| 실제 너비 = px × resolution (m) | | ≈ W | |
| 실제 높이 = px × resolution (m) | | ≈ H | |
| 루프 클로저 잘림 | (눈으로 본 갭) | < 20cm | |
| 빈 영역(미매핑) 비율(육안) | | < 20% | |
| 동적 장애물(사람) 잔상 | | 없음 권장 | |

## 정성 평가
- 잘 잡힌 구간: ...
- 깨진 구간 / 원인: ...
- 다음 매핑에서 보완할 운전 패턴: ...

## 첨부
- arena_v1.pgm (회색조)
- arena_v1.yaml
- arena_v1.png (변환본)
- 현장 사진 N장 (사진은 `docs/evidence/maps/<map_name>/photos/`)
```

---

## Phase 5 — Unity 임포트 (20분)

### 5a) pgm → png 변환 + Unity로 복사 + 스케일 계산 (한 줄)

```bash
tb3-fetch-map arena_v1      # robot → docs/evidence/maps/arena_v1/{.pgm,.yaml,.png}
tb3-map-to-unity arena_v1   # → unity-smoke/Assets/Maps/ + Plane scale 자동 계산 출력
```

`tb3-map-to-unity`는 yaml의 `resolution`과 PNG 해상도를 읽어 Unity Plane scale (.x, .z) 값을 계산해서 출력한다. 그대로 인스펙터에 입력하면 됨.

### 5b) Unity 텍스처 import 설정

Unity Editor에서 `Assets/Maps/arena_v1.png` 선택:

| 설정 | 값 | 이유 |
|---|---|---|
| Texture Type | Default | |
| sRGB (Color Texture) | OFF | 점유 그리드는 선형 데이터 |
| Wrap Mode | Clamp | 맵 바깥 반복 금지 |
| Filter Mode | Point (no filter) | 픽셀당 점유 의미가 흐려지면 안 됨 |
| Max Size | 4096 | 4K까지 보존 |
| Compression | None | 점유 임계값(occupied/free)이 깨지면 안 됨 |

### 5c) Plane 스케일 계산

- 픽셀 너비 = `Wpx`, 높이 = `Hpx`
- resolution `r` (m/pixel, yaml에서 가져옴, 기본 0.05)
- 실제 너비 (m) = `Wpx × r`
- 실제 높이 (m) = `Hpx × r`

Unity 기본 Plane은 10u × 10u (XZ 평면). Plane scale:
- `scale.x = (Wpx × r) / 10`
- `scale.z = (Hpx × r) / 10`
- `scale.y = 1`

예: 200×150 px, r=0.05 → 10m × 7.5m → scale = (1.0, 1, 0.75)

### 5d) 좌표축 변환 (ROS ↔ Unity)

| 축 | ROS REP-103 | Unity |
|---|---|---|
| 전진(forward) | +X | +Z |
| 좌측(left) | +Y | +X (-X for right) |
| 위(up) | +Z | +Y |

Plane 위치(월드 원점):
- ROS yaml `origin` = `[ox, oy, 0]`. Plane 중심 = `((Wpx × r) / 2 + ox, 0, (Hpx × r) / 2 + oy)`.
- Unity로 변환: `position = (-oy_unity, 0, ox_unity)` (Y/X swap + Y 부호 반전).
- Plane 회전: `Rotation.Euler(90, 0, 0)` (XZ 바닥에 PNG가 보이도록).

⚠️ 첫 임포트 시에는 단순화: Plane을 (0,0,0)에 놓고 점유 그리드 중심이 원점에 오게 시각적 정렬만. 정확한 origin 매칭은 Nav2 통합 단계에서.

### 5e) 검증

Unity Editor에서:
1. 새 Empty GameObject "ArenaMap" 생성, 위치 (0,0,0)
2. 자식으로 Plane 추가, 위에서 계산한 scale 적용
3. Material에 `arena_v1.png` 텍스처 할당 (Unlit/Texture shader 권장)
4. 카메라를 위에서 내려다보도록 (Y=10, X=Z=0, Rotation=(90,0,0))
5. 점유된 검은 영역과 빈 흰 영역이 보이면 OK

스크린샷을 `docs/evidence/maps/<map_name>/unity_preview.png`로 저장.

---

## Phase 6 (선택) — Nav2 1-waypoint 베이스라인 (15분)

이전 phase의 맵 위에서 Nav2를 띄우고 RViz에서 goal 클릭 → 도착 거리 측정.

```bash
tb3-nav2 arena_v1
sleep 10
tb3-rviz              # robot RViz (Nav2 panel 활성)
tb3-vnc               # 화면 보기
```

RViz 절차:
1. `2D Pose Estimate` 클릭 → 로봇의 현재 위치/방향에 화살표 드래그 (수동 초기화).
2. `Nav2 Goal` 클릭 → 맵 위 도착 지점 클릭.
3. 로봇이 자동으로 경로 계획 + 주행.
4. 도착 시 실제 위치와 클릭한 위치의 거리 측정 (줄자).

기록(`eval.md`에 추가):
```markdown
## Nav2 베이스라인
| 항목 | 측정 |
|---|---|
| 클릭한 goal 좌표 (RViz) | (x, y, θ) |
| 실제 도착 좌표 (줄자) | (x', y') |
| 위치 오차 | sqrt((x-x')² + (y-y')²) m |
| 도착 시간 | s |
| 충돌 횟수 | |
| 회복 동작(recovery) 발생 | y/n |
```

목표: 위치 오차 ≤ 30cm.

---

## 정리 (세션 종료)

```bash
tb3-ssh
tmux kill-session -t slam 2>/dev/null
tmux kill-session -t rviz 2>/dev/null
tmux kill-session -t nav2 2>/dev/null
tmux ls
exit

# 또는 한 방:
tb3-down              # bringup·ros_tcp·arduino_bridge·slam·rviz·nav2 모두 정리
```

세션 종료자 체크리스트:
- [ ] `docs/evidence/maps/<map_name>/` 4파일(.pgm/.yaml/.png/eval.md) 모두 존재
- [ ] `docs/evidence/<YYYY-MM-DD>-slam-arena.md`로 재현 가능한 명령 시퀀스 기록
- [ ] `docs/status/HANDOFF.md`의 "지금 즉시 해야할 일"에 다음 액션 갱신
- [ ] 변경분 git commit + push

---

## 자주 발생하는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `/map` 토픽 안 나옴 | cartographer 죽음 (lua 설정 못 찾음) | robot 측 `tmux a -t slam`로 직접 로그 확인. `turtlebot3_cartographer` 패키지 재설치. |
| 점유 그리드가 회전한 채 누적 | TF 트리 깨짐, base_footprint↔odom 누락 | `bringup` 재기동 후 SLAM 재시작. |
| LiDAR 못 잡힘 | LDS-03 USB 분리 또는 펌웨어 멈춤 | LiDAR 메인 스위치 OFF→ON. `ros2 topic hz /scan`. |
| 매핑 도중 로봇 멈춤 | OpenCR 통신 끊김 (USB reset) | `tb3-down` → `tb3-up` 재기동. |
| Nav2 path planning 실패 | 맵 외곽이 너무 좁음 (inflation radius < 로봇 폭) | nav2_params.yaml의 `inflation_radius`를 0.25 → 0.15로 낮춤. |
| 첫 매핑 후 origin 좌표가 음수 | cartographer의 점유 그리드는 첫 위치를 기준으로 ± 확장 | 정상. yaml `origin`의 부호를 그대로 사용. |
| RViz Linux libGL 에러 | 헤드리스 + DISPLAY 없음 | `DISPLAY=:2` 환경변수 (이미 helper에 포함). VNC 필수. |
| `/scan`은 보이는데 `/map` 안 나옴 | bringup과 cartographer의 ROS 모드 불일치 (한쪽 DS, 한쪽 multicast) | `urhynix_robot_up.sh`에서 `ROS_DISCOVERY_SERVER`/`ROS_SUPER_CLIENT` 제거 → multicast 통일. `tb3-down`→`tb3-up`→`tb3-slam`. |
| `Package 'turtlebot3_bringup' not found` | `~/turtlebot3_ws/build` 누군가 지움 → install/setup.bash hook 깨짐 | 워크스페이스 재빌드: `cd ~/turtlebot3_ws && colcon build --symlink-install --parallel-workers 1 --executor sequential`. 8 패키지 6-10분. |
| colcon build 중 SSH thrash + sshd hang | RPi 4 4GB RAM + 병렬 빌드 OOM → swap thrash | `--parallel-workers 1 --executor sequential` 강제. `nohup` + `disown`으로 SSH 끊겨도 빌드 살아남게. |
| RPi 디스크 0 byte 도달 + dpkg hang | apt 작업 중 SD 풀 (15GB SD, 96%+ 사용) | `echo "$PW" \| ssh -T host 'sudo -S -p "" journalctl --vacuum-size=10M'` 200MB+ 즉시 회복. 또는 `tb3-disk-cleanup`. 그래도 hang이면 power cycle. |
| robot SSH는 살았는데 daemon이 stale 환경으로 떠있음 | bringup launch 후 ros2 daemon이 이전 env 캐시 | 콘솔에서 `ros2 daemon stop && ros2 daemon start` 후 topic list. |
| Mac 컨테이너에서 robot topic 미발견 | macOS Docker host networking은 outbound NAT만 (inbound UDP 미라우팅) | A) robot 직접 cartographer 권장. B) 동료 Ubuntu native. C) OrbStack. 자세한 진단 `MAC-DOCKER-ROS2-PLAYBOOK.md §6.5`. |
| `scp host:dir/{a,b}` 분리 안 됨 | macOS scp client가 brace expansion 미지원 | `.pgm`과 `.yaml` 분리 scp. tb3-fetch-map은 이미 분리 패턴. |
| `tb3-up`이 `tmux: command not found` | 로봇에 tmux 미설치 (기체마다 다름. 젠지 2026-06-16) | `ssh kim@<ip> "echo <pw> \| sudo -S apt-get install -y tmux"` |
| `cartographer.launch.py` FileNotFoundError (ws install 경로) | `~/turtlebot3_ws` symlink-install인데 `src/turtlebot3_cartographer` 삭제됨 → install의 launch가 **깨진 심볼릭 링크** | ws 오버레이 source 없이 `/opt/ros/jazzy`만 source해 **apt판** 실행. (`readlink`로 깨진 링크 확인) |
| Unity가 /map 등록은 됐는데 데이터 안 옴 + 곧 끊김 | codelab WiFi `Broken pipe`(핑 75~136ms 변동) | ROS-TCP 자동 재연결로 링크 안정 시 수신됨. 안정 시연은 codelab_5G 근접 배치. [[urhynix-wifi-codelab-status]] |
| Unity 첫 맵 수신 로그가 Editor.log에 안 보임 | `ControlRoomEvents.RaiseLogAdded`는 인앱 로그 패널 전용(Editor.log 미기록) | 검증 시 `Debug.Log` 별도 추가해 Editor.log로 확인 |
| `unityctl screenshot` Game View 검정 | Unity 백그라운드 시 Game View 렌더 정지 | 기능 무관. Unity 창 포그라운드에서 직접 확인 |

---

## 라이브 맵뷰 (경로 B) — Unity ControlRoom 1:1 (2026-06-16 검증)

기존 Phase 5(정적 PNG 텍스처, 경로 A) 대안. **SLAM 도는 동안 `/map`을 Unity가 실시간 구독**해 MapPanel에 렌더. 2026-06-16 젠지로 PASS.

구현(ControlRoom):
- `Ros/TopicRegistry.cs`: `Map = "/map"`
- `Ros/MapSubscriber.cs`: `OccupancyGridMsg` 구독 → `Texture2D`(RGBA32, Point) 변환. 셀 -1 unknown/0 free/≥65 occupied. 크기 변하면 텍스처 재생성. static `OnMapUpdated` + `LatestMap`. (카메라 구독과 동일 패턴)
- `UI/MapPanelView.cs`: `OnMapUpdated` 구독 → `Image`(ScaleToFit, 절대배치 fill)에 렌더, 힌트 숨김
- `App/ControlRoomApp.cs`: `MapSubscriber` GameObject 코드 부착(씬 YAML 비편집)
- `default_robots.json`: 사용할 로봇을 `robots[0]`으로(=`ConfigureRos`가 endpoint IP 지정)
- `UI/Parts/MapPanel.uxml`: 목업(격자/웨이포인트/로봇점) 제거, 라이브 맵만

검증 체인: 컴파일 OK → `RegisterSubscriber(/map, nav_msgs/OccupancyGrid) OK`(endpoint) → `🟢 first /map frame WxH @res`(Unity). 근거: `docs/evidence/2026-06-16-genji-live-slam-unity-map.md`.

⚠️ 전제: 로봇에 `ros_tcp_endpoint`가 떠 있어야(=`tb3-up`이 bringup+ros_tcp 동시 기동) Unity가 /map을 받음. cartographer /map은 RELIABLE+TRANSIENT_LOCAL, endpoint 구독은 VOLATILE이라 호환(새 메시지 수신 OK).

---

## ROS2 환경변수 모드 통일 (필수)

ROS2 발견 모드는 **bringup·cartographer·ros2 cli·rviz 모두 동일 모드**여야 통신 가능. 섞이면 같은 도메인이라도 발견 실패.

| 모드 | 환경 변수 패턴 | 사용 시점 |
|---|---|---|
| **multicast (SUBNET)** ✅ 권장 | `ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET` | 같은 LAN의 native Linux. **본 프로젝트 기본**. |
| Discovery Server | 위 + `ROS_DISCOVERY_SERVER=<ip>:11811 ROS_SUPER_CLIENT=true` | Discovery 서버 머신이 있고 multicast 안 되는 환경 (Docker, 다른 서브넷 등) |

**검증**: `cat /proc/$(pgrep -f turtlebot3_node)/environ | tr '\0' '\n' | grep -E 'ROS_|RMW_'` — 모든 노드의 env가 같은 모드인지.

오늘(2026-05-29) 책상 매핑 검증 시 bringup이 DS 모드인 채로 cartographer를 multicast로 띄우면 `/scan`은 정상이지만 `/map` 0 publish였음. `urhynix_robot_up.sh`에서 DS 관련 env 제거 후 즉시 작동.

---

## 재현 명령 (2026-05-29 통과 버전)

```bash
. ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh

# 1. 연결 + bringup (12s)
tb3-up

# 2. cartographer (10s)
tb3-slam

# 3. /map 검증
ssh kim@$(tb3-ip) 'bash -c "source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && ros2 daemon stop >/dev/null; ros2 daemon start; sleep 3; timeout 8 ros2 topic hz /map"'

# 4. 매핑 주행 (정적이면 30s 대기, 경기장이면 tb3-teleop 25분)
sleep 30   # or: tb3-teleop

# 5. 맵 저장 (robot 측 ~/maps/)
ssh kim@$(tb3-ip) 'bash -c "source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && mkdir -p ~/maps && cd ~/maps && ros2 run nav2_map_server map_saver_cli -f arena_v1 --ros-args -p save_map_timeout:=20.0"'

# 6. 호스트로 fetch + PNG + Unity scale
tb3-fetch-map arena_v1
tb3-map-to-unity arena_v1
```

---

## 한줄정리

연결 → SLAM → 25분 주행 → 맵 저장 → 평가 → Unity 임포트 → (선택) Nav2 1-waypoint까지 6 Phase. 산출은 `.pgm/.yaml/.png + eval.md` 4종 + Unity 텍스처. **2026-05-29 책상 정적 매핑으로 흐름 통과 검증 완료.** 다음 단계는 다중 waypoint 순찰(SCRUM-10) 또는 박물관 액자 보호 트랙(SCRUM-16).
