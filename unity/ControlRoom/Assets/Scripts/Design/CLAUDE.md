# Assets/Scripts/Design/

> 디자인 토큰의 C# 상수. UI USS 토큰과 1:1.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `UiTokens.cs` | 색상/간격/상태 이름 상수 (USS `ControlRoomTokens.uss`와 동기화) |
| `IconNames.cs` | PNG 아이콘 파일명 상수 (`Art/IconsPng/` 자산명) |

## 규칙

- USS 토큰 변경 시 이 폴더도 같이 갱신 (2곳 SSOT). 자동 동기화 도구가 없으니 수동.
- 아이콘 파일명은 `snake_case_<size>.png`, 상수명은 `PascalCase`.
- 잘못된 상수 = 런타임 NRE라서 컴파일 시 잡히게 `const string`으로.
