# Assets/UI/

> UI Toolkit UXML(레이아웃) + USS(스타일) + Token(디자인 토큰) 정본.
> C# 바인더는 `Scripts/UI/`에 둠 — 계층은 마크업, 동작은 코드.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `ControlRoomMain.uxml` | 관제 화면 전체 레이아웃 |
| `ControlRoomStyle.uss` | 전체 스타일 |
| `ControlRoomTokens.uss` | 색상/간격/폰트/상태 토큰 (SSOT) |
| `Parts/*.uxml` | 부분 UXML (TopBar, LeftControlPanel, MapPanel, CameraAndLogPanel, RightStatusPanel) |

## 명명 규칙

- UXML/USS: `PascalCase.uxml` / `PascalCase.uss`.
- `Parts/` 안의 부분 UXML은 합쳤을 때 `ControlRoomMain.uxml`이 됨.

## 토큰 사용 규칙

- 색/간격/폰트는 직접 박지 말고 `ControlRoomTokens.uss`의 변수(`--token-name`)로 참조.
- C#에서도 `Scripts/Design/UiTokens.cs`로 동일 토큰을 상수화.
