---
name: rtabmap-bag-to-ply
description: 티원 D435 rosbag2(mcap)를 OrbStack Ubuntu VM의 RTAB-Map으로 재처리해 컬러 3D 점군 PLY를 만드는 표준 파이프라인. "rtabmap 돌려줘", "bag으로 3D 맵 만들어줘", "PLY 뽑아줘", "3D 맵 만들어" 같은 요청에 발동. 2026-06-30 검증 완료, 2026-07-01 대용량 bag(24GB급) + mcap 손상 복구 + tf 함정 추가 검증.
---

# rtabmap-bag-to-ply

## 목적

티원 D435 bag(rosbag2 mcap) → OrbStack VM rtabmap → 컬러 점군 PLY.
Docker-on-Mac은 message_filters sync 불가 — OrbStack Ubuntu VM(네이티브 Linux 커널)만 동작.

## 선행 확인

```bash
# OrbStack VM 접속 확인
ssh rtabmap@orb "echo OK"
# ROS2 + rtabmap 설치 확인
ssh rtabmap@orb "source /opt/ros/jazzy/setup.bash && ros2 pkg list | grep rtabmap_ros"
```

VM 미설치 시: `bash scripts/rtabmap_setup_ubuntu.sh` 를 VM에서 실행.

## Step 0 — 실제 이동 구간 확인 (대용량 bag이면 먼저)

bag 녹화 시간 = 실제 주행 시간이 아닐 수 있다 (녹화 켜놓고 정지 상태로 오래 둔 경우). 처리 전 odom으로 실제 이동 구간을 먼저 확인하면 뒤에서 `duration_sec` 인자로 그 구간만 잘라 처리해 시간을 아낄 수 있다.

```bash
# VM/티원 어디서든 rosbag2_py로 odom 위치 샘플링 (전체를 실시간 재생할 필요 없음)
ssh rtabmap@orb "source /opt/ros/jazzy/setup.bash && python3 -c \"
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
r = SequentialReader(); r.open(StorageOptions(uri='/home/family/bags/<bag_폴더>', storage_id='mcap'), ConverterOptions('',''))
count=0; first=None
while r.has_next():
    topic, data, t = r.read_next()
    if topic != '/tb3_1/odom': continue
    count+=1
    if first is None: first=t
    if count % 3000 == 1:
        m = deserialize_message(data, Odometry); p = m.pose.pose.position
        print(f'{(t-first)/1e9:7.1f}s x={p.x:.3f} y={p.y:.3f}')
\""
```

x,y가 어느 시점부터 소수점 3자리까지 완전히 고정되면 그 이후는 정지 구간 — 그 직전 시각을 `duration_sec`로 사용.

## bag 파일 위치

- 티원 `~/bags/<bag_폴더>/` — `*.mcap` + `metadata.yaml` 있어야 함
- metadata.yaml 없으면: `ssh t1 "ros2 bag reindex ~/bags/<bag_폴더>"`
- `ros2 bag info <mcap파일>` 으로 metadata.yaml 없어도 토픽 확인 가능

## 실행

### Step 1 — bag을 VM으로 복사

**방법 A (권장): VM에서 티원 직접 pull** — VM↔티원 ping 가능 (OrbStack Mac NAT 경유)

```bash
# VM에 sshpass 설치 (최초 1회)
ssh rtabmap@orb "sudo apt-get install -y sshpass"

# VM에서 티원 직접 pull (Mac 중계 없이 빠름)
ssh rtabmap@orb "mkdir -p ~/bags/<bag_폴더> && \
  nohup sshpass -p '123' scp -o StrictHostKeyChecking=no \
  t1@192.168.20.101:/home/t1/bags/<bag_폴더>/<bag_폴더>_0.mcap \
  ~/bags/<bag_폴더>/<bag_폴더>_0.mcap > ~/scp_direct.log 2>&1 &
  echo PID=\$!"

# metadata.yaml 별도 복사 (작아서 Mac 중계도 OK)
sshpass -p '123' scp -o StrictHostKeyChecking=no -3 \
  t1@192.168.20.101:/home/t1/bags/<bag_폴더>/metadata.yaml \
  rtabmap@orb:/home/family/bags/<bag_폴더>/
```

**방법 B: Mac 중계 scp** (VM pull 안 될 때)

```bash
scp -3 t1:/home/t1/bags/<bag_폴더>/<bag_폴더>_0.mcap \
  rtabmap@orb:/home/family/bags/<bag_폴더>/
```

방법 A가 방법 B보다 빠름 — OrbStack 내부 경로로 한 구간만 WiFi.

