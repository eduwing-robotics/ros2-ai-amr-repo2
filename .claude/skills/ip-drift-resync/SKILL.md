---
name: ip-drift-resync
description: DHCP로 robot IP가 바뀌었을 때 default_robots.json(SSOT) + known_hosts를 한 번에 동기화한다. "젠지/티원 IP 바뀜", "Unity가 로봇 연결 안 됨인데 ssh는 됨" 요청에 발동. URHYNIX 매 세션 첫 5분 표준.
user_invocable: true
tags: [network, dhcp, unity, ros2, urhynix-m3-m5]
trigger: "경기장/사무실 이동 또는 Wi-Fi 재접속으로 robot DHCP IP가 변경됐고 default_robots.json·SSH known_hosts를 일괄 동기화해야 할 때"
version: 2
---

# IP Drift Resync

DHCP 환경에서 robot이 새 IP를 받으면 Unity SSOT(`default_robots.json`)가 따라가지 못해 "ssh는 되는데 Unity는 연결 안 됨"이 생기는 문제를 한 줄로 해결.

**2026-07-03 v2**: v1은 `unity-smoke/Assets/Scenes/SampleScene.unity`+`RosSmokeDashboard.cs`를 patch 대상으로 했으나, 이 둘은 `unity/CLAUDE.md`에 "보존만, 신규 작업 금지"로 동결된 구프로토타입 — **실제로는 아무 효과 없이 계속 방치돼 있었음**(젠지 IP가 `192.168.20.7`로 드리프트했는데 `default_robots.json`의 `hostAddress`는 옛값 `192.168.10.84`로 계속 남아있었던 실사고로 발견). 현재 SSOT는 `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json`이므로 이걸 patch 대상으로 교체.

## Use When

- 매 세션 첫 5분 — robot IP 재확인 + `default_robots.json` 동기화
- 경기장↔사무실 이동 후 다른 Wi-Fi에 접속했을 때
- `tb3-ip` 결과가 어제와 다를 때
- **`ssh <alias>`는 되는데 Unity가 그 로봇에 연결 안 될 때**(=SSOT 드리프트 신호, 아래 실사고 참고)
- `ssh` 시 `Host key verification failed` 발생 시

## 동기화 대상

| 위치 | 내용 |
|---|---|
| `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json` | 해당 `robotId`의 `"hostAddress": "user@ip"` |
| `~/.ssh/known_hosts` | 옛 IP 엔트리 (충돌 방지) |

JSON은 TextAsset이라 Unity Editor가 Scene/Script처럼 자동 save-back 하지 않음(v1의 핵심 함정이었던 "Editor 켜진 채로 patch하면 덮어써짐"이 여기선 발생 안 함) — **Editor kill 불필요**. 단 Play 중이면 `Resources.Load`가 이미 캐시했을 수 있어 반영하려면 play stop→start 재시작은 필요.

## Inputs

- `<tb3_1|tb3_2>` (필수): 어느 로봇인지.
- `[new_ip]` (선택): explicit IP. 생략 시 `tb3-ip`로 MAC sweep 자동 발견(단일 로봇 전제 — 두 로봇이 같은 서브넷에 같이 있으면 `robot-ip-detect-fallback`으로 신원 보장 먼저 확인 후 explicit IP로 넘길 것).

## Outputs

- `default_robots.json` patch (해당 robotId만)
- known_hosts에서 옛 IP 제거
- 검증 출력(patch 후 해당 블록 grep)

## One-Liner

```bash
bash .claude/skills/ip-drift-resync/resync.sh tb3_2                    # 자동 발견
bash .claude/skills/ip-drift-resync/resync.sh tb3_2 192.168.20.7       # explicit
```

## 실제 사례 (2026-07-03)

| 항목 | 값 |
|---|---|
| 증상 | `ssh genzi`(alias)는 되는데 `default_robots.json`의 tb3_2 hostAddress는 `192.168.10.84`(구값) |
| 실제 IP | `192.168.20.7` (ssh config 자체는 이미 최신 — 2026-06-30에 누군가 갱신했으나 default_robots.json은 누락) |
| 발견 경로 | 사용자가 "젠지 켜져있는데"라고 정정 → ping 실패 재확인 → ssh alias는 성공 → 두 소스가 어긋남을 인지 |
| 조치 | `default_robots.json` 직접 patch + 본 스킬 v2로 재발 방지 |

## 트러블슈팅

| 증상 | 원인 | 해법 |
|---|---|---|
| `tb3-ip` 응답 없음 | 다른 Wi-Fi 대역 | `scripts/tb3.sh`의 `TB3_LAN_CIDR` 변경, 또는 explicit IP로 직접 지정 |
| 두 로봇이 같은 서브넷이라 `tb3-ip`가 헷갈림 | MAC OUI만으론 어느 로봇인지 모호 | `robot-ip-detect-fallback`(ed25519 키 매칭, 신원 보장)으로 먼저 IP 확정 후 explicit로 이 스킬 호출 |
| patch 후에도 Unity가 옛 IP로 붙음 | Play 모드가 이미 `Resources.Load` 캐시 | `unityctl play stop` → `play start`로 재시작 |
| `Host key verification failed` | known_hosts 정리 안 됨 | 수동: `ssh-keygen -R <old_ip>` |
| sed: in-place 실패 (macOS) | BSD sed 문법 차이 | 스크립트는 `sed -i ''` (macOS) / `sed -i` (Linux) 분기 처리 |

## Chain With

- 선행(신원 모호 시): `robot-ip-detect-fallback`
- 후속: Unity `play stop`→`play start`로 연결 재시도
- 결정 시: `decision-broadcast` (IP가 영구 변경됐을 때)

## 한줄정리

DHCP IP 변경 → `bash .claude/skills/ip-drift-resync/resync.sh <tb3_1|tb3_2> [ip]` 한 줄로 `default_robots.json`(진짜 SSOT) + known_hosts 동기화. v1의 unity-smoke 타겟은 죽은 코드였다.
