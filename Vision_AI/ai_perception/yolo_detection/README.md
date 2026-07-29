# YOLO Museum Detection

박물관 순찰 중 화재·연기·사람·조각상을 감지하는 YOLO 기능입니다.

## 시연 영상

- [T1 YOLO 실시간 감지 영상](media/T1_YOLO.mp4)

## 구성

- `models/`: 파인튜닝 및 화재·연기 가중치
- `training/`: 데이터 준비와 YOLO 학습 코드
- `../../museum_patrol_system/`: ROS 2 감지 노드와 Task Manager
- `../../scripts/robot_yolo_viewer.py`: 실시간 ROS 카메라 추론

## 주요 실행

```bash
cd ~/ros2-ai-amr-repo2/Vision_AI

# T1
./scripts/run_finetune_live.sh

# Gen.G
./scripts/run_geng_yolo_live.sh
```
