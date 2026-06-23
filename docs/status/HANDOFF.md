# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-06-18 (**✅ demo_logs_rls.sql 적용 완료 + Unity→Supabase 직접쓰기 end-to-end 검증 PASS** — Supabase `ueupkrxwybuuqxflstvg`는 paused 아니라 **복구 LIVE** 확인. demo_logs_rls.sql 적용(logs 테이블 + dispatches event_id nullable·nav_mode·reason + anon RLS 10개), anon REST 왕복(pose_logs/logs insert→select) PASS, Unity Play에서 **session_meta + logs 직접쓰기 PASS**(logs 7건 DB 실기록, `DbVerifyConsole.Verify()` active=True 검증). **⚠️ 미해결 1건**: pose_logs에 Unity pose 미기록 — RobotPoseSubscriber가 `/tf` map 프레임을 못 받음(로봇 정지 아님; 첫 pose는 무조건 기록되는 로직이라 데이터 소스 미수신이 원인). **다음 진입**: ① Unity Play에서 RobotPoseSubscriber `/tf` 구독·수신 확인 → ROS 연결(젠지 `192.168.10.84:10000`)·TF 체인(map→odom→base_link 발행 여부)·센서 real/fake 점검 → ② pose 흐르면 pose_logs 적재 확인. **주의**: anon DELETE 정책 없음(204여도 미삭제) → 정리는 `supabase db query` service 권한. 자세히: `DECISION-LOG.md` 2026-06-18 최상단. **함정 메모**: unityctl 0.4.0 `play start/stop`은 `--project` 필수, `exec invoke`는 `--type`/`--method` 분리. **이전(2026-06-18, superseded)**: 🗄️ Unity→Supabase "직접 택배" 코드+컴파일 PASS·DB 복구 대기 — 위에서 Restore·SQL 적용·검증 완료로 해소. **이전(2026-06-18)**: ✅ 실센서→ROS→Unity 4카드 라이브 표시 LIVE 검증(사용자 화면 확인), IP 정합+PIR D4→D2. **이전(2026-06-18 오후)**: Phase C Unity UI 4센서 카드 리팩토링 PASS. **이전(2026-06-17)**: 🌡️ PP-A017 온도 A0 PASS · 🎨 시나리오 다이어그램. **ROS IP SSOT**: `default_robots.json[0].hostAddress` — DHCP drift 시 먼저 여기 갱신.

---

## ⚡ Top 1 Action (가장 최신)

**Unity pose_logs 미기록 추적 — RobotPoseSubscriber /tf map 프레임 수신 / TF 체인 확인**

- **배경**: Supabase demo_logs_rls.sql 적용 완료 + session_meta/logs 직접쓰기 PASS (logs 7건 기록), pose_logs만 0건  
- **원인**: RobotPoseSubscriber가 /tf map 프레임 못 받는 것(TF 체인/ROS 연결/센서 fake 여부 미확인)  
- **다음 확인**:  
  1. ROS bringup 시 `/tf` 토픽이 map→odom→base_link 체인 발행되는가  
  2. RobotPoseSubscriber 구독 로그에 "Transform received" 메시지가 나오는가  
  3. 로봇 센서(SLAM/wheel odom)가 정상 동작 중인가  
- **주의**: 첫 pose는 조건 없이 무조건 기록(로직 정상), 데이터 소스만 미수신

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
