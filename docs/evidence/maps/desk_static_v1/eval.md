# SLAM 첫 검증 — desk_static_v1

> 2026-05-29 첫 SLAM end-to-end 검증 결과. 정적 매핑 (책상 위, robot 가만히 1분).

## 메타데이터

| 항목 | 값 |
|---|---|
| 일시 | 2026-05-29 14:42 KST |
| 장소 | 책상 위 (개발 환경, 미니 검증) |
| 매핑 방식 | 정적 (robot 가만히, LiDAR 360° 1분) |
| 매핑 시간 | 30s + 저장 |
| 주행 거리 | 0 (정적) |
| cartographer 실행 위치 | **로봇 직접** (Mac Docker/UTM 우회) |

## 산출물

- `desk_static_v1.pgm` — 12.7 KB 회색조 점유 그리드
- `desk_static_v1.yaml` — 메타데이터
- `desk_static_v1.png` — Unity 임포트용 (PIL 변환)

## 정량 지표

| 지표 | 측정 | 목표 | PASS/FAIL |
|---|---|---|---|
| resolution (m/pixel) | 0.050 | 0.05 | ✅ |
| 점유 그리드 너비(px) | 118 | — | — |
| 점유 그리드 높이(px) | 108 | — | — |
| 실제 너비 = px × resolution (m) | 5.90 | — | — |
| 실제 높이 = px × resolution (m) | 5.40 | — | — |
| origin (ROS) | (-3.613, -2.847, 0) | — | — |
| `/map` publish rate | 1.0 Hz | ≥ 0.5 Hz | ✅ |
| `/scan` publish rate | 10.0 Hz | ≥ 5 Hz | ✅ |

## Unity Plane scale 계산

```
이미지: 118 × 108 px
resolution: 0.05 m/px
실제 크기: 5.90 m × 5.40 m
Unity Plane (10u 기본):
  scale.x = 0.5900
  scale.z = 0.5400
  scale.y = 1
```

Unity Editor에서 Plane GameObject에 위 scale 그대로 입력 + Material에 `Assets/Maps/desk_static_v1.png` 텍스처 할당.

## 정성 평가

- ✅ end-to-end 흐름 (LiDAR → cartographer → /map → map_saver → host scp → PNG → Unity scale 자동 계산) 모두 작동
- ✅ ROS2 멀티캐스트 모드에서 robot 내부 cartographer 통신 깨끗
- ⚠️ 정적 매핑이라 점유 그리드는 robot 주변 5.9×5.4m 범위만. 진짜 경기장 매핑 시에는 teleop 주행 필요
- ⚠️ 매핑 품질 정량 평가 (드리프트, 루프클로저)는 정적이라 측정 의미 없음

## 재현 명령

```bash
. ~/.tb3rc && . ~/jason/URHYNIX/scripts/tb3.sh
tb3-up                    # bringup + ros_tcp tmux
sleep 12
tb3-slam                  # cartographer tmux (multicast 모드, ROS_DISCOVERY_SERVER 미사용)
sleep 30                  # /map 누적 대기
# 맵 저장 (robot 측)
ssh kim@$(tb3-ip) 'bash -c "source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=56 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && cd ~/maps && ros2 run nav2_map_server map_saver_cli -f desk_static_v1"'
tb3-fetch-map desk_static_v1
tb3-map-to-unity desk_static_v1
```

## 학습

1. **Robot 직접 SLAM이 가장 빠른 길** — Mac Docker(host networking inbound 미라우팅) / Multipass(QEMU hang) / UTM(QEMU bridged hang) 모두 우회. RPi 4 + LDS-03은 작은 매핑(5×5m 책상 환경)에 충분.
2. **ROS2 환경 변수 모드 통일 필수** — bringup이 Discovery Server 모드면 cartographer도 같은 모드여야 통신. 양쪽 multicast(SUBNET) 모드가 가장 단순.
3. **scp brace expansion 비호환** — `scp host:dir/{a,b}` 패턴이 macOS scp client에서 분리 안 됨. `.pgm`과 `.yaml` 분리 scp 안전.
4. **tb3-slam helper의 환경변수가 ROS_DISCOVERY_SERVER 미명시 = multicast 모드 default** — bringup이 multicast이면 자연스럽게 통신.

## 다음 단계

- 경기장(박물관·미술관 액자 보호 환경) waypoint 측정 시: teleop 주행 + 25분 매핑
- Nav2 1-waypoint 베이스라인: tb3-nav2 + RViz Goal 클릭
- 다중 trajectory: cartographer는 여러 세션 트래젝토리 누적 가능 (이번 0번)
