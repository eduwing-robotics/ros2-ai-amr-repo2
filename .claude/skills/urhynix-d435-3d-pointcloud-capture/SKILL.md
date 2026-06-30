---
name: urhynix-d435-3d-pointcloud-capture
description: 티원(TurtleBot3+RealSense D435)으로 RGB-D를 rosbag 캡처하고 Mac에서 odom tf로 누적해 컬러 3D 점군(PLY)으로 복원하는 표준. 제자리 360° 회전(단독) 또는 동료 teleop 주행(협업) 둘 다 지원. "3D 점군", "d435 포인트클라우드", "포인트클라우드 맵", "점군 캡처", "3d 스캔해줘", "rgb-d 맵", "디지털트윈 3d 떠줘", "동료랑 3d 매핑", "teleop 3d", "협업 3d 매핑" 요청에 발동. 디지털트윈 3D scene/viewpoint viewer의 입력을 만든다. Unity 3D 뷰어(별도)와 RTAB-Map A/B 비교의 앞단.
---

# URHYNIX D435 3D 점군 캡처

티원 D435로 공간을 3D 컬러 점군으로 떠서 디지털트윈/발표용 3D scene을 만든다. LDS-03 2D 맵(arena_v*)은 정본으로 두고 건드리지 않는다.

## 핵심 결정 — 경로 B (티원 캡처, Mac 복원)

RealSense wrapper 4.57은 `pointcloud.enable`을 **declare 안 함** → 티원에서 PointCloud2 생성 불가(`re-enable the stream` 경고 후 토픽 안 뜸). 대신:
- **티원**: `aligned_depth_to_color`(color frame 정렬 depth) + color + camera_info만 가볍게 rosbag record. 라즈베리 CPU/RAM 부하 최소.
- **Mac**: `rosbags`(ROS 설치 불필요, 순수 python)로 읽어 deproject + odom tf 누적 → PLY.

6/17 메모리 "Pi는 캡처, Mac이 본체" 원칙과 일치. RTAB-Map(2/5)보다 가볍고 발표 효과 큼.

## 상수 (2026-06-25 실측)
- 도메인: **`ROS_DOMAIN_ID=210`** (robot-camera-bringup 문서의 230은 오류 — 스크립트가 맞음)
- 토픽: `/tb3_1/camera/aligned_depth_to_color/image_raw`(Z16, mm), `.../camera_info`(intrinsics), `/tb3_1/camera/color/image_raw/compressed`
- intrinsics(640x480): fx≈604.5 fy≈603.2 cx≈324.1 cy≈254.2
- tf 사슬: `tb3_1/odom → base_footprint → base_link →(static 추정)→ camera_link → camera_color_optical_frame`
- 회전 토픽: `/tb3_1/cmd_vel` = **TwistStamped** (turtlebot3_node 구독, 매틱 현재 stamp 필요)

## 절차

### 0. D435 PointCloud 스모크
`scripts/_t1_rs_pointcloud.sh` (scp → bash). `align_depth.enable:=true`, 640x480x15. aligned depth 14~15Hz·USB3(5000M, bcdUSB 3.2) 확인.

### 1. odom 확보 (bringup)
`scripts/_t1_bringup_only.sh <mac_ip>`. `/tb3_1/odom` ~20Hz + `tb3_1/base_footprint` tf 확인. OpenCR(/dev/ttyACM0) 통신 필수.

### 2. base_link → camera_link static tf
```bash
ros2 run tf2_ros static_transform_publisher --x 0.04 --z 0.10 \
  --frame-id tb3_1/base_link --child-frame-id camera_link
```
`ponytail:` 마운트 실측 전 추정값(전방 4cm·위 10cm·수평 정면). 정밀 정합 필요 시 실측 x/y/z/rpy로 보정.
검증: `ros2 run tf2_ros tf2_echo tb3_1/odom camera_color_optical_frame` → Translation 나오면 사슬 완성.

### 3. 회전 record
로봇을 공간 **중앙**(벽까지 ~1.4m = D435 sweet 0.3~3m)에 들어서 옮기고(밀면 odom 오염), 충전 케이블 분리. 2~3초 정지 후:
`bash /tmp/d435_record_smoke.sh 0.3 21` — record(`timeout --signal=INT`로 자동종료) + drive_rotate TwistStamped 제자리 ~360°.

### 4. Mac 복원
```bash
scp -r t1:/tmp/d435_rot_<ts> docs/evidence/3d_maps/<session>/
uv venv /tmp/plyenv && uv pip install --python /tmp/plyenv/bin/python rosbags numpy pillow
/tmp/plyenv/bin/python scripts/d435_bag_to_ply.py <bagdir> -o out.ply --accumulate --frames 0 --stride 3 --zmax 3.5
```

### 5. 시각 검증 (성역 — 추측 금지)
탑다운(odom x-y) 렌더에서 **로봇 원점 주위 360° 벽 분포 = 성공**. 제자리면 부채꼴 하나만. numpy 비닝 PNG → 육안.
- 뷰어 없이 빠른 확인: `scripts/ply_render.py <ply> -o out.png [--turntable]` (탑다운+정면 또는 4각도 3D, matplotlib 불필요).
- 인터랙티브 3D: `brew install --cask cloudcompare` → `open -a CloudCompare <ply>` (좌드래그 회전·휠 줌, Colors→RGB).

