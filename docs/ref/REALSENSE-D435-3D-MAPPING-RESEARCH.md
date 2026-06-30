# RealSense D435 3D Mapping Research Handoff

Last updated: 2026-06-25

이 문서는 다음 세션에서 RealSense D435 기반 3D 맵/디지털트윈 작업을 이어받기 위한 리서치 메모다. 아직 하드웨어 실검증이 끝난 실행 계획이 아니며, 각 항목은 `Verified`, `Repo-observed`, `Source-backed`, `Unverified`로 상태를 표시한다.

## Current Project Context

| 항목 | 상태 | 메모 |
|---|---|---|
| LDS-03 2D SLAM/Nav2 맵 | Verified | 현재 Unity는 `.png + .json` 슬롯의 `origin/resolution/widthPx/heightPx`로 1:1 좌표를 유지한다. `arena_v4` 검증됨. |
| `arena_v4_pretty` 2D 관제 천장뷰 | Verified | 1024x1024 발표용 이미지 생성. 좌표 메타는 원본 `arena_v4`와 동일. |
| pretty 자동 후처리 | Verified | `scripts/pgm_to_map_slot.py`가 새 슬롯 생성 후 `*_pretty`를 자동 생성한다. |
| D435 하드웨어 존재 | Verified | T1(ti@192.168.10.250)에 Intel RealSense D435 탑재. Serial 254522075185, FW 5.17.0.10, USB 3.2. |
| D435 ROS2 토픽명 | Verified | T1 결과: `/tb3_1/camera/aligned_depth_to_color/image_raw`, `/tb3_1/camera/color/image_raw`, `/tb3_1/camera/camera_info`. pointcloud.enable 미declare라 `/camera/points` 미생성. |
| D435로 3D 맵 생성 (Offline Path B) | Verified | 제자리 360° rosbag(aligned_depth+color) 캡처 → Mac deproject+odom tf 누적 → PLY 복원. 1200만점 컬러 점군 성공. `docs/evidence/3d_maps/2026-06-25-d435-rot/rot360_odom.ply`. |
| ROS_DOMAIN_ID | Verified | 운영 도메인: 210 (문서 230은 오류). |
| rosbag record 폭주 | Verified | 방지: `timeout --signal=INT` 사용. |
| odom tf 누적 | Verified | 경로 B 성공. loop closure 없어 드리프트 있음. RTAB-Map A/B 보류 중. |
| D435로 2D 맵 보정 | Unverified | 가능성 높음. 검증 전 Nav2 정적 맵 병합 금지. Phase 2C 예정. |

## Decision So Far

주인님이 원하는 방향은 단순 주행 회피 보강이 아니라, OneCanvas 같은 **viewpoint 기반 3D scene/digital twin viewer**다.

따라서 다음 목표는:

1. LDS-03 2D map은 계속 좌표 정본으로 둔다.
2. D435 RGB-D 데이터를 오프라인으로 수집한다.
3. RGB-D + pose/tf를 map 좌표계 point cloud로 누적한다.
4. Unity에서 `arena_v*_pretty` 2D 맵과 연결된 3D scene cloud/viewpoint viewer를 만든다.
5. 2D 보정은 별도 보조 산출물로 남기고, 검증 전 Nav2 static map에 병합하지 않는다.

## OneCanvas-Inspired Interpretation

OneCanvas는 여러 시점 image patch를 depth와 camera pose로 3D world coordinate에 올린 뒤, 선택한 origin 기준의 equirectangular panorama canvas에 다시 투영한다. 이 방식의 핵심은 "모든 frame/patch가 하나의 3D 공간 좌표계를 공유한다"는 점이다.

URHYNIX에 맞춘 실용 버전:

| OneCanvas 개념 | URHYNIX 실용 대응 |
|---|---|
| image patch feature | RGB frame의 저해상도 patch 또는 point color |
| metric depth | D435 depth image 또는 PointCloud2 |
| camera-to-world pose | `map -> base_link -> camera_link` TF |
| continuous longitude/latitude canvas | Unity viewpoint panorama/scene strip |
| source-frame color/rays | 캡처 위치별 marker/ray 색상 |
| situated question viewpoint | 2D 맵의 capture marker 클릭 → 해당 위치의 3D view로 이동 |

### Recommended MVP

`D435 RGB-D rosbag -> map-frame pointcloud export -> PLY/GLB -> Unity 3D viewer + 2D viewpoint markers`

이 MVP는 실시간보다 덜 위험하고, 발표 효과가 크며, 기존 Nav2 주행 안정성을 건드리지 않는다.

## Approaches Compared