### Step 1.5 — 복사 진행 모니터링

```bash
until ssh rtabmap@orb "! pgrep -x scp > /dev/null"; do
  ssh rtabmap@orb "du -sh ~/bags/<bag_폴더>/<bag_폴더>_0.mcap"
  sleep 60
done && echo "복사 완료!"
```

### Step 1.7 — mcap 손상 의심 시 (재생이 즉시 `record type 0x00 ...` 에러로 죽으면)

```bash
# mcap CLI 설치 (arm64 예시, 없으면)
curl -sL -o mcap https://github.com/foxglove/mcap/releases/download/releases/mcap-cli/v0.2.0/mcap-linux-arm64 && chmod +x mcap

# 복구는 원본이 이미 있는 소스 장비(티원 등, 디스크 여유 넉넉한 곳)에서 — 원본+결과물 동시 보관 필요
scp mcap t1:/home/t1/mcap
ssh t1 "chmod +x ~/mcap && ~/mcap recover /home/t1/bags/<bag_폴더>/<bag_폴더>_0.mcap -o /home/t1/bags/<bag_폴더>/recovered.mcap"
# 로그에서 "Recovered N msgs ... stopped early" 확인 → mcap info로 실제 duration 확인
ssh t1 "~/mcap info /home/t1/bags/<bag_폴더>/recovered.mcap"
# 이후 recovered.mcap을 원래 <bag_폴더>_0.mcap 자리에 덮어써서 Step 2 진행 (metadata.yaml은 안 맞아도 ros2 bag play는 mcap 자체를 읽으므로 무방)
```

### Step 2 — rtabmap 재처리

```bash
scp scripts/rtabmap_replay_bag.sh rtabmap@orb:/home/family/
# cam_ns: /tb3_1/camera/camera (신규 bag) 또는 /tb3_1/camera (구 bag)
# duration_sec(선택): Step 0에서 확인한 실제 이동 구간(초)만 재생. 생략 시 끝까지.
ssh rtabmap@orb "nohup bash ~/rtabmap_replay_bag.sh \
  /home/family/bags/<bag_폴더> jazzy /tb3_1/camera/camera 230 \
  > /home/family/replay_main.log 2>&1 &"
```

스크립트가 자동으로 하는 것: ①compressed→raw republish ②rtabmap launch ③`tb3_1/base_link → camera_link` static tf(D435 마운트 추정 오프셋, 아래 함정 참고) ④`--qos-profile-overrides-path`로 `/tf_static` transient_local 강제 ⑤재생 종료 후 rtabmap 정상 종료 + PLY export.

### Step 3 — 진행 모니터링

```bash
# WM 증가 확인 (숫자 올라가면 정상)
ssh rtabmap@orb "grep 'rtabmap (' /home/family/bags/rtabmap_out/rtabmap.log | tail -3"
# 완료 대기
ssh rtabmap@orb "until ! pgrep -f 'ros2 bag play' > /dev/null; do sleep 10; done && echo '완료'"
```

### Step 4 — PLY Mac으로 복사

```bash
scp rtabmap@orb:/home/family/bags/rtabmap_out/rtabmap_cloud.ply \
  docs/evidence/3d_maps/<bag_폴더명>_cloud.ply
```

CloudCompare로 열기: `open docs/evidence/3d_maps/*.ply`

## 함정 (2026-06-30 검증)

| 함정 | 원인 | 해결 |
|---|---|---|
| `Did not receive data since 5s` (WM=1 고착) | bag에 color/raw 없고 compressed만 있음 | `image_transport republish` 노드 추가 (`-p in_transport:=compressed` 방식) |
| republish CLI 버그 | `republish compressed raw` 위치인자 파싱 순서 잘못됨 | `-p in_transport:=compressed -p out_transport:=raw` 명시 |
| approx_sync 매칭 실패 | color·depth 타임스탬프 ~1초 차이 | `approx_sync_max_interval:=2.0` 필수 |
| DB I/O error / SIGABRT | 손상된 rtabmap.db 잔류 | 실행 전 `rm -f .../rtabmap_out/rtabmap.db` |
| rtabmap_viz=true | VM headless라 GUI 불가 | `rtabmap_viz:=false` |
| 티원 디스크 100% — /tmp 쓰기 불가 | rootfs 꽉 참 | `/dev/shm` (RAM tmpfs, 1.8GB) 사용 |
| metadata.yaml 0바이트 (reindex 실패) | 티원 디스크 100%라 reindex 결과 못 씀 | `ros2 bag info <mcap파일>` 직접 실행 → 토픽 정보 확인 후 수동 metadata.yaml 작성 |
| scp -3 느림 | Mac이 암호화를 두 번 처리 | VM에서 티원으로 직접 pull (방법 A) |
| bag 카메라 네임스페이스 변경 | D435 launch 설정에 따라 다름 | `ros2 bag info`로 확인 후 `cam_ns` 인자 지정 |

