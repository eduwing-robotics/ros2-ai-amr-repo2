# Assets/Scenes/

> Unity `.unity` 씬 파일들이 들어가는 폴더.

## 예정 씬

- `ControlRoomMain.unity` — 관제 메인 씬 (Phase 2에서 생성).
- 추가 씬은 데모/테스트 용도로 후속 phase에 추가 가능.

## 명명 규칙

- `PascalCase.unity`
- 씬에 들어가는 GameObject 이름도 PascalCase + 역할 prefix (예: `TopBar`, `MapPanel3D`).

## 주의

- 씬 파일은 YAML 텍스트라 git diff 가능. 큰 변경은 commit 단위로 쪼개기.
- batch mode로 씬 편집 시 `Assets/Editor/` 안의 스크립트로만 수행 (런타임 코드에서 씬 편집 금지).