| 접근 | 용도 | 추천도 | 상태 | 이유 |
|---|---|---:|---|---|
| Offline RGB-D point cloud export | 발표용 3D scene map | 5/5 | Source-backed, Unverified locally | 주행에 영향 없이 D435 데이터를 3D로 보여줄 수 있다. |
| Unity viewpoint viewer | OneCanvas식 관제 경험 | 5/5 | Design only | 2D pretty 맵과 연결하기 쉽고 발표 효과가 좋다. |
| `pointcloud_to_laserscan` | 낮은 가벽 2D 보정/회피 | 4/5 | Source-backed, Unverified locally | 3D PointCloud를 2D LaserScan으로 바꿔 기존 2D 알고리즘에 넣을 수 있다. |
| Nav2 ObstacleLayer + `/camera/scan` | 주행 중 동적 회피 | 4/5 | Source-backed, Unverified locally | 정적 맵 오염 없이 D435를 보조 obstacle source로 쓸 수 있다. |
| Nav2 Voxel Layer/STVL | 3D obstacle handling | 3/5 | Source-backed, Unverified locally | 가능하지만 처음부터 쓰기엔 설정/성능 리스크가 크다. |
| RTAB-Map full RGB-D SLAM | 3D/2D SLAM | 2/5 | Source-backed, Unverified locally | 시각 효과는 좋지만 TurtleBot/RPi 쪽 부하와 튜닝 리스크가 크다. |
| D435 result를 `.pgm/.yaml`에 영구 병합 | 정적 맵 보정 | 1/5 | Risk flagged | calibration/noise/static성 검증 전에는 맵 정본 오염 위험이 크다. |

## Minimal Next-Session Smoke Plan

### Phase A: Data Existence Smoke

목표: T1 D435가 실제로 ROS2에서 depth/pointcloud를 낼 수 있는지 확인.

```bash
ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=424x240x15 \
  enable_color:=false \
  pointcloud.enable:=true \
  pointcloud.ordered_pc:=false \
  align_depth.enable:=false
```

확인:

```bash
ros2 topic list | grep -E 'camera|points|depth'
ros2 topic hz /camera/camera/depth/color/points
ros2 topic echo /camera/camera/depth/color/points --once
```

성공 기준:

- PointCloud2 토픽이 나온다.
- 5Hz 이상 유지된다.
- RViz에서 fixed frame과 TF를 맞추면 점군이 보인다.

실패 기준:

- D435 USB/권한 문제.
- pointcloud topic 없음.
- TF가 없어 RViz에서 좌표 변환 실패.
- CPU 과부하로 TurtleBot bringup/odom이 흔들림.

### Phase B: Offline 3D Map Smoke

목표: rosbag을 짧게 떠서 pointcloud를 `.ply`로 export.

기록 후보:

```bash
ros2 bag record \
  /camera/camera/depth/color/points \
  /tf /tf_static /odom
```

다음 세션 구현 후보:

- `scripts/d435_bag_to_ply.py`
- input: rosbag 또는 sampled PointCloud2
- output: `docs/evidence/3d_maps/<name>/<name>.ply`
- downsample: voxel grid 또는 N프레임 간격 sampling
- transform: `map` 또는 `odom` 기준으로 누적

성공 기준:

- `.ply`가 생성된다.
- MeshLab/CloudCompare/Unity 중 하나에서 열린다.
- 2D map의 대략적인 벽/가벽 위치와 육안으로 맞는다.

### Phase C: Unity 3D Viewer Smoke

목표: Unity ControlRoom에서 3D scene cloud를 별도 보기 모드로 표시.

MVP:

- 2D `arena_v*_pretty` 위 capture marker 표시
- marker 클릭 시 3D 점군 view로 이동
- 처음에는 실시간 ROS-TCP PointCloud2 수신 금지
- `.ply` 또는 `.glb` 로컬 파일 로드 우선

성공 기준:

- 2D 맵 좌표와 3D 점군 anchor가 같은 map origin/resolution 체계로 설명된다.
- 3D view가 발표용으로 볼만하다.
- Unity 조작 화면의 좌표 클릭/출동 기능은 기존 2D에서 유지된다.

## 2D Correction Policy

D435 3D 결과로 2D 보정은 가능하지만, 단계별로 격리한다.

1. **Visual overlay only**: D435에서 추출한 낮은 장애물 후보를 Unity에 다른 색 레이어로 표시.
2. **Local costmap only**: `/camera/scan`을 Nav2 local costmap obstacle source로 사용.
3. **Static map merge**: 아래 조건을 모두 만족할 때만 검토.

정적 병합 조건:

- D435 외부파라미터(`base_link -> camera_link`)가 실측 검증됨.
- 같은 장애물이 여러 pose/frame에서 같은 map 좌표에 반복 검출됨.
- 장애물이 실제로 정적 구조물임.
- 표면 반사/조도/무늬 때문에 depth hole이 심하지 않음.
- LDS-03 map과 D435 projection의 오차가 발표/주행 허용치 안에 들어옴.

병합 금지 조건:

- 한 번만 보인 장애물.
- 바닥면이 벽처럼 보이는 ghost wall.
- 유리/반사/무광 단색 등 depth가 불안정한 표면.
- 카메라 pitch/roll 오차가 확인되지 않음.
- Nav2가 열린 공간을 막힌 공간으로 판단하기 시작함.

## Implementation Notes

### Keep These Separate