## 협업 변형 — teleop 다중 세그먼트 (2026-06-26 PASS)
단독 360° 회전은 한 자리만 봐서 가림이 큼. **동료가 teleop으로 천천히 외곽 한 바퀴**(벽 0.3~3m, 급회전·들어올리기 금지)면 시점이 쌓여 3D가 꽉 참. 단계 0~2는 동일, 3·4만 교체:
- **3′. 회전 없는 record**: `bash /tmp/d435_record_only.sh <secs>` (자동회전 미포함 — teleop과 cmd_vel 충돌 방지). 운영자가 record 띄우고 "출발!" → 동료 주행.
- **동료 teleop**(별 터미널, **ROS source 필수**): `source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=210 && python3 /tmp/teleop_stamped.py /tb3_1/cmd_vel`. 키 w/x·a/d·s·q.
- 더 찍으려면 record를 또 띄움 → 여러 bag. **bringup(odom) 안 끊으면 같은 좌표계라 합쳐짐**.
- **4′. 합쳐 복원**: `d435_bag_to_ply.py <bag1> <bag2> ... --accumulate --frames 0 --frame-step 8 --stride 3` (다중 bag + `--frame-step`로 긴 주행 프레임 솎기 = 점 폭주 방지). 상세: `docs/ref/tech/3D-MAPPING-COWORK.md`.

## 함정 (2026-06-25 / 06-26 전부 실측)
| 증상 | 원인 | 해결 |
|---|---|---|
| 점군 토픽 안 뜸 | wrapper가 `pointcloud.enable` declare 안 함 | aligned depth + Mac deproject (경로 B) |
| 회전 안 함 | cmd_vel = **TwistStamped**, 매틱 stamp 필요 | `drive_rotate.py` (ros2 topic pub·Twist 둘 다 불가) |
| record 5GB 폭주 + **turtlebot3_node 죽음** | `ros2 bag record`가 안 닫힘(`pkill -INT` 미작동) | `timeout --signal=INT N ros2 bag record` |
| odom/base_footprint frame 없음 | bringup 미가동 | `_t1_bringup_only.sh` |
| /odom 토픽 있는데 frame 없음 | 도메인 잔재(젠지) or daemon 캐시 | `ros2 topic info /odom -v`의 Publisher count로 생존 판정 |
| ssh 끊김(`pkill -f realsense`) | 패턴이 ssh 명령줄에 노출 → self-kill | 스크립트 파일 내부 pkill / `[r]` bracket trick |
| LiDAR abnormal restart 루프 | single_coin_d4 하드웨어 | odom과 독립이면 무시(별개 이슈) |
| teleop 안 움직임(cmd_vel Publisher=0) | teleop 터미널서 ROS source 안 함 → `import rclpy` 실패 즉사 | `source /opt/ros/jazzy/setup.bash`+`export ROS_DOMAIN_ID=210` 후 실행 |
| record 좀비(timeout 무시·bag 미생성) | record 여러 개 겹쳐 시작 단계 hang | 단일 record만; `pgrep -f "[b]ag record"`로 1개 확인·정리 |
| 점 1억개 폭주(긴 주행) | `--accumulate --frames 0` 전 프레임 누적 | `--frame-step 8` 프레임 솎기(중복 제거, 디테일 영향 0) |
| 로봇 들어올림 → 점 뭉침 | 바퀴 안 돎 = odom "제자리" 착각 | 들지 말 것; 바퀴 땅에 붙인 채 주행 |

## 재사용 스크립트
- `scripts/_t1_rs_pointcloud.sh` — D435 aligned depth 깨끗 재기동
- `scripts/_t1_bringup_only.sh` — turtlebot3 bringup(odom/tf 복원)
- `scripts/d435_record_smoke.sh` — 회전 + record(timeout 자동종료)
- `scripts/drive_rotate.py` — TwistStamped 제자리 회전(매틱 stamp, 단독 캡처용)
- `scripts/teleop_stamped.py` — TwistStamped 키보드 teleop(동료 수동 주행, 협업용)
- `scripts/d435_record_only.sh` — 회전 없는 record(teleop 협업용, cmd_vel 충돌 방지)
- `scripts/d435_bag_to_ply.py` — bag(들)→컬러 PLY (`--accumulate` odom 누적, 다중 bag 입력 + `--frame-step` 솎기)
- `scripts/ply_render.py` — PLY→탑다운/정면/턴테이블 PNG(뷰어 없이 육안 검증, numpy+PIL)

## 한계 (정직)
- odom 누적 = **드리프트**(loop closure 없음). 정밀하려면 RTAB-Map(visual loop closure).
- 단일 위치 = **가림**(물체 뒤·먼 구석 빈 곳). 완전 3D는 다중 위치 캡처.
- D435 0.3~3m → 먼 벽 부분적. 발표는 회전 파노라마로 보완.
- 발표·관제용 3D 디지털트윈엔 충분, Nav2 정본 병합엔 부적합.

## 관련
- 앞단 카메라 살리기: [[robot-camera-bringup]], 비침습 pose: [[ros2-noninvasive-pose-tap]]
- 2D 맵 정본/슬롯: [[saved-map-to-unity-slot]], 리서치: `docs/ref/REALSENSE-D435-3D-MAPPING-RESEARCH.md`
- 협업 매핑 절차서: `docs/ref/tech/3D-MAPPING-COWORK.md` (역할분담·동료 명령카드·주행 팁)
- RTAB-Map 재처리(드리프트 근본해결): [[urhynix-rtabmap-docker-mac-blocked]] — Mac/Docker 불가, 동료 네이티브 우분투 경로(`scripts/rtabmap_*.sh`)
- 함정 짝: pkill self-kill, T1 nav2 lifecycle(메모리)
