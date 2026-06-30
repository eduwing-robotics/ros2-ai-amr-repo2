<!-- 3D-MAPPING-COWORK.md — 티원 D435 3D 점군 매핑을 2인(운영자+텔레옵 동료)이 협업하는 절차서.
     단독 자동회전 표준은 .claude/skills/urhynix-d435-3d-pointcloud-capture/SKILL.md. 이 문서는 그 teleop 협업 변형. -->

# 3D 매핑 협업 가이드 (운영자 + 텔레옵 동료)

> **무엇**: 티원(TurtleBot3 + RealSense D435)으로 공간을 컬러 3D 점군(PLY)으로 뜬다.
> **왜 협업/teleop**: 단독 자동회전(제자리 360°)은 한 자리만 봐서 물체 뒤·구석이 **가림(occlusion)**. 동료가 teleop으로 **천천히 한 바퀴 돌면** 여러 시점이 쌓여 가림이 줄고 3D가 꽉 찬다.
> **로봇**: 3D는 **티원(tb3_1)** 전용(D435 장착). 젠지는 끔.

---

## 역할 분담

| 역할 | 누가 | 무엇 |
|---|---|---|
| **운영자** | 나(Mac) | 티원 bringup·D435 기동·static tf·**record 시작/종료**·Mac에서 PLY 복원·시각 검증 |
| **텔레옵** | 동료 | 티원에 ssh 진입 → **`teleop_stamped.py`로 수동 주행** (record 도는 동안 공간 한 바퀴) |

> 둘 다 같은 도메인(`ROS_DOMAIN_ID=210`). cmd_vel은 **TwistStamped** — 표준 `teleop_keyboard`(Twist)는 **안 먹는다**. 반드시 `teleop_stamped.py`를 쓴다.

---

## 타임라인 (한눈에)

```
운영자: ①bringup → ②D435 → ③static tf → (준비완료 신호) ─────→ ④record 시작 ──[120s]──→ record 자동종료 → ⑤scp+복원+검증
동료:                                         ssh 진입 → teleop 대기 ──→ "출발!" 듣고 천천히 한 바퀴 ───→ 정지
```

핵심: **record가 도는 120초 동안** 동료가 주행한다. 운영자가 "출발" 외치면 시작, record 자동 종료되면 "정지".

---

## 운영자 절차 (Mac)

스크립트는 모두 `scripts/`에 있음. 티원으로 scp 후 실행하는 패턴(`_t1_*`은 SKILL과 동일).

```bash
MAC_IP=192.168.10.48          # Mac IP (DHCP면 ifconfig로 확인)
T1=t1@192.168.10.250          # 티원 (IP drift 시 ssh alias/ mDNS)

# 스크립트 티원으로 올리기 (한 번)
scp scripts/_t1_bringup_only.sh scripts/_t1_rs_pointcloud.sh \
    scripts/d435_record_only.sh scripts/drive_rotate.py \
    scripts/teleop_stamped.py  $T1:/tmp/

# ① bringup — odom + tf 복원 (turtlebot3_node, OpenCR 통신 필수)
ssh $T1 "bash /tmp/_t1_bringup_only.sh $MAC_IP"
#   확인: /tb3_1/odom ~20Hz, tb3_1/base_footprint tf 존재

# ② D435 깨끗 재기동 (aligned depth, 640x480x15)
ssh $T1 "bash /tmp/_t1_rs_pointcloud.sh"
#   확인: /tb3_1/camera/aligned_depth_to_color/image_raw ~14Hz, USB3(5000M)

# ③ base_link → camera_link static tf (마운트 추정값; 정밀시 실측 보정)
ssh $T1 "source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=210 && \
  setsid nohup ros2 run tf2_ros static_transform_publisher --x 0.04 --z 0.10 \
  --frame-id tb3_1/base_link --child-frame-id camera_link >/tmp/cam_tf.log 2>&1 &"
#   검증: ros2 run tf2_ros tf2_echo tb3_1/odom camera_color_optical_frame → Translation 나오면 tf 사슬 완성

# ── 여기서 동료에게 "준비됐으면 teleop 켜" 신호 ──

# ④ record 시작 (120초, 회전 명령 없음 = 동료 teleop 전담)
#    실행 직후 동료에게 "출발!" → 동료가 천천히 한 바퀴
ssh $T1 "bash /tmp/d435_record_only.sh 120"
#   → BAG=/tmp/d435_rot_<ts> 출력됨. record 자동 종료되면 동료에게 "정지!"

# ⑤ Mac으로 복사 + 컬러 PLY 복원
SESS=cowork_$(date +%m%d)
scp -r $T1:/tmp/d435_rot_<ts> docs/evidence/3d_maps/$SESS/
uv venv /tmp/plyenv && uv pip install --python /tmp/plyenv/bin/python rosbags numpy pillow
/tmp/plyenv/bin/python scripts/d435_bag_to_ply.py docs/evidence/3d_maps/$SESS/d435_rot_<ts> \
  -o docs/evidence/3d_maps/$SESS/out.ply --accumulate --frames 0 --stride 3 --zmax 3.5

# ⑥ 시각 검증 (성역): 탑다운 렌더에서 주행 경로 따라 360° 벽 분포 = 성공
```

