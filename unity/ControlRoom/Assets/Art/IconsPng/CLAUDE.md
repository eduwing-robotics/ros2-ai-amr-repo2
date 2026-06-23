# Assets/Art/IconsPng/

> PNG 아이콘 세트. 6개 카테고리 × 4단계 사이즈.

## 카테고리

| 폴더 | 용도 | 현재 자산 |
|---|---|---|
| `Common/` | 공통 UI (경보/카메라/배터리/전원/맵 전환) | `fire_alert_*.png` (64/128/256/512) |
| `Robot/` | 로봇 배지 | `turtlebot_badge_*.png` (64/128/256/512) |
| `Sensor/` | 센서 (가스/소리/조도/PIR/화재) | `sensor_badge_*.png` (64/128/256/512) |
| `Target/` | 보호대상 (액자/작품/물품) | `protected_frame/art/object_*.png` (64/128/256/512) |
| `Generated/` | imagegen 시트 통본 | `control_room_icon_sheet.png` |
| `GeneratedRaw/` | imagegen 원본 raw | `control_room_icon_sheet_raw.png` |

## 사이즈 정책

- 원본: `512x512`
- UI 변형: `256`, `128`, `64`

## 명명 규칙

- `<role>_<size>.png` — 예: `protected_frame_128.png`, `fire_alert_512.png`
- snake_case 사용. PascalCase 금지.

## 생성/리사이즈 방법

- 신규: Codex 전역 스킬 `imagegen` 호출 → 원본 `512x512` 생성 → 자동 리사이즈.
- 리사이즈만: `sips -Z <size> input.png --out output.png` (macOS 기본 도구).
