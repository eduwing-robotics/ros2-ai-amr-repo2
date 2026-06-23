# 티원(tb3_1) RealSense D435 depth 2D SLAM — 진행 기록 (2026-06-17)

## 배경
경기장 가벽이 LDS-03 스캔 평면(~192mm)보다 낮아 **2D 라이다로는 벽이 안 잡힘**(arena_v1/v2 모두 unknown 50%). → 젠지 라이다 SLAM 중단하고 **티원 D435 depth로 매핑** 전환 결정.

## 파이프라인 (다 구축됨, 개별 부품 작동 확인)
```
RealSense depth(/tb3_1/camera/depth/image_rect_raw)
  → depthimage_to_laserscan → /scan
  → slam_toolbox(async, params yaml) → /map (글로벌)
+ static tf: tb3_1/base_link → camera_link (x0.05 z0.12, 마운트 추정·실측 보정 필요)
```
tf 체인 검증됨: `tb3_1/base_footprint → base_link → camera_link → camera_depth_frame → camera_depth_optical_frame`.

스크립트(전부 `scripts/`): `_t1_rs_depth_only.sh`(depth 재기동·작동), `_t1_slam_depth.sh`, `_t1_slamtb_relaunch.sh`(slam_toolbox launch+yaml), `_t1_scan_throttle.sh`.

## ★ 함정 (이번에 물린 것 — 다음 세션 시간 절약)
1. **`set -u` 금지**: 스크립트에 `set -u` 있으면 `source /opt/ros/jazzy/setup.bash`가 `AMENT_TRACE_SETUP_FILES: unbound variable`로 죽음. → depth가 "안 뜨던" 진짜 원인이었음.
2. **RealSense explicit depth profile 불안정**: `depth_module.depth_profile:=848x480x6`/`640x480x15` 주면 depth 스트림이 안 뜨거나 **얼어붙음**(stamp 82s 과거). → **기본값(848x480x30)으로만** 안정. 프로파일 지정하지 말 것.
3. **slam_toolbox는 sparse `-p` 금지**: `ros2 run ... async_slam_toolbox_node -p ...`로는 /scan 구독이 안 붙음(sub=0). → **`ros2 launch slam_toolbox online_async_launch.py slam_params_file:=<yaml>`** + yaml로 띄워야 구독됨.
4. **rtabmap 미설치 + sudo 비번 필요**: 티원엔 depthimage_to_laserscan만 있고 rtabmap/slam_toolbox/cartographer 없었음. slam_toolbox는 이번에 apt 설치함(사용자).
5. `/cmd_vel`은 **TwistStamped** → teleop은 `turtlebot3_teleop teleop_keyboard`.

## ✅ 해결됨 (2026-06-17 후반 — slam 드롭 0, 맵 저장 성공)
- "queue is full" 드롭의 실제 원인 **2가지**:
  1. **티원 라이다(lidar_node)가 글로벌 /scan 발행** → depth 스캔(camera_depth_frame)과 **프레임 혼재** → 드롭.
  2. scan rate(30Hz) > **odom tf(10Hz)** 불일치.
- **해결**: depth 스캔을 **전용 토픽 `/scan_depth`로 격리** + **7.3Hz throttle**(odom 이하) → 드롭 0, `/map` 라이브.
- **저장**: 티원 **nav2_map_server 미설치** → `map_saver_cli`·`slam_toolbox save_map`(255) 둘 다 실패 → **`scripts/_t1_save_map.py`**(OccupancyGrid→pgm/yaml 직접)로 성공.
- 산출: `docs/evidence/maps/arena_depth_v1/` (85×93=4.25×4.65m). depth가 라이다 못 잡던 낮은 가벽 포착 검증. 한계=좁은 FOV로 unknown 76%(더 꼼꼼한 주행 필요).
- 마스터 스크립트: `scripts/_t1_depthmap_full.sh`(리셋+RealSense+static tf+d2scan+throttle+slam 한 방).

## ⚠️ 추가 함정 (2026-06-17 재매핑 중 — slam이 갑자기 전량 드롭하면 이것부터)
- **광범위 `pkill -f turtlebot3`가 티원 bringup까지 죽임** → `tb3_1/base_footprint` 프레임 소멸 → slam이 camera_depth_frame→odom 못 풀어 **"queue is full" 전량 드롭**. 증상은 rate 문제와 똑같이 보이나 원인은 tf 체인 끊김.
- 진단: `ros2 run tf2_ros tf2_echo tb3_1/base_footprint camera_depth_frame` — Translation 안 뜨면 base_footprint 소멸.
- 복구: `scripts/_t1_bringup_only.sh`(bringup만 재기동, RealSense/slam 안 건드림) → base_footprint 복원 후 **slam은 반드시 재시작**(`_t1_slam_reset.sh`, tf 건강해진 뒤). slam이 tf 끊긴 동안 시작됐으면 메시지필터가 망가진 채 계속 드롭함.
- 교훈: 듀얼 정리 시 `pkill turtlebot3`/`single_coin` 등 **bringup 패턴을 무차별 kill 금지**. 매핑 파이프라인만 정리하려면 realsense/depthimage/slam_toolbox/scan_throttle/static_transform 패턴만.
- 진행 상태(배터리 방전으로 중단): tf 체인 복구·slam 재시작까지 함. 다음 세션은 bringup→base_footprint 확인→slam 재시작→드롭0 확인→주행→저장.

## 다음 세션 재개 레시피
1. **안정 링크 확보**: codelab_5G 근접 또는 Mac↔티원 직결([[urhynix-team-wifi-isolation-direct-link]]). 무선 불안정이 이 작업 최대 적.
2. depth 재기동: `bash /tmp/_t1_rs_depth_only.sh`(기본 프로파일). depth stamp ≈ now 확인.
3. d2scan→/scan, slam_toolbox(launch+yaml) 기동.
4. **drop 해결 검증 순서**: ① `/scan` stamp가 fresh(≈now)인지 ② scan rate를 odom(10Hz) 이하로(파이썬 throttle 릴레이 또는 depth fps) ③ 그래도 drop이면 slam_toolbox `transform_timeout` 키우고 `tf_buffer_duration` 확대, scan stamp vs odom tf 시점 정밀 비교.
5. **티원 움직여보기**: slam_toolbox는 이동 시 노드 추가 → 정지 상태 drop이 이동 중 해소되는지 확인(미검증 가설).
6. 맵 나오면 `map_saver_cli -f arena_depth_v1` → `docs/evidence/maps/arena_depth_v1/`.

## 참고
- 젠지 cartographer/라이다(`single_coin_d4_node`)는 이 세션에서 중단 시도(무선 churn으로 확정 출력 못 봄). RealSense 매핑은 젠지 라이다와 무관(다른 로봇·토픽).
- 듀얼 Unity 풀스택 검증은 별건으로 PASS([[urhynix-dual-fullstack-unity]]).
