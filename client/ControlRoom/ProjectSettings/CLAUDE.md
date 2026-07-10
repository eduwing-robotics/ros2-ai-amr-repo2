# ProjectSettings/

> Unity Editor가 자동 관리하는 프로젝트 설정. **사람이 직접 편집 금지** (예외: `ProjectVersion.txt`).

## 사람이 만지는 파일

| 파일 | 언제 |
|---|---|
| `ProjectVersion.txt` | Unity 버전 변경 시 (현재 `6000.3.16f1`) |

## Unity가 관리하는 파일 (직접 편집 금지)

`ProjectSettings.asset`, `InputManager.asset`, `TimeManager.asset`, `QualitySettings.asset`, `GraphicsSettings.asset`, `URPProjectSettings.asset`, ... 등.

## 변경 흐름

- 설정 변경은 항상 Unity Editor에서 (`Edit → Project Settings`).
- 변경 후 git diff로 의도된 변경인지 확인.
- merge conflict 발생 시 Unity Editor를 닫고 한쪽 채택 후 다시 열기.
