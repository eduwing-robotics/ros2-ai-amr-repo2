---
name: t1-rgbd-mapping-session
description: 티원 D435 RGB-D 매핑 세션 전체 절차 — bringup + D435 기동 + bag 녹화 + WASD teleop 준비. "티원 매핑 시작", "맵핑 세션", "bag 녹화하자", "D435 켜고 매핑" 같은 요청에 발동. 2026-06-30 검증 완료.
---

# t1-rgbd-mapping-session

## 목적

티원 D435로 공간을 주행 매핑하고 bag(rosbag2 mcap)을 저장하는 표준 절차.
bag 저장 후 `rtabmap-bag-to-ply` 스킬로 3D 점군 PLY 생성.

## 선행 확인

```bash
ssh t1 "echo OK"  # WiFi SSH 확인 (192.168.20.101)
ssh t1 "ls /dev/ttyACM0 && ls /dev/video0"  # OpenCR + D435 연결 확인
```

## Step 1 — bringup (백그라운드)

```bash
ssh t1 "export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp && nohup bash ~/_robot_bringup_ns.sh tb3_1 /dev/ttyACM0 2 > /tmp/bringup_t1.log 2>&1 &"
```

30초 후 확인:
```bash
ssh t1 "source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && timeout 4 ros2 topic list | grep tb3_1/odom"
```

## Step 2 — D435 기동 (백그라운드)

```bash
ssh t1 "kill \$(pgrep -u t1 realsense) 2>/dev/null; sleep 2; source /opt/ros/jazzy/setup.bash; export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp; nohup ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true align_depth.enable:=true camera_namespace:=/tb3_1/camera > /tmp/d435.log 2>&1 &"
```

10초 후 확인 (`RealSense Node Is Up!` 뜨면 OK):
```bash
ssh t1 "tail -3 /tmp/d435.log"
```

## Step 3 — bag 녹화 (새 터미널)

```bash
ssh t1 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && ros2 bag record \
  /tb3_1/camera/camera/aligned_depth_to_color/image_raw \
  /tb3_1/camera/camera/aligned_depth_to_color/camera_info \
  /tb3_1/camera/camera/color/image_raw/compressed \
  /tf /tf_static /tb3_1/odom \
  -o ~/bags/mapping_$(date +%Y%m%d_%H%M)'
```

`All requested topics are subscribed.` 뜨면 녹화 중.

## Step 4 — WASD teleop (새 터미널, -t 필수)

```bash
ssh -t t1 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=2 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && python3 /tmp/wasd_teleop.py'
```

wasd_teleop.py 없으면 먼저 배포:
```bash
# Mac에서 실행
cat > /tmp/wasd_teleop.py << 'PYEOF'
#!/usr/bin/env python3
import sys, tty, termios, rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

LIN, ANG = 0.06, 0.5

KEYS = {
    'w': ( LIN, 0.0), 's': (-LIN, 0.0),
    'a': (0.0,  ANG), 'd': (0.0, -ANG),
    ' ': (0.0,  0.0),
}

def getkey():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def main():
    rclpy.init()
    node = Node('wasd_teleop')
    pub = node.create_publisher(TwistStamped, '/tb3_1/cmd_vel', 10)
    print("WASD teleop | w=전진 s=후진 a=좌 d=우 space=정지 q=종료")
    while True:
        k = getkey()
        if k == 'q': break
        lin, ang = KEYS.get(k, (None, None))
        if lin is None: continue
        msg = TwistStamped()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.twist.linear.x = lin
        msg.twist.angular.z = ang
        pub.publish(msg)
        print(f"  lin={lin} ang={ang}   ", end='\r')
    node.destroy_node(); rclpy.shutdown()

main()
PYEOF
scp /tmp/wasd_teleop.py t1:/tmp/wasd_teleop.py
```

키 배치: `w`=전진 `s`=후진 `a`=좌 `d`=우 `space`=정지 `q`=종료

## 매핑 팁

- 속도 0.06 m/s — 빠르면 depth blur → 맵 틀어짐
- **반드시 시작점으로 돌아올 것** — loop closure 없으면 drift
- 골목: 들어갔다 **후진으로 나오기** (D435 전방 카메라라 기존 구조 재인식 → 정합 유리)
- 한 구역 완료 → 돌아오기 → 다음 구역 순서

## 녹화 완료 후

1. bag 창에서 `Ctrl+C`
2. 저장 확인: `ssh t1 "du -sh ~/bags/mapping_*"`
3. Mac으로 복사: `scp -r t1:~/bags/mapping_<ts> docs/evidence/3d_maps/`
4. PLY 생성: `rtabmap-bag-to-ply` 스킬 실행

## 함정 (2026-06-30 검증)

| 함정 | 해결 |
|---|---|
| teleop 키 입력 에코만 되고 움직임 없음 | `ssh -t` 없으면 raw tty 안 됨 — `-t` 필수 |
| cmd_vel 전달 안 됨 | 티원은 TwistStamped 사용 — WASD 스크립트가 이미 TwistStamped 발행 |
| D435 "Device or resource busy" | 기존 PID 직접 kill (`pgrep -u t1 realsense` → `kill <PID>`) 후 재시작 |
| D435 color 토픽 없음 | `enable_color:=true` 확인, `tail -3 /tmp/d435.log`에서 `RGB Camera` 확인 |
| bag 15MB만 복사됨 | `scp &` 백그라운드는 불안정 — 포그라운드로 실행 |
| `ros2 bag record`를 `Ctrl+C`/`kill -2`로 못 멈춤(수십 초 대기해도 파일 계속 자람) | 2026-07-03 실측, 원인 불명(고load 상태에서 rclpy 시그널핸들러 지연 추정) | `kill -15`(SIGTERM)로 escalate. metadata.yaml이 정상 생성되면 깔끔 종료된 것 |

## 토픽 네임스페이스 (2026-06-30 확인)

D435 네임스페이스: `/tb3_1/camera/camera/` (camera가 두 번 붙는 구조 정상)
- color: `/tb3_1/camera/camera/color/image_raw/compressed`
- depth: `/tb3_1/camera/camera/aligned_depth_to_color/image_raw`
- camera_info: `/tb3_1/camera/camera/aligned_depth_to_color/camera_info`
