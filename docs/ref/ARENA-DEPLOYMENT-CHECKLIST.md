# 경기장 출동 체크리스트 — URHYNIX TurtleBot3 SLAM/Nav2

> 경기장(실외→실내 이동) 1회 출동 전 30분 안에 가방을 닫을 수 있도록 만든 체크리스트.
> 매 출동 전 처음부터 끝까지 한 번 훑는다. 빠진 항목 발견 시 이 문서에 추가.

## 🎒 하드웨어 (가방)

### 로봇 본체
- [ ] TurtleBot3 Burger 본체 (메인 스위치 OFF)
- [ ] LiDAR LDS-03 마운트 잠금 확인 (M3 볼트 4개)
- [ ] OpenCR USB-A↔Micro 케이블 (예비 1개)
- [ ] Arduino UNO R3 + USB-A↔B 케이블 (예비 1개)
- [ ] 배터리 LiPo 풀충전 확인 — 11.1V 3S 11.1Ah 권장 (잔량 표시기 점등 확인)
- [ ] 예비 LiPo 1개 (운영 시간 ≥ 1h 요구 시)
- [ ] LiPo 가방 (충돌·발열·인화 차단)

### 호스트 머신
- [ ] 노트북 (Mac 또는 Ubuntu) 풀충전
- [ ] 전원 어댑터 + 전원 연장선
- [ ] USB-C 도크 (Ubuntu) 또는 USB-A 허브 (Arduino 직결용)

### 네트워크
- [ ] 무선 공유기 (백업) — 경기장 Wi-Fi가 같은 LAN인지 사전 확인 못 했을 때
- [ ] 휴대폰 핫스팟 (백업의 백업, `192.168.0.0/24` 매칭되도록 SSID 설정)
- [ ] 짧은 이더넷 케이블 (공유기 ↔ 노트북, 디버깅용)

### 측정 도구
- [ ] 줄자 5m × 1
- [ ] 메모지 + 펜 (현장 경기장 치수 적기)
- [ ] 휴대폰 (사진/영상, Nav2 도착 위치 측정)

## 💻 소프트웨어 (사전 확인)

### 호스트 머신
- [ ] `source ~/URHYNIX/scripts/tb3.sh` 작동 확인 → `tb3-help` 출력
- [ ] `~/.tb3rc`에 TB3_PASSWORD / TB3_VNC_PASSWORD / SUPABASE_ACCESS_TOKEN 존재
- [ ] `tb3-key-setup` 1회 완료 (이전 세션에서 했으면 skip)
- [ ] Unity Hub + Editor `6000.0.64f1` 설치 + `unity-smoke` 프로젝트 Open 1회
- [ ] `python3 -c "from PIL import Image, yaml" 2>&1` 통과 (pgm→png + yaml 파싱용)
- [ ] git clone 최신 + `git pull origin main`

### 로봇 측 (네트워크 가능한 곳에서 사전 점검)
- [ ] `tb3-pkg-check` — 4개 패키지 OK (turtlebot3-cartographer, turtlebot3-navigation2, nav2-map-server, teleop-twist-keyboard)
- [ ] `tb3-disk` — SD 여유 ≥ 800MB. 부족하면 `tb3-disk-cleanup` (200MB+ 회복)
- [ ] `~/turtlebot3_ws/install/turtlebot3_bringup/share/...` 살아있음 (`build/` 지운 적 없는지)
- [ ] `tb3-go` — bringup/ros_tcp/arduino_bridge tmux 3개 OK
- [ ] `urhynix_robot_up.sh`에 `ROS_DISCOVERY_SERVER` 없음 확인 (multicast 모드)
- [ ] `/dev/tb3_arduino` udev symlink 살아있음 (Arduino USB)
- [ ] `tmux ls` 모두 정리 (`tb3-down` 후 출동)

### 자격 증명
- [ ] Supabase service_role JWT 가용 (`tb3-ssh` 후 `cat /etc/urhynix.env` 확인)
- [ ] Supabase Access Token (sbp_…) 만료일 확인

## 📋 현장 도착 후 첫 10분

