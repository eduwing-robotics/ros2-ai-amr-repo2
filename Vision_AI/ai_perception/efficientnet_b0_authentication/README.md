# EfficientNet-B0 Painting Authentication

Bacchus 그림을 `GENUINE`, `FAKE`, `RECHECK`로 분류하는 진위 판별 기능입니다.

## 시연 영상

- [EfficientNet-B0 바쿠스와 아리아드네 진위 판정 영상](media/Efficientnet_B0_바쿠스와_아리아드네_진위판정.mp4)

## 구성

- `models/`: EfficientNet-B0 체크포인트와 평가 메타데이터
- `config/`: 작품 ROI 설정
- `scripts/`: 데이터 촬영·준비·학습·오프라인 및 실시간 추론

## 주요 실행

```bash
cd ~/ros2-ai-amr-repo2/Vision_AI

python3 ai_perception/efficientnet_b0_authentication/scripts/infer_auth_offline.py --image /path/to/image.jpg
python3 ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py
```
