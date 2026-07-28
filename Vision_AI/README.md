# 박물관 로봇 AI 통합 기능 안내

`Vision_AI/`는 박물관 순찰 로봇용 두 기능을 한곳에 정리한 폴더입니다.

1. **YOLO 박물관 감지**: 화재·연기·조각상 등을 감지하고, 사람 감지 모델과 함께 실시간 화면에 표시합니다.
2. **Bacchus 진위 판별(EfficientNet-B0)**: 카메라로 본 Bacchus 그림을 `GENUINE(진품)`, `FAKE(위작)`, `RECHECK(재확인)`으로 분류합니다.

## 먼저 알아둘 점

- 이 저장소에는 학습용 원본 데이터셋 전체가 들어 있지 않습니다. 학습하려면 별도로 데이터셋을 준비해야 합니다.
- `models/`의 `.pt` 파일은 이미 학습된 모델 가중치입니다.
- ROS 2 카메라 토픽이 실행 중이어야 실시간 기능을 사용할 수 있습니다.
- 실행 전 카메라와 ROS 2 환경을 먼저 준비하세요.

## 설치

```bash
cd ~/ros2-ai-amr-repo2/Vision_AI
python3 -m venv .venv
source .venv/bin/activate
pip install opencv-python numpy pillow pyyaml torch torchvision ultralytics
```

ROS 2 Jazzy 환경에서는 ROS 2가 설치된 터미널에서 실행하고, 필요한 Python ROS 패키지가 설치되어 있어야 합니다.

## 기능 1: 박물관 YOLO 실시간 감지

### T1 카메라(`tb3_1`)

먼저 로봇에서 RealSense 카메라를 실행한 뒤, 노트북에서 다음을 실행합니다.

```bash
cd ~/ros2-ai-amr-repo2/Vision_AI
./scripts/run_finetune_live.sh
```

카메라 토픽이 다른 경우 직접 지정합니다.

```bash
./scripts/run_finetune_live.sh \
  --camera-topic /tb3_1/camera/color/image_raw/compressed
```

### Gen.G 카메라(`tb3_2`)

```bash
./scripts/run_geng_yolo_live.sh
```

토픽을 직접 지정할 수도 있습니다.

```bash
./scripts/run_geng_yolo_live.sh \
  --camera-topic /tb3_2/camera/image_raw/compressed
```

YOLO 실시간 실행에 사용되는 주요 파일은 다음과 같습니다.

| 파일 | 역할 |
|---|---|
| `scripts/robot_yolo_viewer.py` | ROS 카메라 영상을 받아 YOLO 추론 및 화면 표시 |
| `scripts/run_finetune_live.sh` | T1용 실행 래퍼와 토픽 기본값 설정 |
| `scripts/run_geng_yolo_live.sh` | Gen.G용 ROS 도메인·토픽 설정 및 실행 |
| `ai_perception/yolo_detection/models/museum_finetune.pt` | 박물관 감지용 파인튜닝 YOLO 모델 |
| `ai_perception/yolo_detection/models/museum_fire_smoke.pt` | 화재·연기 모델 |
| `ai_perception/yolo_detection/training/train_museum_yolo.py` | YOLO 학습 스크립트 |

화면을 종료하려면 YOLO 창을 선택하고 `q`를 누릅니다.

## 기능 2: Bacchus 그림 진위 판별

### 저장된 이미지 한 장 검사

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py --image /path/to/painting.jpg
```

결과는 진품 확률, 위작 확률, 최종 판정으로 출력됩니다.

여러 장을 한 번에 검사하려면:

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py \
  --split-dir datasets/museum_auth_dataset/dataset/test
```

판정 결과를 JSON으로 저장하려면:

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py \
  --image /path/to/painting.jpg \
  --json-out results/auth_result.json
```

### 카메라 실시간 검사

T1 카메라를 먼저 실행한 뒤 다음을 실행합니다.

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py
```

기본 판정은 두 확률의 차이가 작으면 `RECHECK`를 표시합니다. 기준을 조정하려면:

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py \
  --genuine-threshold 0.55 \
  --fake-threshold 0.55
```

관련 파일은 다음과 같습니다.

| 파일 | 역할 |
|---|---|
| `ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py` | ROS 카메라 영상의 그림 영역을 실시간 판별 |
| `ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py` | 이미지 파일 오프라인 판별 |
| `ai_perception/efficientnet_b0_authentication/scripts/train_auth_efficientnet.py` | EfficientNet-B0 학습 |
| `ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.py` | 진품·위작 데이터셋 분할 |
| `ai_perception/efficientnet_b0_authentication/config/painting_auth_bacchus.yaml` | Bacchus 그림 ROI 설정 |
| `ai_perception/efficientnet_b0_authentication/models/bacchus_auth_effnet_b0.pt` | 학습된 EfficientNet-B0 가중치 |

## 모델 재학습

진품·위작 이미지가 다음 구조로 준비되어 있어야 합니다.

```text
datasets/museum_auth_dataset/dataset/
├── train/genuine/
├── train/fake/
├── val/genuine/
├── val/fake/
├── test/genuine/
└── test/fake/
```

데이터셋을 준비한 뒤 학습합니다.

```bash
python3 ai_perception/efficientnet_b0_authentication/scripts/train_auth_efficientnet.py \
  --epochs 8 \
  --batch-size 8
```

YOLO를 재학습하려면:

```bash
python3 ai_perception/yolo_detection/training/train_museum_yolo.py \
  --data datasets/museum_fire/processed/data.yaml \
  --epochs 50
```

## 문제 해결

- `no camera frames`: 카메라 노드가 실행 중인지, 토픽 이름이 맞는지 확인하세요.
- `Publisher count: 0`: `--camera-topic`으로 실제 토픽을 지정하세요.
- 화면이 검게 보임: ROS_DOMAIN_ID와 DDS 설정이 로봇·노트북에서 일치하는지 확인하세요.
- 모델 파일 없음: `models/` 아래의 `.pt` 경로와 실행 명령의 경로가 맞는지 확인하세요.

현재 `Vision_AI/` 폴더에는 위 두 기능이 함께 들어 있습니다.