1. **위치 선정**: 평탄한 바닥, LiDAR 시야 반경 3.5m 내 작은 장애물(의자 등) 있어야 매핑 좋음
2. **메인 스위치 ON** → 30초 대기
3. **노트북을 같은 Wi-Fi에 연결** → `tb3-myip` 결과가 `192.168.0.x`인지 확인
4. **`tb3-ip`** → 로봇 IP 응답
5. **`tb3-go`** → 5채널 LIVE 확인 (선택: `tb3-unity`로 Unity 대시보드)
6. **줄자로 경기장 치수 측정** (가로 W m × 세로 H m) → `eval.md` 기록
7. **SLAM 시작**: `tb3-slam` → 5초 대기 → `ros2 topic hz /map` 확인
8. **매핑 주행**: `tb3-teleop`, 천천히 (0.10 m/s), 한 방향 루프 + 출발점 복귀
9. **맵 저장**: `tb3-slam-save arena_<지명>_v1` + `tb3-fetch-map`
10. **Unity 임포트**: `tb3-map-to-unity arena_<지명>_v1` → 출력된 scale 그대로 인스펙터 입력
11. **선택**: Nav2 1-waypoint 베이스라인 (`tb3-nav2`) 검증 + 줄자로 도착 오차 측정

## 🚨 비상 매뉴얼

- **로봇 통신 끊김** → `tb3-down`, 라즈베리파이 재부팅(전원 ON/OFF), `tb3-go` 재시작
- **SSH 응답 정지 (load avg ≥ 10)** → RAM OOM + SD swap thrash 가능. 메인 스위치 OFF→5초→ON. 부팅 후 `tb3-disk-cleanup`으로 200MB+ 회복.
- **`/map` publish 0 (`/scan`은 정상)** → bringup·cartographer ROS 모드 불일치. `urhynix_robot_up.sh`에서 `ROS_DISCOVERY_SERVER` 라인 제거 → `tb3-down`→`tb3-up`→`tb3-slam`.
- **`Package not found turtlebot3_bringup`** → 워크스페이스 깨짐. `cd ~/turtlebot3_ws && colcon build --symlink-install --parallel-workers 1 --executor sequential` (6-10분).
- **LiPo 11.0V 이하** → 즉시 회수 + 교체. 절대 9V 이하로 방전 금지 (LiPo 영구손상)
- **LiDAR 멈춤** → 메인 스위치 OFF → 5초 → ON. 그래도 안 되면 USB 재연결
- **Nav2 충돌** → `tb3-down`, 안전 위치로 수동 이동, `tb3-nav2` 재시작
- **인터넷 끊김(LAN은 OK)** → 로컬 작업만 진행 (`tb3-*` 모두 LAN 기반이라 인터넷 불필요)
- **경기장 Wi-Fi 대역이 다름** → `tb3-myip`가 192.168.0.x 안 잡힘. `vi ~/URHYNIX/scripts/tb3.sh`로 `TB3_LAN_CIDR='10.0.0'`(현장 대역) 같이 일시 수정. 또는 휴대폰 핫스팟 SSID/PW를 robot이 이전 연결한 Wi-Fi와 동일하게 설정 (가장 단순).
- **Unity가 robot 토픽 못 받음 (5채널 LIVE 미점등)** → `RosSmokeDashboard.rosIP` Inspector 값이 `tb3-ip` 결과와 다름. Unity Editor → RosSmokeDashboard Inspector → `rosIP` 수동 변경 → Play 재시작.

## 🧳 회수 (경기장 떠나기 전)

- [ ] `tb3-down` — 모든 tmux 정리
- [ ] `tb3-poweroff` — 라즈베리파이 셧다운 (y 확인) → `ping -c 2 <ip>` 무응답 확인
- [ ] 메인 슬라이드 스위치 **OFF** (LiDAR 모터까지 정지)
- [ ] LiPo 분리 후 가방
- [ ] `docs/evidence/maps/<map_name>/` 4파일 git에 들어갔는지 확인
- [ ] 현장 사진 `photos/` 폴더로 정리
- [ ] HANDOFF.md "지금 즉시 해야할 일" 다음 액션 갱신

## 한줄정리

가방 → 네트워크 → 호스트 → 로봇 사전점검 → 현장 10단계 → 회수 5단계. 각 출동 전 30분 안에 한 번 훑으면 사고 없이 끝낼 수 있어요.
