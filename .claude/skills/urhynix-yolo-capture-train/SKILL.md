---
name: urhynix-yolo-capture-train
description: URHYNIX에서 T1 RealSense 브라우저 UI로 맞춤 물체를 촬영하고, ROI 연사 자동 라벨링, 마스크 기반 bbox 보정, YOLO 학습, best.pt 라이브 탐지 검증까지 한 세션에 이어갈 때 사용한다. Space 촬영, 8090 low-latency preview, datasets/custom_object, runs/custom_object, rembg/SAM/GrabCut 라벨 보정이 언급되면 로드한다.
---

# URHYNIX YOLO Capture Train

## 언제 쓰나

- `http://127.0.0.1:8766/` 맞춤 YOLO 학습실을 점검하거나 수정할 때
- T1 RealSense D435 영상으로 원하는 물건을 캡처/라벨/학습/탐지할 때
- `영역 자동 연사`, `ROI`, `rembg`, `SAM`, `GrabCut`, `best.pt`가 포함된 작업
- 모델이 사람/손/배경을 잘못 배운 경우 라벨 품질을 회복해야 할 때

## 입력과 정본

- 앱: `scripts/yolo_training/custom_yolo_studio.py`
- T1 저지연 서버: `scripts/yolo_training/t1_compressed_mjpeg_server.py`
- 데이터셋: `datasets/custom_object`
- 학습 결과: `runs/custom_object/**/weights/best.pt`
- 증거 문서: `docs/evidence/2026-06-10-mac-yolo-realsense-live.md`
- 공용 하네스: `/Users/family/jason/jason-agent-harness-template/harnesses/robot-yolo-capture-train.md`

## 성공 패턴

1. T1 8090 서버의 `/status`가 fresh인지 확인한다.
2. 브라우저 실시간 화면은 긴 MJPEG `<img>` 대신 `/preview.jpg` 단발 polling을 쓴다.
3. `Space` 촬영은 저장 후 실시간 화면을 유지한다.
4. 단일 물체는 `영역 자동 연사`로 50~150장을 모은다.
5. 연사 전 `실시간 세그 보기`를 켜고 ROI 안에서 물건을 움직이며 mask/bbox가 물체만 잡는지 본다. 원본 live는 계속 돌리고 세그는 투명 overlay로만 얹어야 한다.
6. ROI 라벨은 그대로 저장하지 말고 가능하면 `ROI crop -> mask -> bbox -> YOLO txt` 순서로 좁힌다.
7. 마스크 엔진 우선순위는 SAM2 또는 `rembg`가 있으면 사용, 없으면 OpenCV GrabCut, 실패 시 ROI fallback이다.
8. 자동연사에서는 기본적으로 `매핑 성공한 사진만 저장`을 켠다. fallback/ROI 컷은 손과 배경 오염 위험이 크므로 즉시 삭제한다.
9. 라벨 없는 사진은 학습 전 삭제하거나 라벨을 채운다.
10. 학습 후 `best.pt`를 바로 로드하고 `/api/detect_frame.jpg` 또는 UI 탐지 보기로 실제 물건을 잡는지 확인한다. 서버 재시작 후에는 `runs/custom_object/*/weights/best.pt` 최신 파일을 자동 로드해야 한다.

## 라벨 품질 규칙

- ROI 안에는 물건만 들어가게 한다. 손, 팔, 몸통, 큰 배경 패턴이 ROI 안에 오래 머물면 모델이 그 대상을 배운다.
- 손으로 돌리는 경우 촬영 간격을 `700~1000ms`로 늘리거나 손을 뺀 뒤 촬영되게 한다.
- 자동 bbox 보정 결과가 너무 작거나 너무 넓으면 fallback 카운터가 오른다. fallback이 많으면 ROI를 다시 잡거나 조명을 바꾼다.
- `실시간 세그 보기`에서 fallback 문구가 자주 보이면 저장 연사를 시작하지 않는다.
- `실시간 세그 보기`가 끊기면 `/api/segment_frame.jpg`를 live 화면으로 쓰고 있는지 확인한다. 성공 패턴은 `/preview.jpg` raw live + `/api/segment_overlay.png` 투명 overlay 분리다.
- 반복 라벨 중 같은 좌표가 과도하게 많으면 고정 ROI가 학습된 것이다. 이때는 해당 사진을 삭제/재라벨하고, 다음 연사는 fallback 컷 삭제 정책으로 다시 모은다.
- 배경 제거 이미지만 학습하지 않는다. 원본 사진을 유지하고 bbox를 더 정확히 만드는 용도로 쓴다.
- 기존 데이터가 잘못 배웠다면 촬영 목록에서 `전체 선택`, `라벨 없음 선택`, 또는 체크박스 선택 후 `선택 삭제`로 jpg/txt를 같이 지운다.
- `탐지 보기`가 끊기면 SAM/rembg를 의심하지 말고 `/api/detect_frame.jpg` 응답 시간, preview frame 경로, browser polling delay, 중복 탭을 먼저 본다.

## 검증

```bash
cd /Users/family/jason/URHYNIX
test/.venv/bin/python -m py_compile scripts/yolo_training/custom_yolo_studio.py
curl -m 1 http://192.168.10.250:8090/status
curl -m 2 http://127.0.0.1:8766/api/status
```

브라우저 검증:
- ROI를 작게 하나 지정한다.
- `실시간 세그 보기`를 켜고 화면에 mask overlay나 fallback 경고가 표시되는지 본다.
- `촬영 장수=1`로 연사를 실행한다.
- 완료 문구에 `bbox 보정 N · fallback M`이 표시되는지 본다.
- 촬영 목록에서 새 jpg를 열고, `수정`에서 박스가 물체에 맞는지 확인한다.
- 삭제 기능 변경 시 `/api/delete_items` 빈 payload smoke로 데이터 손실 없이 API를 확인한다.

## 실패 시

- 8090 status가 stale이면 T1 `t1_compressed_mjpeg_server.py`를 재시작한다.
- rembg/SAM이 없으면 정상이다. 현재 기본 fallback은 GrabCut이다.
- GrabCut도 실패하면 ROI 박스가 저장된다. 이때는 학습 전에 수동 수정하거나 삭제한다.
- 탐지가 사람/배경을 잡으면 모델 문제가 아니라 라벨 문제가 우선이다. 잘못 라벨링된 burst 사진을 고치고 재학습한다.
- SAM2는 `from ultralytics import SAM; SAM("sam2_t.pt")`로 로드한다. `YOLO("sam2_t.pt")`는 잘못된 호출이며 checkpoint 로딩 오류가 날 수 있다.
- SAM2는 저장 라벨 bbox 정밀화에 우선 사용한다. 실시간 preview는 첫 호출이 5초 이상 걸릴 수 있어 기본값은 fast GrabCut 경로를 유지한다.
