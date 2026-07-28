# Assets/Art/

> 비주얼 자산 (PNG 아이콘 등). SVG 미사용 — 전부 PNG.

## 폴더

- `IconsPng/` — UI 아이콘 PNG (Common/Robot/Sensor/Target + Generated/GeneratedRaw)

## 규칙

- PNG only. SVG 가져오지 않음 (Unity 표준 import 안전성 + 렌더 비용).
- 원본 `512x512` + UI 사이즈 `256/128/64` 4단계 리사이즈.
- 파일명: `snake_case_<size>.png`.
- import 설정: `Texture Type = Sprite (2D and UI)`.
