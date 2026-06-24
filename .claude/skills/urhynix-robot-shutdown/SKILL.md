---
name: urhynix-robot-shutdown
description: URHYNIX 젠지·티원 라즈베리파이를 한 번에 안전 종료하는 표준. "셧다운해줘", "로봇 꺼", "로봇 종료", "둘 다 꺼", "shutdown", "전원 내려" 같은 요청에 발동. sudo 비번 자동 주입(비대화 ssh) + ping으로 실제 종료까지 검증. 비번은 git에 안 박고 로컬 메모리에서 읽음. 충전소 정박 중에도 안전(OS만 종료, 전원/충전 유지).
---

# URHYNIX Robot Shutdown

## 목적

두 로봇(젠지 tb3_2, 티원 tb3_1)을 한 호출로 안전하게 종료한다. 라즈베리 sudo는 NOPASSWD가 아니라 매번 비번이 필요한데, Claude Code Bash는 비대화형이라 프롬프트를 못 받는다 → `sudo -S`로 stdin 주입.

## 발동 트리거

"셧다운해줘", "로봇 꺼", "로봇 종료", "둘 다 꺼", "전원 내려", "shutdown" 등 세션 종료 정리.

## 선행: 접속 정보 확보

1. **IP**: alias/mDNS가 죽어 있으면 SSOT `unity/ControlRoom/Assets/Resources/RobotConfig/default_robots.json`의 `hostAddress` 사용. DHCP drift는 정상(메모리 `project_robot_ip_dynamic`). 못 찾으면 `robot-ip-detect-fallback`.
2. **sudo 비번**: git에 안 박는다. 로컬 메모리 `~/.claude/projects/-Users-family-jason-URHYNIX/memory/urhynix-robot-sudo-passwords.md`에서 읽는다. 메모리에 없으면 주인님께 1회 물어보고 그 메모리에 저장.

현재 접속(2026-06-24): 젠지 `kim@192.168.10.84` · 티원 `t1@192.168.10.250`. **비번 값은 여기 적지 않는다(git 커밋됨)** — 위 메모리 파일에서 읽고, IP가 바뀌었으면 default_robots.json 우선.

## 절차

### Step 1 — 셧다운 명령 주입 (두 로봇 병렬)

```bash
# 젠지
ssh -o ConnectTimeout=6 <genji_host> "echo <genji_pw> | sudo -S shutdown -h now" 2>&1 | grep -iv password | tail -2
# 티원
ssh -o ConnectTimeout=6 <t1_host>    "echo <t1_pw> | sudo -S shutdown -h now" 2>&1 | grep -iv password | tail -2
```

`grep -iv password`로 sudo 비번 프롬프트 줄만 숨기고, 다른 에러(연결 실패 등)는 남긴다. 출력이 비면 정상 전송(shutdown은 즉시 연결을 끊어 표준출력이 없다).

### Step 2 — 종료 검증 (ping, 반드시 수행 — 검증은 성역)

```bash
for i in 1 2 3 4 5 6; do
  g=$(ping -c1 -t1 <genji_ip> >/dev/null 2>&1 && echo UP || echo DOWN)
  t=$(ping -c1 -t1 <t1_ip>    >/dev/null 2>&1 && echo UP || echo DOWN)
  echo "[$i] 젠지=$g  티원=$t"
  [ "$g" = DOWN ] && [ "$t" = DOWN ] && break
  ping -c2 <genji_ip> >/dev/null 2>&1   # foreground sleep 금지 대용 시간벌이
done
```

둘 다 DOWN이면 종료 완료. 라즈베리는 wlan이 빨리 내려가 보통 1~2회 내 DOWN.

## 함정

- **`timeout` 명령 없음(macOS)**: ssh는 `-o ConnectTimeout`만 사용. `timeout 5 ssh ...`는 `command not found`.
- **`sudo shutdown` 직접 = 비번 프롬프트 에러**: `a terminal is required to read the password`. 반드시 `echo <pw> | sudo -S`.
- **비번을 SKILL.md/스크립트에 평문 커밋 금지**: 메모리 파일(repo 밖)에서만 읽는다. `secret-scan` 대상.
- **ping 1회 DOWN을 너무 빨리 신뢰**: shutdown 직후 ssh 세션이 끊기며 잠깐 끊길 수 있으니, 첫 DOWN이어도 위 루프로 1회 더 확인.
- **충전소 정박**: shutdown은 OS만 내린다. 전원선/충전은 유지 — 안전.

## Verify

- 두 로봇 모두 ping DOWN 확인.
- 보고: 로봇별 IP + 🔴 종료됨 표.

## Outputs

- 두 로봇 종료 + ping 검증 결과 1표.
