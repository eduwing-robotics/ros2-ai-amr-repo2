<!--
2026-06-15 evidence. 직결 제거 → 팀 와이파이 무선 통일, ROS_DOMAIN_ID 210 전면 통일,
cross-discovery 검증 PASS, Unity 듀얼 로봇(카메라/배터리) 전환 코드+Scene 검증.
티원=RealSense 비전 전용 / 젠지=Pi Camera + 센서 전용 역할 분담 확인.
-->
# 2026-06-15 무선 통일 + 도메인 210 통일 + Unity 듀얼 로봇 전환 검증

## 한 줄 결과
직결(en5) 제거하고 **팀 와이파이로 무선 통일**, `ROS_DOMAIN_ID` **210 전면 통일**, **cross-discovery PASS**. Unity 카메라/배터리 듀얼 로봇 전환은 코드+Scene 완비 확인. 센서는 역할 분담대로 **젠지 단독**(티원은 RealSense 비전 전용).

## 1. 네트워크 — 무선 통일 (직결 제거)
| 항목 | 값 |
|---|---|
| 팀 와이파이 격리 | **AP isolation 아님** (Mac↔티원 SSH 통과로 확인) |
| 젠지 | `192.168.10.87` (wlan0) · hostname `kim-desktop` |
| 티원 | `192.168.10.250` (wlan0) · hostname `rb` |
| 직결 | 제거 (Mac en5 down) |

### 젠지 무선 불통 원인 = asymmetric routing (해결됨)
- 증상: 젠지 `.87`이 ARP(L2)는 응답하나 ping/SSH(L3+)는 모든 출발지에서 100% loss. 티원은 정상.
- 원인: 젠지가 eth0(직결)+wlan0 동시 보유 + **default route가 eth0**로 잡혀, wlan0(.87)로 온 요청의 응답을 직결로 내보냄 → Mac 미수신.
- 해결: **직결 랜선 물리 제거** → eth0 down → `default via 192.168.10.1 dev wlan0`로 전환 → ping 0% loss, SSH OK.
- (IP는 DHCP drift 정상. 항상 ARP OUI `2c:cf:67`(젠지)/`d8:3a:dd`(티원) 매칭으로 재탐색.)

## 2. ROS_DOMAIN_ID 210 통일 + cross-discovery
- 젠지: 팀원이 이미 210. 티원: `~/.bashrc` 230→210 변경.
- namespace 분리(`/tb3_1`=티원, `/tb3_2`=젠지)는 유지 → **"도메인 통일 + namespace 분리"**가 정본.
- **cross-discovery PASS**: 티원에서 talker 발행 → 티원·젠지 양쪽 `ros2 topic list`(210)에 `/chatter` 동시 노출 = 같은 도메인 상호 발견 확인.
- SSOT 6개 갱신: ARCHITECTURE.md, CONTRACT.md, tech/ROS2-ROBOT.md, tech/VISION-CAMERA.md, PROJECT-PLAN.md, unity Ros/CLAUDE.md.

## 3. Unity 듀얼 로봇 전환 검증 (코드 + Scene 정적)
역할 분담: **티원(tb3_1)=RealSense 비전 / 젠지(tb3_2)=Pi Camera + 센서**.

| 데이터 | 티원(tb3_1) | 젠지(tb3_2) | 전환 |
|---|---|---|---|
| 카메라 | ✅ Subscriber 배치(T1) | ✅ 배치(Genji) | ✅ |
| 배터리 | ✅ 배치 | ✅ 배치 | ✅ |
| 조도/PIR | — (물리 센서 없음, 정상) | ✅ 배치 | 젠지 탭만 |

- 전환 메커니즘 (모델 B): `CameraStreamSubscriber`/`BatterySubscriber`/`Lux·PirSubscriber`가 항상 동시 구독 → View가 `robotId == SelectedRobotId` 필터. 탭(`tab-tb3_1`/`tab-tb3_2`) 클릭 → `ControlRoomState.SelectRobot` → `OnRobotChanged` → 카메라/배터리/센서 View 즉시 재표시(캐시 redraw, 지연 0~33ms).
- Scene 배치 확인(`ControlRoomMain.unity`): CameraStreamSubscriber ×2(T1·Genji), BatterySubscriber ×2, LuxSubscriber ×1(젠지), PirSubscriber ×1(젠지).
- cross-host 가시성은 **단일 ros_tcp_endpoint(티원)**가 210에서 양 로봇 토픽을 forward하는 구조에 의존 → 도메인 통일이 전제(검증됨).
- 티원 탭 선택 시 센서 카드 `--` 표시는 **정상**(티원에 센서 없음).

## 4. 미해결 갭 / 다음 세션
- [ ] **런타임 토픽 0** — 두 로봇 bringup + 카메라(젠지 Pi Camera / 티원 RealSense) 노드 기동해야 Unity에 실제 영상/값이 뜸. 현재 미실행이라 켜면 빈 화면.
- [ ] **ControlRoomApp IP 하드코딩**(`192.168.0.250` fallback + `t1@192.168.10.250`) → hostname/mDNS 전환 검토 (IP drift 위반).
- [ ] **젠지 센서 토픽 `/sensors/*` namespace 미분리** → Phase 3에서 `/tb3_2/sensor/*` 정합.
- [ ] Unity 에디터 Play로 실제 듀얼 전환 육안 확인(GUI, 사람이 수행).
