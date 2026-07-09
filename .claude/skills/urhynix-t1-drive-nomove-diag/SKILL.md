---
name: urhynix-t1-drive-nomove-diag
description: 티원(tb3_1)이 Nav2 goal을 수락하고 피드백도 흐르는데 물리적으로 안 움직일 때의 계층 진단 트리. "로봇이 안 움직여", "goal 줬는데 정지", "순찰 시작해도 무반응", "ETA 0", "안 움직이는 이유"에 발동. 구동계→속도체인→collision_monitor→costmap→상류(Unity 발행) 순서로 이분탐색 — 2026-07-08 실전(3중 결합 원인) 도출.
user_invocable: true
tags: [ros2, nav2, turtlebot3, diagnosis, urhynix]
version: 1
---

<!-- 2026-07-08 실주행 디버깅 2시간의 증류. 원인이 "한 개"라고 가정하지 말 것 — 그날은 3중 결합이었다. -->

# 티원 "안 움직임" 계층 진단

**전제**: bringup·AMCL·nav2 8노드 active, goal은 수락됨(피드백 흐름). 그런데 바퀴가 안 돎.

## 진단 순서 (이분탐색 — 아래층부터)

### 0. 신호 읽기 — 피드백의 ETA가 말해준다
- `ETA 0.0s 고정 + 거리 불변` = **컨트롤러 무계획**(환경/체인 병) → 1~4로.
- `ETA 정상 + 거리 불변` = 물리적 낌/구동계 → 1로.
- 피드백 자체가 안 옴 = 액션/네임스페이스 문제(함정#12, [[urhynix-t1-nav2-patrol-drive]]).

### 1. 구동계 생사 (모든 상위 계층 우회)
```bash
ssh t1 '... export ROS_DOMAIN_ID=2; python3 ~/drive_rotate.py /tb3_1/cmd_vel 0.5 4'
# odom 쿼터니언 z가 변하면 구동계 무죄. ⚠️ ros2 topic pub은 "rcl context invalid"로
# 조용히 실패할 수 있어(2>&1 숨기면 오진) — 반드시 rclpy 스크립트로.
```

### 2. 속도 체인 — 반드시 동시 측정
`cmd_vel_nav`(컨트롤러) → `cmd_vel_smoothed`(스무더) → `cmd_vel`(모니터 출력, turtlebot3_node 입력).
순차 hz 측정 금지(측정 사이 goal 취소로 오판) — **rclpy 하나로 3토픽 동시 카운트 8초**.
- nav만 흐름 → 스무더/모니터 층. **모니터 출력만 0 = collision_monitor가 STOP 상태로 삼킴** → 3.
- nav부터 0 → 컨트롤러/costmap → 4.

### 3. collision_monitor 차단 사유
```bash
grep collision_monitor /tmp/nav_tb3_1.log | tail
```
| 로그 | 원인 | 해결 |
|---|---|---|
| `Robot to stop due to PolygonStop` | 최소거리가 문턱(0.14) 부근 — 구석/독 정차. **라이다≠로봇중심 오프셋** 때문에 라이다 0.20도 걸릴 수 있음 | 8방위 트인쪽으로 직접 cmd_vel 탈출(0.05m/s, 0.2m 상한) 후 재시작 |
| `timestamps differ ... Ignoring the source` → `invalid source` | scan source_timeout(구 0.2) < Pi 부하 지연 0.2~0.36s | source_timeout 1.0 (patch_nav_params_ns.py 반영됨) |

### 4. costmap 굶주림
```bash
grep -E "Message Filter dropping|KeepoutFilter" /tmp/nav_tb3_1.log | tail
```
- `KeepoutFilter: Filter mask was not received` = keepout 마스크 서버 미기동(재부팅 소실) → `_keepout_filter_up.sh` 또는 params에서 filters 키 제거+재기동.
- `Message Filter dropping ... earlier than transform cache` = activate 직후 과도기면 무시, goal 중 지속이면 scanfix(`urhynix-scanfix` 서비스) 생사 확인.
- 참고: tf는 전역 `/tf`로 흐름(`/tb3_1/tf` 아님 — nav_ns_launch가 리매핑 제거한 이유).

### 5. 상류(Unity) — 발행이 로봇에 오긴 하나
bridge 저널에 수신 로그가 없으면 로봇 문제가 아님:
```bash
ssh t1 'journalctl --user -u urhynix-bridge -n 10 --no-pager'   # "N점 수신" 없으면 상류
ssh t1 'journalctl --user -u urhynix-endpoint --no-pager | grep RegisterPublisher'
```
- RegisterPublisher(/tb3_1/patrol_waypoints)가 없다 = Unity 발행자가 **공유 기본 연결**(`Resources/RosConfig/ros_endpoint.json`의 endpointRobotId)로 나감 — 그 로봇이 꺼져 있으면 전부 유실. endpointRobotId를 산 로봇으로 바꾸고 **Play 재시작**(Resources 캐시).

## 실측 사례 (2026-07-08 — 3중 결합)
keepout 마스크 부재(costmap 미완성) **+** source_timeout 0.2 초과(모니터 상시 정지) **+** 독 구석 정차(PolygonStop 발동)가 동시에 겹침. 하나 풀 때마다 다음 층이 드러났다 — **한 층 고치고 끝났다고 단정하지 말고 트리를 끝까지 내려갈 것.** 최종적으로 1.5m 실주행 확인.

## 관련
[[urhynix-t1-nav2-patrol-drive]] 함정#13~19(원인 표) · [[urhynix-t1-amcl-saved-map]] · `scripts/nav2_goal_t1.py`(표준 주행) · `scripts/robot_services/`(상주 4서비스)