---

## 동료(텔레옵) 절차 — 이 부분만 동료에게 전달

```bash
# 1. 티원에 진입
ssh t1@192.168.10.250          # 비밀번호 123

# 2. teleop 켜기 (운영자가 "준비됐으면 켜" 하면)
#    ★ ROS source + 도메인 export 먼저 — 안 하면 import rclpy 실패로 즉시 죽음(빈 ssh 터미널이라).
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
python3 /tmp/teleop_stamped.py /tb3_1/cmd_vel
```

**조작키**

| 키 | 동작 | 키 | 동작 |
|---|---|---|---|
| `w` / `x` | 전진 / 후진 | `a` / `d` | 좌 / 우 회전 |
| `s` 또는 `space` | 즉시 정지 | `q` 또는 `Ctrl-C` | 종료 |

**주행 요령 (3D 품질 = 주행 품질)**

- **천천히.** 상한이 0.15 m/s로 묶여 있다. 빠르면 odom이 어긋나(드리프트) 점군이 뭉개진다.
- **벽까지 0.3~3m 유지.** D435 측정 범위. 너무 붙거나 멀면 빈 구멍.
- **급회전 금지.** 회전은 살살. 제자리 급회전은 odom 오차 제일 큼.
- **한 바퀴 돌며 구석을 채운다.** 물체 뒤·모서리를 다른 각도에서 한 번씩 비춰주면 가림이 메워진다.
- 운영자가 **"출발!"** 하면 시작, **"정지!"** 하면 `s`로 멈춘다(record 끝남).

---

## 함정 / 주의 (실측)

| 증상 | 원인 | 해결 |
|---|---|---|
| 로봇이 안 움직임 (cmd_vel Publisher count=0) | teleop 터미널에서 ROS source 안 함 → `import rclpy` 실패로 즉사 | `source /opt/ros/jazzy/setup.bash` + `export ROS_DOMAIN_ID=210` 후 실행 |
| 로봇이 안 움직임 | `teleop_keyboard`(Twist) 썼다 | **`teleop_stamped.py`**(TwistStamped) 써야 함 |
| 움직이는데 너무 느림/멈칫 | 1회 누름=0.02m/s(매핑용 저속 상한) | `w`를 3~5번 눌러 가속(상한 0.15m/s) |
| 명령이 떨림/멈칫 | cmd_vel publisher 2개(teleop + 자동회전) 충돌 | 협업엔 `d435_record_only.sh`(회전 없음) 사용 — `d435_record_smoke.sh` 아님 |
| record 5GB 폭주·노드 죽음 | `ros2 bag record`가 안 닫힘 | `timeout --signal=INT`(스크립트에 내장) |
| odom frame 없음 | bringup 미가동 | `_t1_bringup_only.sh` 먼저 |
| ssh 끊김 | `pkill -f`에 패턴 노출 = self-kill | 스크립트 내부 pkill만, 수동 pkill 금지 |
| 점군 드리프트/뭉갬 | odom 누적엔 loop closure 없음 | 천천히·짧게. 정밀 필요 시 RTAB-Map(visual loop closure) |

---

## 한계 (정직)

- **odom 누적 = 드리프트.** loop closure 없어 크게 돌수록 어긋난다 → 발표/디지털트윈엔 충분, Nav2 정본 병합엔 부적합.
- D435 0.3~3m → 먼 벽 부분적. 다중 위치 주행으로 보완(이 협업의 목적).
- 2D 정본 맵(`arena_v*`)은 LDS-03 SLAM 별도 — 이 3D는 그 위에 얹는 발표/관제용 레이어.

## 관련
- 단독 자동회전 표준: `.claude/skills/urhynix-d435-3d-pointcloud-capture/SKILL.md`
- 스크립트: `scripts/teleop_stamped.py`, `scripts/d435_record_only.sh`, `scripts/_t1_bringup_only.sh`, `scripts/_t1_rs_pointcloud.sh`, `scripts/d435_bag_to_ply.py`