| 산출물 | 목적 | Nav2 정본 여부 |
|---|---|---|
| `arena_v*.pgm/yaml` | LDS-03 SLAM 정본 | Yes |
| `arena_v*_pretty.png/json` | 2D 발표/관제 천장뷰 | No, visual only |
| D435 `.ply/.glb` | 3D scene cloud | No, visual/evidence |
| D435 low obstacle overlay | 2D 보정 후보 | No, until verified |
| `/camera/scan` | dynamic obstacle source | Local costmap only |

### Possible File Targets

- `scripts/d435_bag_to_ply.py` - rosbag/PointCloud2 to PLY export.
- `scripts/d435_pointcloud_smoke.sh` - D435 + topic smoke.
- `unity/ControlRoom/Assets/Scripts/Map/Map3DSceneCloudLayer.cs` - local point cloud viewer.
- `unity/ControlRoom/Assets/Scripts/Data/MapCapturePoseInfo.cs` - capture pose metadata.
- `docs/evidence/3d_maps/<session>/` - generated `.ply`, screenshots, notes.

## Source Notes

### Source-backed

- OneCanvas project page: multi-view patch features are lifted to 3D using depth and camera pose, then projected to a single equirectangular canvas. This supports viewpoint-centered reasoning.  
  https://baranowskibrt.github.io/onecanvas/
- OneCanvas arXiv record, submitted 2026-06-17, describes the same depth+pose unprojection and panoramic reprojection concept.  
  https://arxiv.org/abs/2606.19253
- `pointcloud_to_laserscan` Jazzy docs: converts 3D PointCloud into 2D LaserScan, useful for making RGB-D devices appear like a laser scanner for 2D algorithms.  
  https://docs.ros.org/en/jazzy/p/pointcloud_to_laserscan/
- Nav2 Voxel Layer docs: uses 3D raycasting for depth/3D sensors and squashes the model down to 2D for planning/control.  
  https://docs.nav2.org/configuration/packages/costmap-plugins/voxel.html
- Nav2 STVL tutorial: demonstrates loading external costmap plugins, using STVL as the example.  
  https://docs.nav2.org/tutorials/docs/navigation2_with_stvl.html
- RealSense ROS2 wrapper docs mention ROS2 wrapper parameters such as enabling depth/color, alignment, sync, and pointcloud behavior.  
  https://dev.realsenseai.com/docs/ros2-wrapper/  
  https://github.com/realsenseai/realsense-ros
- Intel D435 official product specs identify D435 as a depth camera with RGB sensor and no tracking module; operating range is listed around 0.3m-3m in official specs.  
  https://www.intel.com/content/www/us/en/products/sku/128255/intel-realsense-depth-camera-d435/specifications.html

### Downloaded Report Reviewed

Local file:

```text
/Users/family/Downloads/ROS2 디지털트윈 장애물 회피 구축.md
```

Useful parts:

- LDS-03 static map should remain the global map.
- D435 should initially be a dynamic/visual supplement.
- `pointcloud_to_laserscan` is a practical bridge from 3D depth to 2D Nav2-compatible data.
- Static `.pgm/.yaml` merge is risky before calibration and repeatability checks.

Needs verification/caution:

- Some numeric thresholds and performance claims are not locally verified.
- Several inline equations/images are broken in markdown.
- ROS-TCP/Unity pointcloud performance claims need local profiling.
- STVL as "best single approach" is too aggressive for first implementation; use it only after `pointcloud_to_laserscan` smoke.

## Open Questions (2026-06-25 갱신)

1. ✅ T1 D435 ROS2 토픽명: `/tb3_1/camera/aligned_depth_to_color/image_raw`, `/tb3_1/camera/color/image_raw`, `/tb3_1/camera/camera_info` (pointcloud 미생성).
2. ✅ `realsense2_camera` 설치 (pointcloud_to_laserscan는 미확인).
3. ❓ D435 외부파라미터 (`base_link -> camera_link` x/y/z/roll/pitch/yaw) 정밀 측정 필요 (현재 기본값).
4. ✅ T1 CPU: aligned_depth+color rosbag 스트리밍은 bringup/Nav2 안정성 미영향. 오프라인 deproject도 OK.
5. ❓ Unity 3D 뷰어: `.ply` 로드 테스트 필요 (Phase 3).
6. ✅ 점군 anchor: odom 누적으로 성공 (drfit 있음, map으로 보정 후보).
7. ❓ Phase 2B: RTAB-Map 실시간 vs 오프라인 비교.
8. ❓ Phase 2C: D435 low obstacle → 2D overlay/local costmap/static merge.

## Next Recommended Prompt

```text
T1 RealSense D435로 30초 rosbag을 떠서 map/odom 기준 pointcloud PLY를 만들고, Unity ControlRoom에서 arena_v*_pretty 2D 맵과 연결된 3D scene cloud preview로 여는 최소 스모크를 구현해줘. 검증 전 Nav2 static map 병합은 하지 말고, D435 결과는 visual/evidence 레이어로만 유지해줘.
```
