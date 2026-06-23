# 다음 세션 진입 준비 — 경기장 SLAM + Unity 연결

> HANDOFF Top 1 + ARENA 11단계 + 검증된 6 helper 흐름 + 트러블슈팅 +8건 모두 git에 박혀있음. **95% 준비 완료**. 잠재 갭 2개(경기장 Wi-Fi 대역, Unity rosIP 수동 변경)는 현장 5분 처리 가능.

## ✅ 준비 완료 (95%)

| 영역 | 상태 | 위치 |
|---|---|---|
| HANDOFF Top 1 | ✅ "경기장 출동 + 25분 매핑" + 검증된 6 helper 흐름 | `docs/status/HANDOFF.md` |
| 현장 11단계 | ✅ 위치선정→스위치ON→Wi-Fi→tb3-go→줄자→SLAM→teleop→저장→Unity→Nav2 | `docs/ref/ARENA-DEPLOYMENT-CHECKLIST.md` |
| 검증된 헬퍼 6개 | ✅ `tb3-up/slam/teleop/slam-save/fetch-map/map-to-unity` (오늘 책상 매핑 PASS) | `scripts/tb3.sh` |
| 스킬 본문 | ✅ 결정 트리 + ROS 모드 통일 + 트러블슈팅 +8 | `.claude/skills/slam-nav2-arena-survey/SKILL.md` |
| Unity-smoke 프로젝트 | ✅ 5채널 LIVE + ROS-TCP-Connector | `unity-smoke/Assets/Scripts/RosSmokeDashboard.cs` |
| 가방 체크리스트 | ✅ 하드웨어/네트워크/측정 도구/예비 LiPo | ARENA-CHECKLIST §🎒 |
| 비상 매뉴얼 | ✅ /map 0 / SSH thrash / Package not found 회복 | ARENA-CHECKLIST §🚨 |
| 자격 증명 | ✅ `~/.tb3rc`, robot `/etc/urhynix.env` (머신 로컬, 커밋 안 됨) | 각 머신 |
| SSOT 갱신 | ✅ 4개 SSOT 최신 (28a2632) | git log |

## ⚠️ 잠재 갭 2개 (현장 도착 시 처리)

### 1. 경기장 Wi-Fi 대역이 192.168.0.x가 아닐 경우 🟡

- 다른 대역(예: 10.0.0.x)이면 `scripts/tb3.sh`의 `TB3_LAN_CIDR='192.168.0'` 일시 수정
- robot이 새 Wi-Fi 자동 연결 안 됨 → robot 직접 키보드+모니터 또는 휴대폰 핫스팟
- **추천**: 휴대폰 핫스팟을 미리 SSID 동일하게 설정 (ARENA §🎒 백업 핫스팟)

### 2. Unity의 `rosIP` 수동 변경 필요 🟡

- `RosSmokeDashboard.rosIP` 기본값 `192.168.0.138` (DHCP라 매번 다름)
- 흐름: `tb3-ip` → IP 받음 → Unity Editor → RosSmokeDashboard Inspector → `rosIP` 입력
- **개선 후보** (다음 세션 시간 있으면): `tb3-unity-set-ip <ip>` helper 또는 RosSmokeDashboard 환경 변수 읽기

## 🚀 다음 세션 첫 5분 한 줄 흐름

```bash
# 도착
1. 메인 스위치 ON → 30초 대기
2. 노트북 같은 Wi-Fi 연결 → tb3-myip → 192.168.0.x 확인
3. . ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh
4. tb3-ip → 로봇 IP 확보 (✏️ 기록)
5. tb3-go → 5채널 LIVE
6. tb3-slam → /map 검증
7. tb3-teleop → 25분 매핑
8. tb3-slam-save arena_<지명>_v1 + tb3-fetch-map + tb3-map-to-unity
9. Unity Editor → RosSmokeDashboard.rosIP를 4번 IP로 변경 → Play
```

## 🟥 준비 안 된 것 (다음 세션 즉시 처리)

| 항목 | 작업 |
|---|---|
| 로봇 전원 | 메인 스위치 OFF 상태 — 현장에서 ON |
| Arduino PIR 핀 D7→D2 정렬 (이전부터 미완) | `sketches/pir_led/pir_led.ino` 수정 + `arduino-flash` 재플래시 (선택, SLAM과 무관) |
| LiPo 충전 | 출동 전 풀충 확인 |

## 한줄정리

**다음 세션 95% 준비됨**. HANDOFF Top 1 + ARENA 11단계 + 검증된 6 helper 흐름 + 트러블슈팅 +8건 모두 git. 남은 갭은 경기장 Wi-Fi 대역(휴대폰 핫스팟 백업)과 Unity rosIP 수동 입력 한 줄뿐. 현장 도착 시 5분 안에 처리 가능.
