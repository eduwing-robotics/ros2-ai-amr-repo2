# scripts/aruco_parking — ArUco 자동주차 노드

티원 TurtleBot3 + RealSense D435용 ArUco 마커 자동주차 ROS2 노드.

## 파일

- `parking_node.py` — 메인 노드 (TwistStamped 발행). 마커 ID 1번 + DICT_4X4_50, depth 거리(m) 직접 사용.

## 사용

t1(라즈베리파이)에 `~/aruco_ws/src/aruco_parking/aruco_parking/` 경로로 배포 후 `colcon build` → `ros2 run aruco_parking parking_node`.

## 안전 한도

- 최대 선속도: 0.15 m/s
- 최대 각속도: 0.5 rad/s
- `dry_run:=true` 파라미터로 실제 cmd_vel 0 발행 (시뮬레이션 검증용)

## 의존

- ROS 2 Jazzy
- opencv-contrib-python (aruco 모듈)
- cv_bridge (ros-jazzy-cv-bridge)
