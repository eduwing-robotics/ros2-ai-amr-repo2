# Demo Validation Checklist

**Use Case**: 박물관/미술관 실제 현장 시연 전 최종 검증  
**Owner**: 김주영(전체 조율)

---

## Tier 1: 환경 점검 (현장 도착 후)

- [ ] 전원 공급: 전용 멀티탭 2개 연결 확인 (UPS 필요 시)
- [ ] Wi-Fi 신호 강도 측정 (RSSI > -70 dBm)
- [ ] 경기장 바닥 평탄도 확인 (요철 < 5mm)
- [ ] 가벽/경계선 설치 및 안전 검사

## Tier 2: 하드웨어 상태 확인

- [ ] T1(티원) 배터리 전압 11.5V 이상 (`ssh t1@... 'cat /sys/class/power_supply/*/uevent'`)
- [ ] 젠지 배터리 전압 11.5V 이상
- [ ] 두 로봇 LiDAR/카메라/센서 정상 작동 (시각적 LED 확인)
- [ ] OpenCR USB 연결 및 재설정 버튼 누름

## Tier 3: ROS2 통신 확인

- [ ] `ssh` 연결 성공 (mDNS 또는 IP, 권장: mDNS)
- [ ] 두 로봇 ROS_DOMAIN_ID=210 동일 확인
- [ ] `ros2 topic list` → 10개 이상 토픽 보임
- [ ] bringup 노드 정상 실행 (`ros2 node list | grep burger`)

## Tier 4: 카메라 및 센서 스트림

- [ ] T1 RealSense 영상 stream 30Hz+ (`ros2 topic hz /tb3_1/camera/...`)
- [ ] 젠지 Pi Camera 영상 stream 30Hz+ (`ros2 topic hz /tb3_2/camera/...`)
- [ ] 센서 데이터 발행: PIR/온도/레이저 (`ros2 topic echo /sensors/...`)

## Tier 5: Unity ControlRoom 시연

- [ ] 에디터 실행 후 Play 모드 진입 (메모리 < 2GB 필요)
- [ ] 듀얼 로봇 탭 전환 (tb3_1 ↔ tb3_2) 가능
- [ ] 라이브 카메라 영상 렌더링 (blackness 아님)
- [ ] 배터리 % 표시 업데이트
- [ ] 센서 카드 (PIR/온도 등) 데이터 표시

## Tier 6: YOLO 비전 (옵션)

- [ ] Mac MPS YOLO 추론 준비 (`test/detect_realsense.py --headless`)
- [ ] 탐지 객체 4종(사람/로봇/중요품/불) 테스트
- [ ] 영상 끊김 없음 (compressed 토픽 사용)

## Tier 7: 시나리오 5종 리허설

- [ ] Scenario 1: 침입자 감지 (PIR 손 흔들기)
- [ ] Scenario 2: 전시품 변화 감지 (카메라 재촬영)
- [ ] Scenario 3: 화재 의심 (YOLO 불 감지 또는 온도 시뮬)
- [ ] Scenario 4: 전시품 접촉 (손 감지, YOLO)
- [ ] Scenario 5: 배터리 부족 (배터리 % 모니터링)

## Tier 8: 긴급 대응

- [ ] 롤백: `git status` 0 uncommitted changes (원본 복구 보장)
- [ ] 네트워크 끊김: 직결(Mac ↔ 젠지 eth0) 또는 다른 SSID 준비
- [ ] 카메라 프리징: 노드 재시작 명령어 준비 (`ros2 pkg find ...`)
- [ ] 배터리 부족: 충전 완료 확인 + 예비 배터리 준비

## Tier 9: 최종 체크 (시연 30분 전)

- [ ] `git diff` 원본 일치 확인
- [ ] 두 로봇 위치 경기장 시작점 배치
- [ ] 카메라 렌즈 청소 (습기/먼지)
- [ ] 음성 안내/알림 스피커 음량 테스트

---

**Last updated**: 2026-06-17
