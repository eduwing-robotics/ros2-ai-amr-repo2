# Camera Integration Checklist

**Use Case**: 카메라(RealSense D435 + Pi Camera v2) 스트림 결선 및 ROS2 토픽 검증  
**Owner**: 임현찬(RealSense), 김주영(Pi Camera)

---

## Tier 1: 하드웨어 점검

- [ ] RealSense D435 USB 연결 확인 (T1 라즈베리파이 USB 포트)
- [ ] Pi Camera v2 리본 케이블 연결 (젠지 라즈베리파이 Camera CSI 포트)
- [ ] 두 카메라 LED 불이 켜있는가?

## Tier 2: 드라이버 및 라이브러리

- [ ] T1: `ros-jazzy-realsense2-camera` 설치 확인 (`dpkg -l | grep realsense`)
- [ ] 젠지: `libcamera-dev` + `rpicam-apps` 설치 확인
- [ ] T1: RealSense firmware 버전 확인 (`rs-enumerate-devices`)
- [ ] 젠지: Pi Camera 권한 설정 (`usermod -aG video pi`)

## Tier 3: ROS2 노드 런칭

- [ ] T1: `ros2 launch realsense2_camera rs_launch.py` 실행
- [ ] 젠지: `ros2 launch camera_ros camera.launch.py` (또는 `rpicam` 스크립트)
- [ ] 두 노드 모두 no error 확인 (`tail -f /var/log/... | grep ERROR` 0건)

## Tier 4: 토픽 발행 확인

- [ ] T1: `/tb3_1/camera/color/image_raw/compressed` 토픽 발행 (30Hz 이상)
- [ ] 젠지: `/tb3_2/camera/image_raw/compressed` 토픽 발행 (30Hz 이상)
- [ ] Cross-host multicast 수신 (ROS_DOMAIN_ID=210 확인)
  ```bash
  ros2 topic list | grep camera
  ros2 topic hz /tb3_1/camera/color/image_raw/compressed  # 30Hz 이상?
  ```

## Tier 5: Unity 통합

- [ ] TopicRegistry에 두 카메라 토픽 등록
- [ ] CameraSubscriber 스크립트 활성화
- [ ] Unity ControlRoom 에디터에서 카메라 패널 표시 (tb3_1 탭, tb3_2 탭 전환 가능)
- [ ] 라이브 영상 렌더링 확인 (5fps 이상)

## Tier 6: 네트워크 안정성

- [ ] Foxglove 클라이언트 drop/error 0건 (log tail)
- [ ] Wi-Fi 신호 강도 확인 (RSSI > -70 dBm)
- [ ] 간헐 끊김 시 compressed 포맷 재확인 (`image_raw` vs `.../compressed`)

---

**Last updated**: 2026-06-17
