# Session Handoff — 다음 세션 진입 캡슐

> **다음 세션의 AI 에이전트가 첫 5분 안에 컨텍스트를 잡기 위한 1페이지.**
> 
> 구조: Last updated 날짜 | Top 액션 | 첫 5분 체크리스트 | 복구 명령 | More info 링크

**Last updated**: 2026-06-26 (밤) — **🛰️ 멀티로봇 도메인 충돌 해결 + 네임스페이스+tf_prefix bringup 검증 PASS.** **증상**: 티원·젠지가 같은 도메인210에서 둘 다 **비-네임스페이스(`__ns:=/`)**로 `/scan`·`/tf`를 쏴서 라이다가 섞여 SLAM 깨짐(`/scan` Publisher count=2 = DDS 충돌). **즉시조치**: 티원이 SLAM 주체(`slam_toolbox`)였으므로 **젠지 종료**(PID 직접 kill — `pkill -f`는 self-kill 위험) → 티원 `/scan` 단독 복귀. **근본해결 설계**: 도메인은 **210 그대로**(Unity 브리지가 한 도메인만 봄·맵/관제 공유 필요), 격리는 **namespace `tb3_1`(티원)/`tb3_2`(젠지)**가 담당 → 토픽 `/tb3_X/*` + TF 프레임 `tb3_X/*` 접두사 분리 = 구조적 충돌 불가. (도메인 분리는 협조 주행에 부적합이라 안 씀.) **유일 누수=coin_d4 라이다**: launch가 namespace 인자를 무시하고 yaml 고정 `frame_id: base_scan` → scan header가 prefix 안 돼 URDF의 `tb3_X/base_scan`과 불일치 → TF 룩업 실패. **봉합**: `scripts/dual_bringup.launch.py`(robot.launch.py 최소 변형, 라이다 `frame_id=[ns,'/base_scan']`) + `scripts/_robot_bringup_ns.sh`(런처). 둘 다 로봇 홈에 scp 후 실행. **기존 단일 경로 `_robot_nav_up.sh`는 무수정**(별도 경로). **검증 PASS(젠지)**: 전 토픽 `/tb3_2/*`, scan/odom frame=`tb3_2/*`, `tf2_echo tb3_2/odom tb3_2/base_scan` 룩업 성공([-0.032,0,0.182]=라이다 오프셋) = 전체 TF 트리 `tb3_2/` 일관, 누수 0. (테스트는 도메인 211 격리로 티원 SLAM 무영향, **실배포는 둘 다 210**.) **🎯 다음 액션**: ① 티원 SLAM 끝나면 맵 저장(`map_saver_cli` 또는 slam_toolbox serialize) — 이 맵이 기존 "동료 새 맵 대기" 블로커를 대체 가능 ② 두 로봇 다 `bash _robot_bringup_ns.sh tb3_2`(젠지)·`tb3_1`(티원)로 **210+namespace** 기동 ③ **nav2를 namespace로** 띄우기(각 로봇 amcl+costmap을 `/tb3_X/tf` 트리로, `_robot_nav_up.sh`의 nav2 부분을 namespace 대응) = 진짜 동시 자율주행. **로봇**: 젠지 `kim@192.168.10.84`(1234), 티원 `t1@192.168.10.250`(123). **이전(저녁)**: 🤖 듀얼 Unity 표시 진행 + ★map5 부정확 블로커(젠지 amcl 0.54,−0.74 ↔ 표시 0.20,−1.55 = 0.9m 불일치, map5가 실제 환경과 정합 안 됨, 정확한 맵 재SLAM이 근본 해결 — 이번 티원 SLAM이 그것). 젠지=map5 nav2 재기동(충전소 0,0, endpoint `.84:10000`), 티원(tb3_1)=구독만(젠지가 대신 `/tb3_1/pose` 정적 발행 x=−0.02 y=−1.53=순회지점1, 티원 본체 무접촉). `_robot_nav_up.sh`의 MAP을 6번째 인자로 인자화. 두 마커 분리 표시됨. **★블로커**: 젠지 amcl 라이다추정(0.54,−0.74)이 주인님 표시(젠지 주차=0.20,−1.55)와 **0.9m 불일치** — map5(2.6m 작고 GIMP편집)가 실제 환경과 정합 안 됨, `/initialpose`+제자리회전으로도 안 좁혀짐. 라이다(amcl)가 실측이라 더 정확, 표시는 맵 정확할 때만 일치 → **정확한 맵 재SLAM이 근본 해결**. **🎯 다음 액션(세션 인계): 동료가 새 맵 보내줄 예정.** 받으면 ① 새 맵 pgm/yaml 젠지 `~/maps/<id>/` scp + `bash /tmp/_robot_nav_up.sh tb3_2 <ix> <iy> <iyaw> yes ~/maps/<id>/<id>.yaml` ② `saved-map-to-unity-slot`으로 Unity 슬롯(png+json) 등록 + `StaticMapLoader` 디폴트 갱신 ③ amcl 정합 재검증(표시=라이다 일치) ④ 티원 정적 pose도 새 맵 좌표로 갱신. **함정**: endpoint(ros_tcp_endpoint)는 Unity Play 반복 stop/start 시 사망 → `~/turtlebot3_ws` overlay source로 재기동(`_robot_nav_up.sh:69` 패턴) · `pkill -f`에 토픽명 넣으면 self-kill · 젠지 wifi(.84) 끊김 잦음(재부팅 복구). 순회지점1=티원주차, 2=젠지주차. **로봇**: 젠지 `kim@192.168.10.84`(1234, mDNS `urhynix-robot`)·티원 `t1@192.168.10.250`(123). Mac IP `192.168.10.48`. 색: 초록 #34D98C·파랑 #4DA3FF. 자세히: `DECISION-LOG.md` 2026-06-26 최상단. **이전(오후)**: 맵 줌/팬(휠+드래그) PASS + map5 디폴트 + 회전 좌표무영향 + "핸드오프" hook(`.claude/settings.json`). **이전(오전)**: Confluence 3페이지+Jira 5티켓+map5 슬롯 등록. **이전(2026-06-25)**: 젠지 AMCL+Nav2 좌표주행 PASS, 티원 주행 풀스택 미설치, D435 3D 점군 경로 B PASS.