## 함정 (2026-07-01 추가, 24GB급 대용량 bag)

| 함정 | 원인 | 해결 |
|---|---|---|
| 맥 디스크가 전송 도중 고갈 | OrbStack VM 디스크가 맥 물리디스크를 직접 소비 + 삭제해도 TRIM 안 돼서 안 줄어듦 | 큰 파일 지운 뒤 VM에서 `sudo fstrim -v /`로 맥에 반환. 습관화할 것 |
| VM 디스크가 22G에서 안 늘어남 | `disk_bytes: 0`(자동)인데 실제로는 재시작 시점에만 재계산 | `orbctl restart <vm>`으로 강제 재-확장 트리거 |
| `rsync --append`로 이어받았는데 재생 시 `record type 0x00 ... length 5959...` 에러 | append는 기존 바이트를 검증 안 함 — 예전 끊긴 전송의 손상이 prefix에 그대로 남음 | 재전송은 `rsync --checksum`(전체 내용 비교, quick-check 스킵 방지)으로. 그래도 에러나면 손상은 원본(t1) 자체 문제 — t1에서 직접 재생 테스트로 확인 |
| `mcap doctor`가 VM을 통째로 먹통(load 30+, SSH 응답 없음)으로 만듦 | 손상 레코드의 length 필드가 쓰레기값(수백 페타바이트)이라 그대로 믿고 거대 할당 시도 → OOM | `bash -c 'ulimit -v <제한>; mcap ...'`로 프로세스만 죽게 격리. `info`처럼 정상 mmap이 필요한 명령은 파일 크기보다 넉넉한 ulimit(예: 30000000=28GB), `doctor`처럼 손상 의심 시엔 4GB같이 타이트하게 |
| `mcap recover` 결과 파일이 tail이 쓰레기값(매직 없음), `info`에서 `Bad magic number` | recover 도중 디스크 꽉 차거나 ulimit에 걸려 죽음 → footer/magic 못 씀 | 원본+결과물 동시에 들어갈 공간(원본 크기의 2배) 확보. 가장 안전한 곳은 **원본이 이미 있는 소스 장비**(예: 티원, 여유 65GB) — VM/맥 디스크 압박을 아예 피함 |
| `recover` 로그: "Recovered N msgs ... stopped early (input truncated)" | 진짜 정상 — 로봇이 실제로 이동한 구간 이후는 원본이 거기서 끊겨있었을 뿐(재녹화 문제 아님) | `mcap info recovered.mcap`으로 실제 duration 확인. 문서상 예상 시간(예: "41분")과 맞으면 정상 |
| `rtabmap: Did not receive data`는 사라졌는데 `TF ... is not set!` / `extrapolation into the past` | `/tf_static`이 replay 중 volatile durability로 나가 늦게 붙는 rtabmap 구독자가 최초 1회성 방송을 놓침 | `ros2 bag play --qos-profile-overrides-path <yaml>`로 `/tf_static`에 `durability: transient_local` 강제 (스크립트에 이미 반영됨) |
| QoS override 이후에도 TF 에러 지속, `earliest data is at [현재 시각]`처럼 계속 흐르는 값 | `tb3_1/base_link → camera_link` 연결 자체가 원본 녹화에 없음(네임스페이스 안 된 카메라 트리와 tb3_1 트리가 분리된 채 녹화됨) — 손상/복구와 무관, 원본부터 이랬음 | `ros2 run tf2_ros static_transform_publisher --x 0.04 --z 0.10 --frame-id tb3_1/base_link --child-frame-id camera_link`를 재생과 같이 띄움(스크립트에 이미 반영됨). 오프셋 출처: `urhynix-d435-3d-pointcloud-capture` 스킬 |
| `ssh ... "pkill -9 -f <패턴>"` 실행 중 SSH 세션 자체가 끊김(exit 255) | 원격 명령 문자열 자체에 패턴이 리터럴로 포함돼 pkill이 그 셸까지 잡아 죽임 | `pkill -f '[p]attern'` 괄호트릭 사용 ([[pkill-f-self-kill-ssh]] 메모리 참고) |
| SSH가 배너 교환에서부터 타임아웃(VM 응답 없음) | VM이 I/O 과부하(디스크 풀스캔 등)로 sshd조차 응답 못 함 | ping은 되는지 먼저 확인, 될 때까지 재시도 루프(고정 sleep 금지, until-루프) |

