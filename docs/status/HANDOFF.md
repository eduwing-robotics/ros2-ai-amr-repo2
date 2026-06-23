# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-06-23 (**🔄 git 원격 이관 완료** — 기존 URHYNIX repo에서 새 ros2-ai-amr-repo2로 이관. 클론 무게 ~25M, Unity ControlRoom 6000.3.16f1 정상. **⚠️ 주의**: 앞으로 모든 push는 새 repo `https://github.com/eduwing-robotics/ros2-ai-amr-repo2`로 진행. 옛 히스토리 백업 `.git.bak.20260623/`은 검증 후 삭제 예정. evidence 맵 PNG는 로컬 보존(git 제외). 자세히: `DECISION-LOG.md` 2026-06-23 최상단. **이전(2026-06-18)**: ✅ demo_logs_rls.sql 적용 완료 + Unity→Supabase 직접쓰기 검증 PASS (pose_logs TF 미수신 차후 추적). **이전(2026-06-18)**: ✅ 실센서→ROS→Unity 4카드 라이브 표시. **ROS IP SSOT**: `default_robots.json[0].hostAddress` — DHCP drift 시 먼저 여기 갱신.

---

## ⚡ Top 1 Action (가장 최신)

**다음 세션 시작 전 git origin 원격 확인**

- **배경**: 2026-06-23 git 원격을 새 repo `https://github.com/eduwing-robotics/ros2-ai-amr-repo2`로 이관 완료
- **다음 확인**:
  1. `git remote -v` → origin이 새 repo인지 확인
  2. 클론 무게 `du -sh .git/` → ~25M 정상 범위
  3. Unity ControlRoom 빌드 → 정상 실행 확인
- **미보류**:
  - 옛 히스토리 백업(`.git.bak.20260623/`) 삭제(새 repo 검증 후)
  - evidence 맵 PNG 필요 시 로컬 보존 확인
- **주의**: 앞으로 모든 push는 새 repo로만 진행

---

## 📋 First 5 Min Checklist

```bash
# 1. 로봇 진입 (직결/무선 중 선택)
ssh urhynix-robot                    # mDNS (권장)
# 또는
ssh kim@192.168.10.50               # 직결(en5) 사용 시 — 젠지 eth0, bootpd DHCP
# 또는  
ssh kim@192.168.10.87 / t1@192.168.10.250  # 무선 (DHCP drift 정상)

# 2. 센서/하드웨어 5단계 점검 (~5분)
cat /sys/class/power_supply/*/uevent | grep VOLTAGE  # 배터리 11.5V 이상?
ros2 launch turtlebot3_bringup robot.launch.py      # Burger connected, DynamixelSDK error 없나?
ros2 run aruco_parking parking_node                 # 마커 주차 5회 시연

# 3. 양 로봇 토픽 확인 (도메인 210)
ros2 topic list | grep -E "tb3_1|tb3_2|camera|sensor"  # 카메라·센서 토픽 보이나?

# 4. Unity 실행
python3 ~/URHYNIX/unity-smoke/run.sh  # 또는 Unity Hub에서 ControlRoom 실행
```

→ **통과 기준**: bringup OK + 토픽 2개 이상 + Unity 화면 LIVE

---

## 🔧 If Stuck (빠른 복구)

| 증상 | 명령 |
|------|------|
| IP 못 찾음 | `bash .claude/skills/robot-ip-detect-fallback/resync.sh` |
| mDNS `.local` 안 잡힘 | 무선 확인: `ifconfig wlan0` → 192.168.0.x 또는 10.x 범위인가? |
| 무선 끊김 | 임시: `ifconfig en5 down` (직결 비활성) + 무선만 사용 |
| 카메라 토픽 0건 | 젠지 Pi Camera / 티원 RealSense `launch` 명령 재실행 + 15초 대기 |
| Arduino `/dev/tb3_arduino` stale | `ln -sf /dev/ttyACM0 /dev/tb3_arduino` |

---

## 📚 More Info (상세 내용)

| 문서 | 용도 |
|------|------|
| **`HANDOFF-FULL.md`** | 이전 모든 세션 기록(506줄), 하드웨어·센서 설치 상세 |
| **`DECISION-CURRENT.md`** | 최신 결정 5건 — 센서 교체·도메인 통일·무선 통일 |
| **`DECISION-LOG.md`** | 전체 결정 이력 + 근거 |
| **`PROJECT-STATUS.md`** | 한 줄 상태 + 역할 매트릭스 |
| **`../ref/TECH-INDEX.md`** | 작업별 빠른 문서 라우팅 |
| **ROS2-ROBOT.md** | 직결/무선 접속, 센서 핀 매핑 |
| **evidence/** | 센서 교체 / 무선 통일 / YOLO 검증 기록 |

---

## ✅ 한줄정리

**도메인 210 통일 + 젠지 센서 교체(LDR→온도·레이저) + 무선망 안정화 완료. 다음 세션: 양 로봇 부팅 + 시나리오 5종 시연.**
