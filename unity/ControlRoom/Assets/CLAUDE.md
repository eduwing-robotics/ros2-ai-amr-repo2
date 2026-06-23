# Assets/

> Unity가 import하는 모든 자산의 루트. 코드, UI, 아트, 씬, 프리팹, 런타임 리소스.

## 폴더 구조 (Phase 진입 순서 기준)

| 폴더 | 용도 |
|---|---|
| `Scenes/` | `.unity` 씬 파일 (`ControlRoomMain.unity` 등) |
| `UI/` | UI Toolkit UXML/USS/Token (UI 계층 정본) |
| `Scripts/` | C# 런타임 코드 (App/Data/UI/Map/Robot/Features/Sensors/Ros/Database/Simulation/Design 11개 하위) |
| `Editor/` | Unity Editor 전용 스크립트 (batch 자동화, 메뉴) |
| `Art/` | PNG 아이콘 등 비주얼 자산 |
| `Robots/` | URDF 원본 + import 결과 prefab |
| `Resources/` | `Resources.Load<>()`로 런타임 로드되는 자산 (SupabaseConfig 등) |

## 명명 규칙

- C# 파일: `PascalCase.cs` — Class 이름과 일치.
- UXML/USS: `PascalCase.uxml` / `PascalCase.uss` 또는 도메인 prefix (`ControlRoomMain.uxml`).
- PNG: `snake_case_<size>.png` (예: `protected_frame_128.png`).
- Scene/Prefab: `PascalCase.unity` / `PascalCase.prefab`.

## 주의

- 모든 자산은 `.meta` 파일이 자동 생성됨. `.meta`는 git에 커밋 (Unity가 GUID로 참조 추적).
- 빈 폴더는 Unity에서 안 보임. 폴더 유지 위해 CLAUDE.md 또는 `.gitkeep` 박기.
