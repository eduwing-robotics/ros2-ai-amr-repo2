# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 이 파일만 읽으면 출발 가능. 자세한 건 아래 링크로 들어가면 됨.

**Last updated**: 2026-06-16 (**🟨 Gen.G 센서 스택 정본 갱신 — LDR→온도·레이저·워터펌프, 자동충전독 제외, 시나리오 5종 확정** — Confluence 정본 v18 반영. Gen.G의 조도(LDR)와 불꽃 센서를 제거하고 온도·레이저·워터펌프로 교체. 자동 충전독은 난이도 이유로 제외하고 ArUco 정밀 주차 후 수동 충전 요청으로 대체. **⚠️ 중요 — 현재 코드는 구 LDR 기준**: `LuxSubscriber.cs`, `arduino_bridge.py`, `urhynix-sensor-bringup` 스킬은 여전히 LDR 토픽 및 핀 기반 문서화. 센서 하드웨어 교체 후 토픽명·핀 매핑 정합 필요. 시나리오 5종(침입자/분실품/화재/접촉/배터리) 및 위험등급 SAFE/WATCH/CHECK/DANGER/EVACUATE 정본 다운로드 → `docs/status/DECISION-LOG.md` 2026-06-16 참조. **다음 세션**: ①센서 물리 교체 ②토픽/핀 코드 정합 ③시나리오 통합 시연. **다음 세션 진입**: ①Mac↔젠지 직결 + bootpd(아래 절차) → `ssh kim@192.168.10.50` ②도메인 210이 티원/Unity와 맞는지 확인 ③무선 영구화 원하면 젠지 인터넷 살아있으니 Tailscale 설치(주인님 보류 중). 자산: 메모리 `urhynix-team-wifi-isolation-direct-link` + `project_robot_ip_dynamic` 갱신 + evidence `2026-06-15-genzi-team-wifi-isolation-direct-link.md`. · **세션 종료자**: 김주영) · 이전: 2026-06-10 (**🟩 Mac MPS + T1 RealSense YOLOv8n 라이브 PASS + 영상 끊김 정량 진단 + 자산 5종 영구화** — T1(`192.168.10.250` wlan0, ssh `t1@192.168.10.250`) RealSense D435 → `web_video_server` 8080 MJPEG → Mac `cv2.VideoCapture` → YOLO(mps)로 26.0fps headless / 16fps GUI 추론. 결과 이미지 `test/realsense_yolo_result.jpg`(person 0.89 + keyboard 0.91 + cup 0.86 + tv 0.79 등). **분업 채택**: 라즈베리는 영상 publish만, Mac MPS가 추론. **끊김 정량 진단**: raw 11.27Hz×14.24MB/s=114Mbps → Wi-Fi 65Mbps 초과 원인. compressed 전환으로 라즈베리 CPU 87.5%→0% + 네트워크 -85%. **병렬 다리 3개**: web_video_server 8080 + foxglove_bridge 8765 + ros_tcp_endpoint 10000. **박제 자산**: 🆕 스킬 `robot-ip-detect-fallback` + 🆕 스킬 `robot-camera-stream-diag` + ✏️ `robot-camera-bringup` §C/§D/§E + 함정 #19 + ✏️ 메모리 `project_robot_ip_dynamic.md` + 🆕 `test/detect_realsense.py`. **T1 apt install**: foxglove_bridge 3.2.6 + realsense2_camera 4.57.7 + web_video_server 3.1.0. **다음 세션 진입**: ①T1 IP 재확인(mDNS 깨졌으면 `robot-ip-detect-fallback`) → ②3종 ssh -fn launch (realsense + foxglove + web_video_server) + turtlebot3_bringup → ③Mac venv: `cd test && source .venv/bin/activate && python detect_realsense.py` → ④다음 트랙 후보: 젠지 Pi Camera 동시 추론 / depth 결합 / Unity `/yolo/detections` 통합 / 15Hz+depth off 최적화. **이전(2026-06-09)**: Phase 2.9 시연 PASS 확정 — 자동주차 동작 + 배터리 트렌드 + 동료 인계 + XQuartz. **이전(2026-06-09 2차)**: 하드웨어 crash 진단 + 코드 구조 강화 + 함정 #9/#10. **이전(2026-06-09 1차)**: Phase 2.9 노드 결선 PASS, 함정 8가지. **이전(2026-06-08)**: Phase 2.8 젠지 LDR/PIR Unity 결선 PASS. · **세션 종료자**: 김주영

## 🆕 2026-06-15 — 젠지 재접속: 팀 와이파이 격리 우회 직결 절차

> 팀 전용 ipTIME 와이파이가 **AP isolation(클라이언트 격리)**라 무선으로 로봇 SSH 불가. 무선은 인터넷만 되고 로컬 TCP·공유기관리(`10.1`) 전부 차단. **직결 + bootpd DHCP**로 우회한다. 자세히: 메모리 `urhynix-team-wifi-isolation-direct-link`, evidence `docs/evidence/2026-06-15-genzi-team-wifi-isolation-direct-link.md`.

```bash
# 0) Mac(USB-C↔이더넷 어댑터, en5=USB 10/100 LAN) ↔ 젠지 이더넷 포트 랜선 직결
ifconfig en5 | grep -E "status|inet"          # status: active 확인

# 1) en5를 같은 대역 수동 IP로 (sudo 비번 = Mac 로그인 비번)
sudo networksetup -setmanual "USB 10/100 LAN" 192.168.10.200 255.255.255.0

# 2) bootpd DHCP 서버 설정 (/etc/bootpd.plist) — dhcp_enabled=[en5], 192.168.10.0/24, range .50~.150
#    (PlistBuddy로 작성 — evidence에 전체 명령. 1회 작성 후 재사용 가능)
sudo launchctl enable system/com.apple.bootpd
sudo launchctl load -w /System/Library/LaunchDaemons/bootps.plist

# 3) 5초 내 젠지 lease 확인 → SSH
sudo cat /var/db/dhcpd_leases       # name=kim-desktop ip_address=192.168.10.50 hw=2c:cf:67:...
ssh kim@192.168.10.50               # 키 인증, 비번 fallback 1234
```

- 젠지 현황(2026-06-15): Ubuntu 24.04.4 + ROS2 Jazzy + `~/turtlebot3_ws` + Pi Camera `/dev/video0~19` + 인터넷 OK. **hostname `kim-desktop`, `ROS_DOMAIN_ID=210`**(예전 230), wlan0=`192.168.10.87`.
- ⚠️ 다음 세션 확인: 도메인 210이 티원/Unity와 일치하는지. 무선 영구화 원하면 젠지 인터넷 살아있으니 **Tailscale** 설치(주인님 보류 중).

## 🆕 2026-06-10 late update — T1 Custom YOLO 학습실 정제 루프

- 앱: `scripts/yolo_training/custom_yolo_studio.py`
- 주소: `http://127.0.0.1:8766/?v=hard-negative-20260610-1806-clean`
- T1 fast preview: `http://192.168.10.250:8090/preview.jpg`
- 데이터셋: `datasets/custom_object`
- 학습 결과: `runs/custom_object/**/weights/best.pt`
- 현재 기능: Space 촬영, ROI 자동연사, SAM2/rembg/GrabCut bbox 보정, 검수 화면(`←/→`, `D 삭제`, `Delete/Backspace`, `Esc`), `review_masks` cache, 최신 `best.pt` 자동 로드, `N 오탐 배경 저장`.
- 중요 결정: 배경 오탐은 `.pt` 파일을 직접 정제하지 않는다. `N 오탐 배경 저장`으로 `negative_*.jpg` + 빈 `.txt` hard-negative 샘플을 30~100장 모은 뒤 재학습한다.
- 현재 데이터 품질 주의: 반복 bbox가 많으면 mAP가 높아도 실전 배경 오탐을 숨긴다. 검증셋에는 물건 없는 배경-only 샘플도 넣어야 한다.
- 자세한 근거: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`, `docs/status/DECISION-LOG.md` 2026-06-10 맞춤 YOLO 섹션.

## 🆕 2026-06-10 shutdown note — T1 robot still alive at doc update

- 문서 업데이트 시점 점검:
  - `ping -c 2 -W 1500 192.168.10.250` → 2/2 응답, packet loss `0.0%`.
  - `curl http://192.168.10.250:8090/status` → `{"ok": true}` fresh.
- 결론: 이 문서 업데이트 시점에는 T1 OS/카메라 서버가 아직 살아 있었다. 실제 셧다운 완료로 표시하려면 OS `poweroff` 후 ping 100% loss를 확인해야 한다.
- 안전 셧다운 순서:
  1. ROS/카메라/브릿지 프로세스 정리: `tb3-down` 또는 T1 fallback `pkill -f robot.launch.py/default_server_endpoint/turtlebot3_ros/single_coin_d4/realsense2_camera/web_video_server/foxglove_bridge`.
  2. OS halt: `ssh t1@192.168.10.250 'sudo poweroff'`.
  3. 10~30초 후 `ping -c 2 -W 1500 192.168.10.250`가 100% loss인지 확인.
  4. ping loss 확인 후 TurtleBot 메인 슬라이드 스위치 OFF.
  5. LiPo 분리/충전 상태 기록.
- 정본 절차: `docs/ref/tech/ROS2-ROBOT.md` Safe Shutdown.

---

## 🎯 첫 5분에 읽을 것 (이 3개만)

1. **이 파일** (`docs/status/HANDOFF.md`)
2. `docs/status/PROJECT-STATUS.md` — 한 줄 상태 + 역할 매트릭스
3. `docs/status/DECISION-LOG.md` 가장 아래 5건 — 오늘까지의 결정 흐름

→ 이 3개 다 읽어도 5분 이내. 자세한 SSOT는 필요할 때 들어가면 됨.

---

## 🆕 새 동료 첫 세팅 (Ubuntu/Mac 공통, 머신당 1회)

> 처음 들어온 사람은 이 9단계만 따라가면 로봇과 직접 통신 가능. 자세한 OS별 분기는 [`unity-smoke/README.md`](../../unity-smoke/README.md).

```bash
# 0) 같은 LAN 확인 (필수) — 로봇은 학원 Wi-Fi(codelab_5G)에 wlan0=192.168.0.x, eth0=192.168.10.x.
#    Mac도 192.168.0.x이면 같은 서브넷. 다른 서브넷이라도 학원 라우터가 0.x ↔ 10.x 라우팅하므로 도달 가능.
#    가장 빠른 진입: `ssh urhynix-robot` (mDNS, 같은 서브넷에서만 동작) 또는 ssh kim@192.168.0.x.
#    WSL2는 기본 NAT라 robot 탐색 실패 → mirrored networking 또는 native Ubuntu 권장.
ip -4 addr show | grep -E "192.168.0|192.168.10"   # Ubuntu (둘 중 하나 잡히면 OK)
ipconfig getifaddr en0                              # macOS (0.x 권장)

# 1) 의존성
#    Ubuntu:
sudo apt update && sudo apt install -y expect openssh-client netcat-openbsd jq curl git
#    macOS (brew):
brew install expect jq

# 2) 레포 clone (콜라보레이터 권한 확인 후)
git clone https://github.com/URHYNIX/URHYNIX.git ~/URHYNIX

# 3) helpers source
echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.bashrc     # Ubuntu
echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.zshrc      # macOS

# 4) 자격 증명 분리 (~/.tb3rc, repo 밖에 보관)
cp ~/URHYNIX/scripts/tb3rc.example ~/.tb3rc
chmod 600 ~/.tb3rc
$EDITOR ~/.tb3rc    # TB3_PASSWORD / TB3_VNC_PASSWORD / SUPABASE_ACCESS_TOKEN 채우기

# 5) 새 셸 + SSH 공개키 1회 (이후 비번 prompt 영구 사라짐)
exec $SHELL
tb3-key-setup

# 6) Unity Hub + Editor 6000.0.64f1
#    Ubuntu: https://unity.com/download → UnityHub.AppImage chmod +x → Hub에서 6000.0.64f1 설치
#    macOS:  Unity Hub.dmg → 동일하게 6000.0.64f1 설치
#    설치 후 Hub에서 ~/URHYNIX/unity-smoke 폴더 Add → 첫 Open 시 Library/ 자동 재생성 (5-10분)

# 7) 로봇 부팅 (사람이 메인 스위치 ON) → 30초 대기

# 8) 한 방 풀-기동 + DB 1행 검증
tb3-go            # bringup + ros_tcp + arduino_bridge + verify
sb-tail           # events count + 최근 5건 — PIR 손 흔든 뒤 row 증가 확인
tb3-unity         # Unity Editor 자동 Play → 화면 가운데 한글 패널 LIVE 확인
```

체크포인트:
- `tb3-myip` → Mac IP가 `192.168.0.x`면 robot wlan0와 같은 서브넷 ✅ (eth0(10.x)도 라우팅으로 도달 가능)
- `tb3-ip` → 로봇 IP 1개 반환 ✅ (mDNS 우선 → 실패 시 MAC sweep)
- `ssh urhynix-robot` → 한 줄로 진입 (mDNS, IP-drift zero-touch) ✅
- `tb3-port` → `Connection succeeded` ✅
- `sb-count` → 숫자 응답 ✅ (Supabase token 작동)

문제 발생 시 → `unity-smoke/README.md` 트러블슈팅 표.

---

## 🚀 지금 즉시 해야 할 일 (Top 1) — **하드웨어 점검 후 t1 부팅 검증 + parking_node 5트라이얼 정밀도 평가**

> **2026-06-09 2차 시도에서 t1이 Dynamixel 통신 실패로 crash 발생.** 배터리 부족 또는 케이블 불량이 원인. 다음 세션 첫 5분에 해야 할 액션은 이 표.

### 새 환경 진입점 (한 줄)

```bash
ssh urhynix-robot   # ~/.ssh/config 별칭 (HostName=192.168.10.59, User=kim, IdentityFile id_ed25519). 비번 없이 즉시
# 또는: ssh kim@192.168.10.59
```

robot 안에서 `~/.bashrc`가 ROS2 환경(ros-jazzy + ~/turtlebot3_ws + TURTLEBOT3_MODEL=burger + LDS_MODEL=LDS-03 + OPENCR_PORT=/dev/ttyACM0 + **ROS_DOMAIN_ID=230**)을 자동 source 하므로 즉시 `ros2 launch ...` 가능. (2026-06-02 30→230 통일, 티원과 일치)

### 다음 세션 첫 5분 — 하드웨어 점검 후 t1 부팅 (2026-06-09 2차 시도 결과 반영)

| # | 점검 | 상태 확인 방법 |
|---|---|---|
| 1 | **LiPo 배터리 충전 완료** | 멀티미터로 11.5V 이상 측정, 또는 t1 부팅 후 `cat /sys/class/power_supply/*/uevent \| grep VOLTAGE` |
| 2 | **OpenCR 리셋 버튼 1회 누름** | 리셋 후 USB LED 깜빡임 확인 (약 2초 후 정상) |
| 3 | **Dynamixel 휠 모터 케이블 재연결** | OpenCR 포트 1·2 커넥터를 뽑았다가 다시 끼움 (딸깍 소리 확인) |
| 4 | **t1 전원 OFF → ON** | 부팅 30초 대기 → `ping urhynix-robot.local` 응답 확인 |
| 5 | **turtlebot3_bringup 검증** | `ssh urhynix-robot 'bash -c "source ~/.bashrc && ros2 launch turtlebot3_bringup robot.launch.py"'` → 10초 후 `[turtlebot3_node] Burger is connected` 출력 + **`[DynamixelSDKWrapper] Failed to read` 에러 없는지 확인** |
| 6 | **parking_node 5트라이얼 정밀도** | 별도 터미널에서 `ros2 run aruco_parking parking_node` → 마커 카드를 0.5m 거리에서 천천히 접근 → 5회 반복, 마지막 3회는 10cm 이내 거리에서 停止 성공 여부 기록 |

→ 위 6단계 모두 통과 시 시연 GO 조건 해제.

### 잔여 액션 (구 목록, 참고용)

| # | 액션 | 명령 | 소요 |
|---|---|---|---|
| 1 | `/etc/urhynix.env` SUPABASE_KEY 주입 | `ssh urhynix-robot 'sudo nano /etc/urhynix.env'` → `PASTE_SERVICE_ROLE_JWT_HERE` 자리에 service_role JWT 붙여넣기. 절대 commit 금지 | 1분 |
| 2 | OpenCR firmware 재플래시 (USB micro 케이블 + 부트로더 모드) | 본 evidence §"잔여" 참조 | 5분 |
| 3 | Arduino UNO PIR+LDR 스케치 재플래시 (D2 핀 SSOT 정렬) | Mac에서 `arduino-flash` 스킬 + USB 연결 | 5분 |
| 4 | ✅ **Pi Camera Module v2 (Sony IMX219, 8MP) user-space 풀 빌드 PASS** — libcamera Pi fork v0.7.1 + rpicam-apps v1.12.0 6분만에 빌드. `rpicam-still` 1920×1080 JPG + `rpicam-vid` 1280×720@30Hz × 5초 H.264 캡처 검증 통과. 함정 3건(rpicam-apps 미제공/libepoxy-dev 누락/libav API mismatch) 모두 `scripts/build-picamera.sh`에 반영. evidence: `docs/evidence/2026-06-01-rpi-camera-imx219-source-build.md`. 잔여: ROS2 camera_ros 토픽 발행 (W2). | ~~30~60분~~ **완료** |
| 5 | bringup `/scan` `/odom` 검증 (LiPo ON 필요) | `ssh urhynix-robot 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && ros2 launch turtlebot3_bringup robot.launch.py'` | 10분 |
| 6 | ✅ **Robot2 RealSense D435 ROS2 setup PASS** | Robot2 `t1@192.168.0.250`에서 `v4l-utils`, `ros-jazzy-realsense2-camera`, `ros-jazzy-realsense2-description`, `ros-jazzy-librealsense2` 설치 완료. `t1`을 `video,plugdev` 그룹에 추가. `ros2 launch realsense2_camera rs_launch.py align_depth.enable:=true pointcloud.enable:=true` PASS. color/depth/aligned depth 모두 약 30Hz. **D435, IMU 없음, Serial 254522075185, FW 5.17.0.10**. Evidence: `docs/evidence/2026-06-01-robot2-realsense-d435-ros2-smoke.md` | 완료 |

### 그 다음 — arena_v2 매핑 (가벽 보강 후)

이전 매핑 실패 진단(`라이다 높이 > 가벽 높이`)은 그대로 유효. 옵션 A(물리 보강) 추천. 자세히 ↓ "가벽 높이 측정 + 보강" 섹션.

---

## 📌 (이전) 가벽 높이 측정 + 보강 결정 (arena_v2 매핑 전 필수 선행)

### 배경: 매핑 실패의 진짜 원인은 "라이다 높이 > 가벽 높이" (회의록 5/29)

- 어제 evening에 작성한 "회전만의 한계" 진단을 **정정함**.
- **진짜 원인**: TurtleBot3 Burger의 LDS-03 LiDAR 스캔 평면(~192mm 지상고)이 경기장 가벽 상단보다 높음 → LiDAR가 가벽을 over-shoot.
- 회전을 더 해도, 하이브리드(stop & rotate)를 해도 **수직 차원 문제는 해결 안 됨**.
- 근거: Confluence 회의록 page `3932161` 김주영 발언 — "라이다높이보다 가벽이낮아서 벽 매핑실패. 하지만 좌표값읽기 성공".
- 좌표값(odom·TF·map 1:1)은 그대로 유효 → Unity 디지털 트윈 좌표 매핑은 가능.

### 결정 분기 (다음 매핑 전 사람이 결정)

| 옵션 | 절차 | 시간 | 위험 |
|---|---|---|---|
| **A. 가벽 물리 보강** | 가벽 상단에 종이/테이프/박스로 200mm 이상으로 올림 | 5분 | 가장 단순. 시연 외관 약간 손상 |
| **B. 카메라 vision fallback** | YOLO에 가벽 클래스 추가 학습 (임현찬 라인) | 수일 | 발표 일정 위험 |
| **C. 가벽을 obstacle 아니라 "보호 영역 경계 마커"로 재정의** | Unity 디지털 트윈 + DB 좌표만 사용, Nav2 cost map 미반영 | 1시간 | Nav2가 가벽 밖으로 갈 위험 → 출동 시뮬 시 주의 |
| **D. LiDAR 더 낮게 마운트** | Burger 구조 개조 | 수시간 | 비추천, 안정성 손상 |

→ **A 추천** (시간/리스크/검증성 모두 최선). 가벽 보강 후 정상 매핑 가능.

### A 선택 시 실행 흐름

```bash
# 0) 가벽 실측 (사람 작업)
줄자로 가벽 상단 지상고 측정 → 200mm 이상으로 종이/테이프 보강 → 측정값을 eval.md에 기록

# 1) 출발 (DHCP IP 변경 가능)
bash .claude/skills/ip-drift-resync/resync.sh
. ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh
tb3-up && tb3-slam

# 2) 별도 터미널: tb3-teleop → 회전만 2~3바퀴 (가벽 보강됐으면 5바퀴 불필요)
#    또는 하이브리드 (회전 + 작은 이동)

# 3) 저장 + Unity 임포트
tb3-slam-save arena_v2
tb3-fetch-map arena_v2
tb3-map-to-unity arena_v2

# 4) 정량 평가
python3 .claude/skills/map-quality-eval/eval.py arena_v2
# → occupied ≥ 5% AND 가벽 연결성 OK 면 통과
```

### W2 진입은 매핑 통과 후 (SCRUM-10 Nav2 베이스라인)

- arena_v1 그대로 W2 진입은 비추천 — 가벽 detect 안 됨 = Nav2 cost map 부정확 = 시연 실패 위험.

### 사전 점검 (2026-06-01 부트스트랩 후 — 다음 세션 출발 시 재검증)

| 항목 | 2026-06-01 최신 |
|---|---|
| 로봇 hostname | `urhynix-robot` (mDNS — IP drift-proof 진입점) |
| 로봇 wlan0 IP | `192.168.0.82` (학원 Wi-Fi codelab_5G, Mac과 같은 망) |
| 로봇 eth0 IP | `192.168.10.59` (랜선 꽂으면 잡힘, 평소엔 안 꽂아도 됨) |
| Mac IP | `192.168.0.71` (학원 LAN) |
| 배터리 | (재부팅 후 미측정 — 다음 세션에 LiPo ON 시 확인) |
| 디스크 | 128GB SD, rootfs 117G 중 8.6G 사용 (8%) — 여유 충분 |
| `~/turtlebot3_ws/build` | 6/1 신규 (ld08_driver + ros_tcp_endpoint colcon build OK) |
| Unity scene rosIP | `urhynix-robot.local` (mDNS — IP 바뀌어도 자동 follow) |
| `scripts/tb3.sh` | TB3_HOSTNAME + mDNS 우선 추가 (IP-drift zero-touch) |
| `/etc/urhynix.env` | ✅ 6/1 신규 작성 (640 root:kim, **SUPABASE_KEY=PASTE_... 빈 상태**) |
| Arduino/OpenCR/LDS-03 udev | ✅ `/dev/tb3_arduino` / `/dev/tb3_opencr` / `/dev/tb3_lidar` 모두 활성 |
| Arduino 스케치 | ✅ 살아있음 ("=== PIR + LDR Test === / Warming up..." 시리얼 출력) |

### 주의

- **`~/turtlebot3_ws/build` 절대 지우지 말 것** (install/setup.bash hook 의존)
- **multicast 모드만 사용** (ROS_DISCOVERY_SERVER 제거됨) — bringup·cartographer 모두 자동 발견
- **로봇 디스크 1.1GB** (94%). 추가 SD 정리 필요 시 `tb3-disk-cleanup`
- 로봇 dpkg trigger 4/4 commit 완료 + ldconfig 부수 미완은 영향 없음

### 별도 트랙 (Mac 통신 영역)

- macOS Docker host networking은 inbound NAT 미라우팅 → ROS2 분산 부적합 (오늘 진단)
- Multipass macOS Apple Silicon QEMU hang (오늘 발견)
- UTM QEMU bridged 좀비 lock 에러 (오늘 발견)
- 향후 Mac에서 cartographer 띄울 필요 있으면 **OrbStack** 또는 **동료 Ubuntu native**가 정답 (`MAC-DOCKER-ROS2-PLAYBOOK.md §6.5` 참조)

### 현재 상태 (출발점)

| 항목 | 상태 |
|---|---|
| Robot bringup | ✅ `/scan /odom /tf` 13 topic publish |
| Robot 워크스페이스 | ✅ 8 패키지 클린 재빌드 (sequential) |
| Robot SD 디스크 | ⚠️ 1.1GB 남음 (94%). `build/` 절대 지우지 말 것 |
| Robot dpkg trigger | ⚠️ 4/4 commit 완료지만 ldconfig trigger 미완. 영향 없음 |
| Mac Docker Desktop 4.34+ host network | ✅ 활성 (컨테이너 ping robot 통과) |
| `robotis/turtlebot3:jazzy-pc-latest` 이미지 | ✅ 5GB pull, cartographer/nav2/map-server 포함 |
| `urhynix_dds` (Fast DDS Discovery Server) 컨테이너 | ✅ 11811 listen (`docker logs urhynix_dds`) |
| Robot `ROS_DISCOVERY_SERVER=192.168.0.104:11811` 환경 export | ✅ |
| Robot → Mac UDP 11811 nc 통과 | ✅ |
| DS log에 robot 접속 메시지 | ❌ |
| Mac container `ros2 topic list`에 robot 토픽 | ❌ |

### 다음 시도 (우선순위)

1. **컨테이너에서 `tcpdump`로 inbound UDP 11811 실제 수신 확인** — `apt install -y tcpdump` 후 `tcpdump -n -i any 'udp port 11811'`
2. **Fast DDS XML 강제 unicast peer 설정** — `FASTDDS_DEFAULT_PROFILES_FILE` env로 robot IP 명시
3. **Cyclone DDS 양쪽 설치 + XML unicast peer** — robot에 `ros-jazzy-rmw-cyclonedds-cpp` 추가 설치 (디스크 1.1GB 빡빡)
4. **`osrf/ros:jazzy-desktop` 다른 base 이미지 시도** — robotis 이미지 내부 DDS 설정 검증 우회
5. **동료 Ubuntu native fallback** — Docker 우회, multicast 정상 작동 기대

### 검증 명령 (재현)

```bash
. ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh
tb3-ip                              # robot IP 확인
tb3-up                              # bringup + ros_tcp 재기동
docker logs urhynix_dds             # DS 작동 확인
tb3-docker-topics                   # 컨테이너에서 robot 토픽 보이나
```



| # | 단계 | 담당 | 상태 |
|---|---|---|---|
| 0 | ~~DB 선정 + 마이그레이션~~ | 김주영 | ✅ 완료 (Supabase `ueupkrxwybuuqxflstvg`, 4테이블 + seed) |
| 1 | **로봇 메인 스위치 ON** (라즈베리파이 셧다운 상태) → 30초 부팅 대기 | 사람 (현장) | 🟥 대기 |
| 2 | `kim@192.168.0.138`에서 **`/etc/urhynix.env`** 작성 (service_role 키 주입) — **2026-05-28 작성 완료** | 박태진 | ✅ done |
| 2.5 | **`tb3-key-setup`** 한 번 (Mac/Ubuntu 머신마다 1회, 이후 비번 prompt 영구 사라짐) | 머신 주인 | 머신당 1회 |
| 3 | **`tb3-go`** (Mac/Ubuntu) — bringup + ros_tcp + arduino_bridge + 검증까지 한 방 | 박태진 | 2.5단계 후 |
| 4 | PIR 손 흔들기 → `sb-tail` 로 `events` row +1 확인 → **Day-1 완전 PASS** 🎉 | 다 같이 | 3단계 후 |
| 5 | LDR 가리기 (어두움 만들기) → `sb-dark` 로 event_type='dark' row +1 확인 | 다 같이 | 4단계 후 (선택) |

### 2단계: `/etc/urhynix.env` 작성 절차

```bash
tb3-ssh   # 또는: ssh kim@$(tb3-ip)
sudo tee /etc/urhynix.env >/dev/null <<'EOF'
SUPABASE_URL=https://ueupkrxwybuuqxflstvg.supabase.co
SUPABASE_KEY=<paste service_role legacy JWT — DO NOT commit>
URHYNIX_SESSION_ID=00000000-0000-0000-0000-000000000001
URHYNIX_ROBOT_ID=tb3_1
EOF
sudo chmod 600 /etc/urhynix.env
```

→ service_role JWT는 작업자 본인의 Supabase 대시보드 또는 어제 발급된 access token으로 `supabase projects api-keys --project-ref ueupkrxwybuuqxflstvg`로 다시 받기. 절대 GitHub/Slack/HTML 보드에 박지 말 것.

### 4단계: 검증 명령

```bash
# Supabase 대시보드에서:
#   Table Editor → events → ts desc 정렬 → MOTION 새 row 확인
# 또는 SQL editor에서:
select id, ts, event_type, severity, x, y, theta, raw_payload->>'label' as label
from public.events
where session_id='00000000-0000-0000-0000-000000000001'
order by ts desc limit 10;
```

### 0단계 외 독립 진행 가능 (Day-1 잔여)

핀 매핑 정렬 잔여 1건: 현재 검증 코드는 PIR=D7·LED=D2지만 SSOT는 PIR=D2. **PIR=D2 / LED=D8(또는 D11)**로 재배선 + 스케치 갱신 후 재플래시 (`arduino-flash` 스킬 그대로 재사용). LDR=A0은 이미 일치. DB 선정과 무관하게 진행 가능.

```bash
# (0단계 결정 후 2단계 검증용 예시)
# 라즈베리파이에서:
ls -l /dev/tb3_arduino          # ttyACM1 자동 심링크 확인
python3 - <<'PY'
import serial, time
s = serial.Serial('/dev/tb3_arduino', 9600, timeout=1); time.sleep(2)
while True:
    line = s.readline().decode('utf-8', errors='replace').strip()
    if line.startswith('[MOTION]'):
        # → 여기서 DB insert (선정된 DB 클라이언트로)
        print('PIR EVENT', line)
PY

# 1건 이상 row가 보이면 Day-1 완전 PASS, W2 진입 OK.
```

---

## 📊 현재 상태 (2026-05-27 21:00 기준)

| 영역 | 상태 |
|---|---|
| 방향 합의 | ✅ 완료 (다중 경비 로봇 디지털 트윈) |
| SSOT 9개 | ✅ 갱신 완료 — 2026-05-28 박물관/미술관 액자 보호 컨셉, LiDAR/PIR 외부자 판단 반영. 좌표·사진·영상·사운드 저장은 실제 DB 미적용 상태의 SCRUM-23 확장 예정안 |
| HTML 보드 8개 + 단일 번들 (465KB) | ✅ 갱신 완료 |
| Jira 18개 티켓 | ✅ 재작성 + 6개 Day-1 본문 |
| Confluence 4페이지 | ✅ 모두 v최신 |
| 신규 스킬 2개 (`ssot-board-sync`, `decision-broadcast`) | ✅ 등록 |
| Day-1 작업 진행 | ⏳ 진행 중 (3팀 동시) |
| Day-1 통합 검증 | 🟡 절반 PASS (PIR + LDR(A0) + 시리얼 ✅ 2026-05-28 / DB 단계 대기) |
| Arduino PIR + LDR 플래시 자동화 | ✅ `arduino-cli` 1.5.0 + `sketches/pir_led/` 검증 (`MOTION`/`CLEAR` + `[LDR] A0=...` 로그) |
| TurtleBot ROS2/RViz/Unity smoke | ✅ 성공 기록 완료 |
| TurtleBot helper aliases | ⚠️ Mac 완료, robot-side 실행은 SSH timeout으로 대기 |
| 팀 Slack 채널 봇 권한 | ⚠️ 채널 `C0B5Q43A27R`에 봇 초대 필요 |

---

## 🧭 Day-1 작업 분담 (오늘 진행 중)

- **김주영 + 임현찬** → Pi Camera 스트림 + DB 연결 테스트 (SCRUM-19, 14)
- **박태진** → Arduino + PIR → 시리얼 → DB 한 줄 통과 (SCRUM-13, 14)
- **김선일** → Unity 관제 UI 기능 명세 문서화 (SCRUM-9)

---

## ⏭️ Day-2 (W2) 진입 시 첫 작업

Day-1 PASS 확인 후 다음 액션:

1. SCRUM-10 (tb3_1 SLAM/Nav2 베이스라인) 시작 — 임현찬·김선일
2. SCRUM-16 (박물관/미술관 실내 트랙·액자형 보호 대상 waypoint 측정) 시작 — 박태진·임현찬
3. 부족 센서 발주: 소리·불꽃 (키트 미포함분)
4. OpenCR 5V 패드 위치 실측 + 점퍼 배선 도면 — 임현찬·김주영
5. 김선일 Unity 기능 문서 → SCRUM-11/22 분해, 보호 대상 상태 패널은 SCRUM-21/23과 연결

---

## 🔗 외부 시스템 진입점

| 시스템 | 페이지/ID | 역할 |
|---|---|---|
| **Confluence 327681** | [기획안 (UR HYNIX) v11](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/327681) | **외부 정본 SSOT** |
| Confluence 1605636 | [역할 분배 보드](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1605636) | 5×4 매트릭스 |
| Confluence 1048633 | [2026-05-27 회의록](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1048633) | Day-1 분담 |
| Confluence 1540099 | [브레인스토밍 마인드맵](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1540099) | 방향 전환 근거 |
| Confluence 2555905 | [상세 UR (사용자 요구사항) v3](https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/2555905) | 40 UR + 5 NFR |
| Jira | [SCRUM-7 에픽](https://jason1127.atlassian.net/browse/SCRUM-7) | 18 카드 부모 |
| Jira | [SCRUM 보드](https://jason1127.atlassian.net/jira/software/projects/SCRUM/boards/1) | 칸반 |
| Slack | 채널 `C0B5Q43A27R` (⚠️ 봇 초대 필요) | 팀 소통 |
| GitHub | [URHYNIX/URHYNIX](https://github.com/URHYNIX/URHYNIX) | 코드 |

---

## 📦 오늘 만든 자산 (다음 세션도 활용)

| 자산 | 위치 | 용도 |
|---|---|---|
| 단일 HTML 보드 | `docs/dev-plan-bundle.html` (465KB) | 더블클릭으로 7페이지 다 열림. 팀 공유용 |
| 7페이지 HTML | `docs/dev-plan*.html` | 페이지별 분리 보기 |
| 역할 매트릭스 PNG | `docs/whiteboards/role_matrix.png`, `role_graph.png` | Confluence/Whiteboard 첨부용 |
| 번들 빌더 | `docs/whiteboards/build_bundle.py` | HTML/번들 갱신 후 재빌드 |
| PNG 생성기 | `docs/whiteboards/generate_role_board.py` | 역할 변경 시 PNG 재생성 |
| 스킬 `ssot-board-sync` | `.claude/skills/ssot-board-sync/SKILL.md` | SSOT ↔ HTML 동기화 |
| 스킬 `decision-broadcast` | `.claude/skills/decision-broadcast/SKILL.md` | 결정 → 5채널(DECISION-LOG/SSOT/HTML/Jira/Slack) 동기화 |
| 스킬 `arduino-flash` | `.claude/skills/arduino-flash/SKILL.md` | Arduino UNO 4종 센서 GUI-less 플래시 파이프라인 (compile→upload→serial verify) |
| 표준 PIR+LDR 스케치 | `sketches/pir_led/pir_led.ino` | HW-740 PIR(D7) + LED(D2) + LDR(A0, 10kΩ 분압) 합본. 워밍업·엣지트리거·2초 주기 LDR 보고·`[LDR] A0=` 라벨 (소리/불꽃 복제 베이스) |
| TurtleBot live smoke evidence | `docs/evidence/2026-05-27-live-turtlebot-ros-rviz-unity-smoke.md` | ROS2/RViz/ROS-TCP/Unity 미니 UI 성공 경로와 재현 명령 |
| TurtleBot env check evidence | `docs/evidence/2026-05-27-unity-ros2-turtlebot-env-check.md` | Mac/Unity/ROS2/참고 repo 환경 점검 결과 |
| 스킬 `urhynix-turtlebot-unity-ros2-success-pattern` | `/Users/family/.codex/skills/urhynix-turtlebot-unity-ros2-success-pattern/SKILL.md` | TurtleBot3 Burger → ROS2 → RViz → ROS-TCP → Unity smoke 재현 패턴 |
| Mac TurtleBot helpers | `/Users/family/.zshrc` | `tb3-ip`, `tb3-ssh`, `tb3-vnc`, `tb3-port`, `tb3-unity`, `tb3-help` |
| 경기장 1차 매핑 evidence | `docs/evidence/maps/arena_v1/{pgm,yaml,png,eval.md}` | 회전만 5바퀴 매핑 결과 + 픽셀 통계 + 시각 검증 + 재현 명령 + 다음 매핑 권장 (`eval.md`) |
| Unity Maps Assets | `unity-smoke/Assets/Maps/arena_v1.{png,yaml}` + `desk_static_v1.*` | Unity Plane 텍스처용 PNG + scale 계산 yaml. `tb3-map-to-unity`가 자동 복사 |
| 스킬 `map-quality-eval` | `.claude/skills/map-quality-eval/{SKILL.md,eval.py}` | 매핑 직후 픽셀 통계 + use case go/no-go + eval.md 자동 생성 (백업 포함). 2026-05-29 arena_v1 dry-run 검증. one-liner: `python3 .claude/skills/map-quality-eval/eval.py <map_name>` |
| 스킬 `ip-drift-resync` | `.claude/skills/ip-drift-resync/{SKILL.md,resync.sh}` | DHCP IP 변경 시 Unity Scene + Script + known_hosts 일괄 동기화. Unity 자동 save back 함정 자동 회피 (Editor 종료→patch→재시작 순). one-liner: `bash .claude/skills/ip-drift-resync/resync.sh [new_ip]` |

---

## 🛠️ 다음 세션 출발 명령 (체크리스트)

```bash
# 1. 현재 git 상태 확인
git status

# 2. 단일 번들 최신인지 (필요 시 재빌드)
python3 docs/whiteboards/build_bundle.py

# 3. HTML 파싱 OK 확인
python3 -c "
from html.parser import HTMLParser
import glob
for f in sorted(glob.glob('docs/dev-plan*.html')):
    HTMLParser().feed(open(f).read())
print('All HTML OK')
"

# 4. 옛 방향 잔재 0건 확인
grep -rn '/turtlebot/\|LiDAR only vs\|expansion plate' docs/ref docs/status docs/dev-plan*.html 2>/dev/null | grep -v DECISION-LOG
# 0건이면 OK

# 5. Day-1 통합 검증 (Top 1 작업)
# 5a. Arduino 보드/스케치 살아있는지 (PIR 절반 회귀 검증)
arduino-cli board list  # /dev/cu.usbmodemNNNN가 Arduino UNO로 잡혀야 함
# 필요 시 30초 시리얼 캡처:
# stty -f /dev/cu.usbmodem1101 9600 cs8 -cstopb -parenb -echo raw
# (cat /dev/cu.usbmodem1101 & CAT_PID=$!; sleep 30; kill $CAT_PID 2>/dev/null) | head -40
# 5b. DB 한 줄 통과 확인:
# psql -c "SELECT * FROM events ORDER BY ts DESC LIMIT 5;"

# 6. TurtleBot live smoke 재현/복구 출발점 (필요 시)
source ~/.zshrc
tb3-help
tb3-ip
tb3-ssh

# 로봇 SSH 접속 후, robot-side helper 설치가 아직 안 끝났다면
python3 /tmp/install_tb3_helpers.py
source ~/.bashrc
tb3-help
```

---

## 🚨 미해결 이슈

- ~~DB 미선정~~ → ✅ **해소 (2026-05-28)**: Supabase `ueupkrxwybuuqxflstvg` 잠금. DECISION-LOG "DB 선정 완료".
- ~~로봇 셧다운~~ → ✅ **해소 (2026-06-01)**: 신규 128GB SD로 풀 부트스트랩 완료. `ssh urhynix-robot` 한 줄 진입.
- **🟥 `/etc/urhynix.env` SUPABASE_KEY 비어있음 (2026-06-01)** — `PASTE_SERVICE_ROLE_JWT_HERE` 자리. 다음 세션 첫 1분에 채워야 Supabase row insert 작동.
- ~~mDNS `.local` 안 잡힘~~ → ✅ **해소 (2026-06-01 오후)**: 학원 Wi-Fi(codelab_5G) 추가로 wlan0=192.168.0.82 (Mac과 같은 망) → mDNS multicast 정상. `ssh urhynix-robot` = `urhynix-robot.local` resolve.
- ~~LAN sweep robot 못 찾음~~ → ✅ **해소**: wlan0가 Mac과 같은 192.168.0.x 망. ARP broadcast 직접 도달.
- ~~LAN 케이블 위치 주의~~ → ✅ **해소**: Wi-Fi 영구 추가됨. 랜선 없이도 자동 무선 연결. (단 codelab_5G 비번 발표 후 변경되면 다시 박아야 함)
- ~~Unity rosIP / helper IP hardcoded → IP 변경 시 `ip-drift-resync` 스킬 호출 필요~~ → ✅ **해소 (2026-06-01 오후)**: Unity Scene/Script rosIP를 `urhynix-robot.local` (mDNS) 로 박음 + `scripts/tb3.sh`에 `TB3_HOSTNAME` + mDNS 우선 시도 추가. **이후 IP 변경 시 zero-touch** (`ssh`/`tb3-ip`/Unity 모두 자동 follow). `ip-drift-resync` 스킬은 안전망으로만 남음. 자세히: `docs/evidence/2026-06-01-new-sd-128gb-ros2-jazzy-bootstrap.md` §"IP-drift zero-touch 화".
- **`/etc/urhynix.env` 미작성** — 로봇 부팅 직후 한 번만 (service_role JWT 주입). 코드 commit 절대 금지.
- **팀 Slack 채널 봇 권한 부족** — 채널 `C0B5Q43A27R`에 Claude 봇 초대 필요. 그때까지 결정 공지는 본인 DM으로만 가능.
- **TurtleBot helper 설치 마무리 대기** — Mac helper는 `/Users/family/.zshrc`에 반영 완료. Robot helper installer는 `/tmp/install_tb3_helpers.py`까지 복사됐으나, teardown 이후 `192.168.0.138:22` SSH가 timeout되어 원격 실행은 미검증. 로봇 전원/네트워크가 돌아오면 위 `python3 /tmp/install_tb3_helpers.py` 실행으로 마무리. (2026-05-28 재접속 확인 — 다음 세션에서 즉시 실행 가능)
- **경기장 Wi-Fi 대역 변경 가능성 (2026-05-29)** — robot DHCP IP가 192.168.0.x 아니면 `scripts/tb3.sh`의 `TB3_LAN_CIDR='192.168.0'` 수정 필요. 또는 휴대폰 핫스팟 SSID/PW를 robot이 이전에 연결했던 Wi-Fi와 동일하게 설정 (가장 단순). 자세히: `docs/ref/ARENA-DEPLOYMENT-CHECKLIST.md` §🚨.
- **Unity rosIP 매 세션 수동 (2026-05-29)** — 어제 evening에 `RosSmokeDashboard.cs:10` + `SampleScene.unity:151` 둘 다 `.33`으로 일시 패치 (Inspector 수동 입력 우회). DHCP 또 바뀌면 두 파일 같이 재패치. 개선 후보: `tb3-unity-set-ip <ip>` helper (sed로 두 파일 일괄 patch, `tb3-ip` 결과 자동 주입) — 미실행.
- **arena_v1 매핑 실패 — 가벽 높이 < LiDAR 스캔 평면 (2026-05-29 late evening, 회의록 기반 정정)** — 회전 한계가 아니라 수직 차원 문제로 진단 정정. **다음 세션 첫 결정**: 가벽 높이 측정 + 옵션 A(물리 보강) / B(vision YOLO 학습) / C(보호 영역 경계 마커 재정의) / D(LiDAR 마운트 변경). A 추천. 자세히: `docs/evidence/maps/arena_v1/eval.md` + DECISION-LOG "매핑 실패 진단 정정".
- **`scripts/tb3.sh` helper의 RViz config 경로 오류 (2026-05-29 evening)** — `tb3-rviz` 함수는 `$HOME/turtlebot3_ws/src/turtlebot3/turtlebot3_cartographer/rviz/tb3_cartographer.rviz`를 가리키지만 실제 경로는 `/opt/ros/jazzy/share/turtlebot3_cartographer/rviz/tb3_cartographer.rviz`. 어제 SLAM 세션에서는 직접 ssh로 우회 실행함. 다음 세션에서 helper 수정 1줄.
- **Arduino PIR 핀 D7→D2 정렬 미실행** — `sketches/pir_led/pir_led.ino` 코드 D7 ↔ SSOT/DECISION-LOG D2 불일치. SLAM과 무관하므로 경기장 출동에 영향 없음. `arduino-flash` 스킬로 재플래시 1회 필요 (선택).
- **🟥 RealSense 카메라 D435 확정 + Mac streaming 차단 (2026-06-01)** — 주인님 손에 있는 건 D435i가 아니라 **D435** (Product ID `0B07`, Serial `254522075185`, FW `5.15.1.55`, **IMU 없음**). Mac에서 `sudo rs-enumerate-devices` verbose는 PASS지만 `rs-hello-realsense` Frame timeout 15s. 원인: brew formula 빌드 옵션 누락(`HWM_OVER_XU`/`FORCE_RSUSB_BACKEND`) + macOS Tahoe(26) 공식 미지원. 결정: **Pi4 이전** (잔여 액션 #6). 박물관 매핑 계획은 VIO 폐기만 빼고 95% 살아있음. 자세히: `docs/evidence/2026-06-01-realsense-d435-mac-sdk-smoke.md` + DECISION-LOG 2026-06-01 항목.
- (그 외 미해결 결정 없음)

---

## 📜 한줄정리

신규 128GB SD에 Ubuntu 24.04.4 + cloud-init 사전설정 + SSH 키 인증 + ROS2 Jazzy 풀 스택(turtlebot3 메타 / cartographer / nav2 / ld08_driver / ros_tcp_endpoint) **한 세션에 완전 부트스트랩 완료**. `ssh urhynix-robot` 한 줄 진입. 다음 세션 첫 5분은 `/etc/urhynix.env` SUPABASE_KEY 주입 + OpenCR/Arduino 재플래시 + bringup 검증 → 그 다음 가벽 보강 + arena_v2 매핑.

---

## 🔁 HANDOFF 갱신 규칙

이 파일은 **세션 종료 시마다** 갱신한다:
1. 첫 5분에 읽을 것 (변경 거의 없음)
2. 지금 즉시 해야 할 일 Top 1 (매번 갱신)
3. 현재 상태 표 (매번 갱신)
4. 미해결 이슈 (해결 시 제거, 새 이슈 시 추가)
5. Last updated 갱신