---

## ⚡ Top 1 Action (가장 최신)

**Unity ControlRoom에서 `map5` / `map5_pretty` 슬롯 시각 검증 + 줌 기능 구현 여부 결정**

- **배경**: 2026-06-26에 `/Users/family/Downloads/map5.{pgm,yaml}`를 `StreamingAssets/Maps/map5.{png,json}`와 `map5_pretty.{png,json}`로 변환 완료. `MapCatalog`는 두 슬롯을 자동 인식하지만, 실제 Unity Play에서 드롭다운 전환과 pretty 텍스처가 정상 표시되는지는 아직 육안 확인 전.
- **다음 액션**:
  1. `unityctl play` (또는 Unity Hub에서 ControlRoom 실행)
  2. 중앙 맵 패널 드롭다운에서 `map5` → `map5 관제 천장뷰` 순으로 선택
  3. 맵이 정상 로드되고 벽/자유공간 색상이 pretty 스타일로 보이는지 확인
  4. 마우스 휠/트랙패드로 줌이 안 되는지 확인 → 안 될 경우 `MapViewport`+`MapInteractionController`에 줌 기능 추가 여부를 주인님께 확인
- **선행 조건**: Unity Editor 사용 가능 (`unityctl` IPC 정상 또는 Unity Hub). 로봇 불필요.

---

## 📋 First 5 Min Checklist

```bash
# 0. 오늘 변경 요약 확인 (SSOT + 슬롯)
git status --short
ls -la /Users/family/jason/URHYNIX/unity/ControlRoom/Assets/StreamingAssets/Maps/map5*
python3 /Users/family/jason/URHYNIX/scripts/pgm_to_map_slot.py --help  # 변환 스크립트 존재 확인

# 1. 로봇 진입 (직결/무선 중 선택) — 로봇 작업 시에만
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
ros2 topic list | grep -E "tb3_1|tb3_2|camera|sensor"  # 칩라·센서 토픽 보이나?

# 4. Unity 실행
python3 ~/URHYNIX/unity-smoke/run.sh  # 또는 Unity Hub에서 ControlRoom 실행
#    → ControlRoom: 맵 드롭다운에서 map5 / map5_pretty 선택
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
| Unity 맵 드롭다운에 `map5` 안 보임 | `*.png` + `*.json` 쌍 + `.meta` 2개가 `StreamingAssets/Maps/`에 있는지 확인 |
| 맵 슬롯 전환 후 화면이 까맣게 나옴 | PNG가 RGBA32가 아니거나 `widthPx/heightPx`가 0인지 JSON 확인 |

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

**2026-06-26: Confluence/Jira 동기화 + 2026/06/26 회의록(drawio 3종) + `map5` Unity 슬롯/pretty 등록 완료. 다음 세션: Unity에서 map5/m5_pretty 시각 검증 및 줌 기능 추가 여부 결정. 로봇 측은 이전 상태 유지(젠지 주행 O, 티원 apt 미설치).**
