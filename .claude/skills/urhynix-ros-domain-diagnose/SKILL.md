---
name: urhynix-ros-domain-diagnose
description: 로봇이 Unity 맵에 안 뜨거나 /map·/tf가 엉키거나 노드가 두 개씩 보이거나 "라이다 안 켜진 것 같다"일 때, ROS_DOMAIN_ID 210의 진짜 상태(ground truth)를 찾아 충돌원·고장원을 root-cause하는 진단 플레이북. 단일/듀얼 bringup 착수 전에 도메인을 깨끗이 만드는 선행 단계. ros2 node list 유령노드, 비-ns 멀티로봇 글로벌 토픽 충돌, OpenCR 크래시 시그니처를 감별한다.
---

# URHYNIX ROS 도메인 Ground-Truth 진단

## 목적

`urhynix-dual-fullstack-unity`(클린 셋업의 *처방*)와 짝을 이루는 *진단* 스킬. 이미 엉킨 도메인 210에서 "왜 로봇이 안 뜨나"를 추측이 아니라 ground truth로 잡는다. bringup 착수 전에 도메인을 1대만 남기고 정리한다.

## 발동 트리거

- "로봇이 맵에 안 뜸 / 마커 안 보임", "맵·tf가 이상함", "노드가 두 개씩 보임", "라이다 안 켜진 듯", "젠지 OFF인 줄 알았는데", "단일 로봇 검증 전 정리".

## 핵심 원리 (성역: 검증은 추측 금지)

- **`ros2 node list`는 거짓말한다** — ros2 daemon이 죽은 노드를 캐시로 한동안 보여줌. `ros2 daemon stop; ros2 daemon start` 후에도 남으면 **라이브(타 호스트)**. 실프로세스는 `pgrep -af`, 실발행은 `ros2 topic hz`로 교차검증.
- **노드가 2개씩(`lidar_node` x2, `diff_drive_controller` x2, `robot_state_publisher` x2) = 복수 비-ns 스택 동거** → 글로벌 `/scan`·`/tf`·`/map` 충돌. 단일 검증 불가.
- **단일 검증 전 다른 로봇·PC 세션을 전부 끈다** — 안 끄면 글로벌 토픽 오염으로 localize·마커가 계속 깨진다.

## 절차

### Step 1 — 진짜 프로세스 vs 유령 노드 감별

```bash
# 대상 로봇에서(예: 티원)
ssh t1@<ip> 'pgrep -af "turtlebot3_node|lidar_node|coin_d4|cartograph|rviz|default_server_endpoint|basic_nav|go_to_goal" | grep -v pgrep'
# daemon 새로고침 후 노드 목록(라이브만 남음)
ssh t1@<ip> 'bash -lc "source /opt/ros/jazzy/setup.bash; source \$HOME/turtlebot3_ws/install/setup.bash; export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp; ros2 daemon stop>/dev/null 2>&1; ros2 daemon start>/dev/null 2>&1; sleep 4; ros2 node list | sort"'
```
- `pgrep` 비었는데 `node list`에 노드가 있다 → **그 노드는 타 호스트에 있다**.

### Step 2 — 발행원 호스트 식별

```bash
# 라즈베리파이 OUI로 ARP 스캔 (티원 d8:3a:dd / 젠지 2c:cf:67 / 구형 b8:27:eb)
arp -a | grep -iE "d8:3a:dd|2c:cf:67|b8:27|dc:a6"
# 후보 호스트마다 ssh로 실프로세스 확인
ssh kim@<genji_ip> 'pgrep -af "turtlebot3_ros|coin_d4|cartograph|rviz" | grep -v pgrep'
# 실발행 확인(유령 아님 증명)
ros2 topic hz /scan --window 10   # average rate 나오면 누군가 실발행 중
```
- 젠지 = `kim@192.168.10.84`(hostname `kim-desktop`, coin_d4). 티원 = `t1@192.168.10.250`. IP는 DHCP drift 정상(메모리 `project_robot_ip_dynamic`) → ARP+ssh로 매번 재확인.
- `rviz2`·`basic_navigator`·`go_to_goal`는 보통 **GUI PC**(.82/.50 등)에 있고 ssh가 막힐 수 있음 → 주인님이 그 창에서 직접 종료.