## 함정 (2026-07-03 추가)

| 함정 | 원인 | 해결 |
|---|---|---|
| `ros2 bag record`를 `kill -2`(SIGINT)로 못 멈춤(수십 초 대기해도 프로세스 안 죽음, 파일 계속 자람) | 이 세션에서 실측 — 원인 불명(rclpy 시그널핸들러가 고load/백그라운드 상태에서 지연되는 것으로 추정) | `kill -15`(SIGTERM)로 escalate. metadata.yaml이 정상 생성되면(빈 파일 아니면) 깔끔히 종료된 것 — mcap 손상 걱정 안 해도 됨(이 세션에서 SIGTERM 종료 후 바로 재생 성공) |
| CloudCompare가 PLY 열자마자 `Error reading 'vertex_index' of 'face' number 3` | PCL이 내보낸 PLY의 비표준 `element camera 1`(뷰 메타데이터)을 CloudCompare 파서가 오해석 | camera/face element를 헤더에서 제거하고 vertex 블록만 남긴 "clean" PLY로 재저장해서 열기(nverts×31바이트만 잘라내면 됨, 함정 코드는 이 스킬의 정합검증 스크립트 참고) |
| 이 방(흰 벽 위주, 작고 대칭)에서 RTAB-Map loop closure가 계속 "Not enough inliers"로 실패, 전체 재구성이 시작점에서 멀어질수록 드리프트 | 시각 특징(코너/텍스처)이 부족해 프레임간 매칭이 약함 — 같은 방에서 라이다 AMCL도 좁고 대칭이라 헷갈리던 것과 동일 근본원인 | 이 방에서는 "시작점 근처는 정합 확인, 전체 커버리지는 제한적"이 기본 기대치. 개선하려면 경로를 여러 번 겹치게 돌거나(교차 재방문으로 loop closure 기회↑), 벽에 임시 마커/텍스처를 붙이는 것도 방법 |
| 2D맵/AMCL과 점군의 좌표계 정합 확인이 필요할 때 별도 툴 없이도 가능 | amcl_pose(map frame)와 odom을 같은 bag에 같이 녹화해두면, 같은 타임스탬프의 두 값으로 SE2 변환(회전+평행이동)을 직접 계산할 수 있음 | bag record 토픽에 `/tb3_1/amcl_pose` 포함 → `θ=amcl_yaw-odom_yaw`, `t=(amcl_xy)-R(θ)·(odom_xy)` 계산 → 점군 전체에 적용해 map frame으로 투영 → 2D맵 pgm과 오버레이 렌더로 육안 검증 |

## 토픽 네임스페이스 (티원 D435)

- color: `/tb3_1/camera/camera/color/image_raw/compressed`
- depth: `/tb3_1/camera/camera/aligned_depth_to_color/image_raw`
- camera_info: `/tb3_1/camera/camera/aligned_depth_to_color/camera_info`
- odom: `/tb3_1/odom`
- frame_id: `tb3_1/base_footprint`, odom_frame_id: `tb3_1/odom`

## 결과물

- `rtabmap_out/rtabmap.db` — RTAB-Map 맵 DB (loop closure 포함)
- `rtabmap_out/rtabmap_cloud.ply` — 컬러 점군 (CloudCompare/MeshLab로 열기)

검증 수치:
- 2026-06-30: 156초 bag → 103,621 포인트, 3.1MB PLY.
- 2026-07-01: 24.7GB/41분 bag(실제 이동 3분40초만 유효, 나머지는 정지) → mcap 손상 복구 후 230초만 재처리 → 380,192 포인트, 11.8MB PLY. 좌표 범위로 유효성 검증(x/y/z 스팬이 실제 공간 크기와 일치, RGB 0~255 전 범위 분포 확인 — 원본 없이도 실렌더 없이 빠르게 결과물 sanity check하는 표준 패턴).
- 2026-07-03: 4.3GB/269초 bag(amcl_pose 동시녹화) → 457,786 포인트 PLY → map frame 정합검증(시작점 근처 PASS, 전체는 loop closure 실패로 드리프트, 위 함정표 참고) → 실측 방 bbox로 크롭(186K)+SOR필터(170K 최종) → Unity `jp.keijiro.pcx`로 3D 탭 렌더링까지 연결(`unity-pcx-pointcloud-view` 스킬 참고).
