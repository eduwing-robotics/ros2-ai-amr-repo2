---
name: ip-drift-resync
description: DHCP로 robot IP가 바뀌었을 때 Unity Scene + Script + known_hosts를 한 번에 동기화한다. Unity Editor 자동 save가 외부 patch를 덮어쓰는 함정까지 Editor 종료/patch/재시작 순서로 자동 회피. URHYNIX 매 세션 첫 5분 표준.
user_invocable: true
tags: [network, dhcp, unity, ros2, urhynix-m3-m5]
trigger: "경기장/사무실 이동 또는 Wi-Fi 재접속으로 robot DHCP IP가 변경됐고 Unity rosIP·SSH known_hosts·helper를 일괄 동기화해야 할 때"
version: 1
---

# IP Drift Resync

DHCP 환경에서 robot이 새 IP를 받으면 다음 4곳을 매번 수동 patch해야 했던 문제를 한 줄로 해결.

URHYNIX의 2026-05-29 evening 발견:
**Unity Editor가 살아있는 동안 Scene을 자동 save back하면서 외부 sed patch를 덮어쓴다**. 이 함정을 Editor 종료 → patch → 재시작 순서로 자동 회피.

## Use When

- 매 세션 첫 5분 — robot IP 재확인 + Unity rosIP 동기화
- 경기장↔사무실 이동 후 다른 Wi-Fi에 접속했을 때
- `tb3-ip` 결과가 어제와 다를 때
- Unity 패널이 "○ ROS-TCP 끊김" 표시할 때
- `ssh` 시 `Host key verification failed` 발생 시

## 동기화 대상 (4곳)

| 위치 | 내용 |
|---|---|
| `unity-smoke/Assets/Scenes/SampleScene.unity:151` | `rosIP:` 직렬화 값 |
| `unity-smoke/Assets/Scripts/RosSmokeDashboard.cs:10` | `public string rosIP = "..."` 기본값 |
| `~/.ssh/known_hosts` | 옛 IP 엔트리 (충돌 방지) |
| `~/jason/URHYNIX/scripts/tb3.sh:TB3_ROBOT_IP_HINT` | (선택) 다음 sweep 빠르게 |

## Inputs

- `[new_ip]` (선택): explicit IP. 생략 시 `tb3-ip`로 MAC sweep 자동 발견.

## Outputs

- Scene + Script 두 파일 patch
- known_hosts에서 옛 IP 제거
- (옵션) Unity Editor 재시작 + ros_tcp_endpoint 로그에서 새 IP 연결 검증

## One-Liner

```bash
bash .claude/skills/ip-drift-resync/resync.sh             # 자동 발견
bash .claude/skills/ip-drift-resync/resync.sh 192.168.0.42  # explicit
```

또는 alias (`scripts/aliases.sh`에 등록 후):
```bash
ip-resync
```

## 5단계 절차 (스크립트 내부)

```
1. 새 IP 결정
   - arg 있으면 그 값
   - 없으면 `tb3-ip` (MAC sweep 자동)

2. 현재 Scene/Script의 옛 IP 추출
   - grep으로 "rosIP" 라인에서 정규식 추출
   - 새 IP와 같으면 patch 스킵

3. Unity Editor 종료 (자동 save back 함정 회피)
   - macOS: pkill -f "Unity.app/Contents/MacOS/Unity"
   - 3초 대기 + 종료 확인
   - 안 살아있으면 skip

4. sed 일괄 patch
   - SampleScene.unity:151 "  rosIP: <old>" → "  rosIP: <new>"
   - RosSmokeDashboard.cs:10 'public string rosIP = "<old>"' → '... "<new>"'
   - ssh-keygen -R <old_ip>로 known_hosts 정리

5. (옵션) Unity 재시작 + 연결 검증
   - `tb3-unity` 호출 (RosSmokeConfigure.Play 자동)
   - 30s 대기 후 robot ros_tcp_endpoint 로그에서 "Connection from <Mac_IP>" 확인
```

## 🚨 핵심 함정 — Unity 자동 save back

Unity Editor가 켜진 상태에서 Scene/Script를 외부에서 수정하면:
- Unity가 변경 감지 → hot reload
- 다음 save 사이클에 **Editor의 메모리 상태(옛 값)로 덮어쓰기**
- 결과: 외부 patch가 무효화됨

→ **반드시 Editor 종료 후 patch**.
patch 후 재시작은 안전 (Unity가 새 값을 deserialize).

## 트러블슈팅

| 증상 | 원인 | 해법 |
|---|---|---|
| `tb3-ip` 응답 없음 | 다른 Wi-Fi 대역 | `scripts/tb3.sh`의 `TB3_LAN_CIDR` 변경 (예: `10.0.0`) |
| patch 후 Scene이 옛 값으로 돌아옴 | Unity 종료 안 됨 | `pgrep -f Unity.app` 으로 확인, 강제 kill |
| Unity 재시작 후 "○ 끊김" | ros_tcp_endpoint 죽었음 | `tb3-up`으로 bringup + ros_tcp 재기동 |
| `Host key verification failed` | known_hosts 정리 안 됨 | 수동: `ssh-keygen -R <old_ip>` |
| sed: in-place 실패 (macOS) | BSD sed 문법 차이 | 스크립트는 `sed -i ''` (macOS) / `sed -i` (Linux) 분기 처리 |

## Chain With

- 출발: `task-intake-router` (세션 첫 5분 routing)
- 동시: `arena-deployment-checklist` 사전 점검
- 후속: `tb3-up` → `tb3-slam` → `slam-nav2-arena-survey` (매핑 사이클)
- 결정 시: `decision-broadcast` (IP가 영구 변경됐을 때)

## 한줄정리

DHCP IP 변경 → `bash .claude/skills/ip-drift-resync/resync.sh` 한 줄. Unity Editor 자동 save 함정까지 종료/patch/재시작 순서로 자동 회피.