### Step 3 — 도메인 정리 (1대만 남기기)

```bash
# self-kill 회피 bracket trick (메모리 pkill-f-self-kill-ssh)
ssh <host> 'for p in "[t]urtlebot3" "[c]oin_d4" "[s]ingle_coin" "[d]iff_drive" "[r]obot_state_pub" "[d]efault_server_endpoint" "[l]idar_node" "[r]obot.launch" "[c]artograph" "[r]viz" "[b]asic_nav" "[g]o_to_goal"; do pkill -9 -f "$p" 2>/dev/null; done; sleep 3'
```
- 못 끄는 PC 세션은 주인님 수동. 정리 후 Step 1로 도메인이 조용한지 재확인.

### Step 4 — bringup 후 고장원 감별

clean bringup(`urhynix-fullstack-bringup`/`urhynix-dual-fullstack-unity`)을 띄운 뒤 증상별 root-cause:

| 증상 | 판정 | 조치 |
|---|---|---|
| `/scan` hz 정상 + 휠 tf 정상 + **`odom` 프레임 없음** + log `There is no status packet` / `stack smashing detected` / `exit code -6` | **OpenCR/다이나믹셀 고장** (라이다 아님 — `/scan` 정상이 감별점) | ①배터리 충전 11.5V↑ ②OpenCR 전원버튼·USB(`/dev/ttyACM0`) 재연결 ③펌웨어 재플래시 |
| bringup 즉사 `KeyError: 'LDS_MODEL'` | env 누락 | 스크립트에 `export LDS_MODEL=LDS-03 TURTLEBOT3_MODEL=burger` |
| `map→base_footprint` 없음 (but odom OK) | SLAM/AMCL 미동작 | cartographer(SLAM) 또는 AMCL+map_server(저장맵) 기동 |

## 함정

- **ssh `bash -c` echo 문자열에 괄호 `()` 금지** — 셸이 `syntax error near unexpected token (`로 깨짐. 괄호 빼고 작성.
- **비대화 `bash -lc`는 ROS setup을 자동 source 안 함** — `nohup ros2`가 `No such file or directory`. 명시적으로 `source /opt/ros/jazzy/setup.bash; source ~/turtlebot3_ws/install/setup.bash`.
- **macOS엔 `timeout` 없음** — ssh `ConnectTimeout` 옵션 또는 `(cmd & p=$!; sleep N; kill $p)` 패턴.
- **백그라운드 launch는 `setsid nohup bash /tmp/x.sh >log 2>&1 </dev/null &`** (`_t1_map_nonns.sh` 패턴).

## Verify

- `pgrep` + `topic hz` + (필요시) `tf2_echo`로 ground truth 3중 확인 — `node list` 단독 신뢰 금지.
- 정리 후 도메인에 의도한 로봇 1대(또는 ns 분리된 N대)만 남는다.
- 고장 판정은 log 시그니처 + 프레임 존재 여부로 근거를 남긴다.

## Outputs

- 도메인 토폴로지 1표(호스트 × 프로세스) + 충돌/고장 root-cause + 다음 조치.

## 관련

- `urhynix-dual-fullstack-unity`(듀얼 클린 셋업 처방), `urhynix-fullstack-bringup`(단일 5트랙), `robot-ip-detect-fallback`/`ip-drift-resync`(IP drift), `ros2-noninvasive-pose-tap`(엔드포인트 비침습 탭), `urhynix-robot-shutdown`(셧다운). 메모리: `pkill-f-self-kill-ssh`, `project_robot_ip_dynamic`, `urhynix-robot-sudo-passwords`.
