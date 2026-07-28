#!/usr/bin/env bash
# 두 모델 웹캠 비교 (같은 조건에서 번갈아 테스트)
#
# 1) AI-Hub YOLOv5:  ./scripts/webcam_aihub_yolov5_test.sh
# 2) 프로젝트 YOLOv8: ./scripts/launch_laptop_webcam_test.sh
#
set -eo pipefail

cat <<'EOF'
=== 모델 비교 테스트 순서 ===

1) AI-Hub YOLOv5 (Downloads/ai)
   ./scripts/webcam_aihub_yolov5_test.sh
   CONF=0.35 ./scripts/webcam_aihub_yolov5_test.sh   # 민감도 조절

2) 현재 robot_project YOLOv8
   ./scripts/launch_laptop_webcam_test.sh
   YOLO_CONF=0.18 SMOKE_CONF=0.32 ./scripts/launch_laptop_webcam_test.sh

비교 포인트:
  - 불/연기 동시 검출 여부
  - 모니터·벽·회색 옷 오탐
  - 실제 화재 영상(휴대폰) 인식

로봇 적용 시:
  - YOLOv8이 더 나으면 → museum_fire_smoke.pt 계속 + 데이터 보강
  - AI-Hub가 더 나으면 → YOLOv8로 distillation/재학습 또는 ONNX 변환 검토
  - person/exhibit 추가 → 3~4클래스로 파인튜닝 (기존 fire/smoke 유지)
EOF
