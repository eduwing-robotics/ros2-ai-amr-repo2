# SLAM arena 평가 — arena_depth_v1 (RealSense depth 매핑)

- 일시: 2026-06-17 14:59 KST
- 대상: 티원(tb3_1) + **Intel RealSense D435 depth** (라이다 아님)
- 파이프라인: depth(/tb3_1/camera/depth/image_rect_raw) → depthimage_to_laserscan(/scan_raw) → python throttle 7.3Hz(/scan_depth) → **slam_toolbox**(async, /map)
- 저장: nav2_map_server 미설치 → **파이썬 OccupancyGrid 세이버**(`scripts/_t1_save_map.py`)

## 정량 지표
| 지표 | 측정 | 비고 |
|---|---|---|
| resolution | 0.05 m/px | |
| 그리드 | 85 × 93 px | |
| 실제 크기 | **4.25 × 4.65 m** | 라이다 맵(3.15×3.05) 대비 확장 |
| 벽(occupied) | 5.9% | |
| 통로(free) | 17.7% | |
| 미매핑(unknown) | **76.4%** | D435 좁은 FOV(~70°) → 전방 cone만, 측면 미매핑 |
| origin | [-0.672, -3.544, 0] | |

## 의의 (왜 이게 중요한가)
- **2D 라이다(LDS-03)는 경기장 낮은 가벽을 못 잡음**(스캔 평면 ~192mm > 가벽) → arena_v1/v2 unknown 50%, 벽 거의 안 잡힘.
- **RealSense depth는 카메라 높이/각도로 낮은 가벽을 포착** → 닫힌 공간 윤곽이 맵에 나타남. depth 매핑이 이 경기장의 올바른 접근임을 검증.

## 한계 / 다음
- depth FOV가 좁아 unknown 76% — **더 꼼꼼한 주행**(벽마다 카메라 정면으로 천천히 스윕) 필요. arena_depth_v2로 확장.
- depth 매핑 안정화의 핵심 픽스(아래)는 [[2026-06-17-t1-realsense-depth-slam]] 및 스크립트에 자산화.

## 핵심 픽스 (slam 드롭 0 달성)
1. **`set -u` 금지** (ROS setup.bash AMENT unbound 충돌).
2. **RealSense 기본 depth 프로파일만**(explicit profile은 스트림 동결).
3. **slam_toolbox는 launch+yaml**(sparse `-p`는 /scan 구독 안 붙음).
4. **depth 스캔을 `/scan_depth` 전용 토픽으로** 라이다(/scan)와 분리 + **7.3Hz throttle**(odom 10Hz 이하) → message-filter "queue full" 드롭 0.
5. 저장: nav2 없으면 `_t1_save_map.py`(OccupancyGrid→pgm/yaml 직접).

## 첨부
- arena_depth_v1.pgm (85×93) · arena_depth_v1.yaml · arena_depth_v1.png
