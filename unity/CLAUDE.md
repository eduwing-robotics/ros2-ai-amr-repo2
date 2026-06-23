# unity/

> URHYNIX Unity 프로젝트 묶음 폴더. 현재 `ControlRoom/` 1개 (관제 UI).

## 무엇이 들어가는가

- Unity Editor로 여는 정식 프로젝트 1개 이상.
- 각 하위 폴더는 독립된 Unity 프로젝트 (자체 `Assets/`, `Packages/`, `ProjectSettings/`).

## 기존 자산 위치 (참고)

- `../unity-smoke/` — 카메라 검증 PASS 자료실 (보존만, 신규 작업 금지).
- `../unity-src/` — PNG 시트만 채워졌던 빈 껍데기 (PNG는 ControlRoom으로 이관됨).

## 새 Unity 프로젝트 추가 시

1. `unity/<NewProject>/` 폴더 생성.
2. Unity Hub로 Add Project + 첫 Open.
3. 그 폴더에 `CLAUDE.md` 박기 (이 패턴 따라).
