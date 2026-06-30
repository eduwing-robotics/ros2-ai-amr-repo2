# docs/presentation/weekly_ppt/

> 주간 진행상황 발표 PPT (HTML 단일 파일 + 이미지 assets). 2026-06-28 첫 작성.

## 구성

- `weekly_report.html` — 단일 HTML PPT. 16:9 슬라이드, 키보드 네비게이션(`→/←/Space/F/Home/end`).
  chatterbox-business-plan.html 디자인(녹탁 #004737 + 민트 #56F09F) 참고, 19 슬라이드.
- `assets/img/` — PPT 본문이 실제 참조하는 PNG 7장 (Confluence drawio exports + ui-layout + 점군).
- `assets/conf_27459586/` — Confluence 06-26 회의록 원본 첨부 17건 백업 (PPT 본문은 미참조, 보존용).

## 데이터 출처 (추적성)

- **라이브 연동**: Atlassian Cloud REST API — Jira `search/jql` + Confluence `content/27459586/child/attachment`.
  자격: `$ATLASSIAN_EMAIL` + `$ATLASSIAN_TOKEN` (환경변수로만, git 미반입).
- **로컬 SSOT**: `docs/status/DECISION-LOG.md` · `HANDOFF.md` · `PROJECT-STATUS.md` (12건 결정 인용).
- **Unity 소스 라인**: `SupabaseDbService.cs` · `DispatchPublisher.cs` · `QuickActionView.cs` · `MapContextMenuView.cs` · `ControlRoomEvents.cs` (버튼→API→DB 흐름).
- **git log**: `git log --since='7 days ago'` 6커밋.

## 재작성 시 주의

- 이미지는 `assets/img/` 상대 경로 — 폴더째 배포해야 함. 단일 파일 분배 시 base64 inline 변환 필요.
- 19 슬라이드는 `SLIDES` 배열 요소 1개 = 1 슬라이드. JSON 문자열 아님(템플릿 리터럴). `<` 등은 HTML entity 아님 — `<code>` 태그 안에서 안전.
- Confluence 첨부 갱신하려면 06-26 회의록 page id가 바뀔 수 있으니 `assets/conf_27459586/att.json`의 id로 `/download` 경로를 다시 계산.

## OpenCode 사용 공시

- 작성 모델: OpenCode (glm-5.2). 2026-06-28.
- 이미지 시각 검증은 본 모델이 이미지 입력을 지원하지 않아 생략. HTML/JS 파서 + 이미지 파일 존재 + JS 구문 검증(`node --check`)만 PASS.
- **high-cost/strong-model 1회 검토 권장** (코드 트레이스 라인·Confluence 매핑·Jira 상태 정합).