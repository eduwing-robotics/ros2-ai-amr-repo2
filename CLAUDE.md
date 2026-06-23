# URHYNIX

프로젝트 루트의 짧은 진입점이다. 다중 TurtleBot 디지털트윈경비로봇.

## 🚀 빠른 시작 (이거만 읽으면 출발 가능)

1. **`docs/status/HANDOFF.md`** — 다음 세션 진입 캡슐 (Top 액션 + 첫 5분 체크리스트).
2. **`docs/status/PROJECT-STATUS.md`** — 한 줄 상태 + 역할 매트릭스 + Day-1 작업.
3. **`docs/status/DECISION-CURRENT.md`** — 최신 결정 5건 (센서 교체·도메인 통일·무선 통일).
4. **`docs/ref/TECH-INDEX.md`** — Unity/ROS2/Arduino/DB/카메라/하네스 작업별 빠른 ref 라우팅.

→ 위 4개로 5분 안에 출발 가능. 나머지는 필요할 때 들어가면 됨.

## 📚 전체 로딩 순서 (필요 시)

1. `CLAUDE.md` (이 파일)
2. `AGENTS.md`, `AGENT.md`
3. `docs/status/HANDOFF.md` ← 빠른 시작 캡슐 (Top 액션 + 5분 체크리스트)
4. `docs/status/PROJECT-STATUS.md`
5. `docs/status/DECISION-CURRENT.md` ← 최신 결정 5건
6. `docs/status/DECISION-LOG.md` ← 전체 역사
7. `docs/ref/TECH-INDEX.md`
7. `docs/ref/PROJECT-PLAN.md`
8. `docs/ref/ARCHITECTURE.md`
9. `docs/ref/CONTRACT.md`, `docs/ref/SCHEMA.md`
10. `docs/ref/STACK-PROFILES.md`, `docs/ref/JIRA-MAP.md`
11. `.claude/skills/README.md`
12. 필요 시 `docs/ref/tech/*.md`, `docs/ref/PRD.md`

## 🔧 즉시 활용 가능 자산

- 시각 보드: `docs/dev-plan-bundle.html` (단일 HTML 465KB, 더블클릭으로 7페이지 다 열림)
- 빌더: `python3 docs/whiteboards/build_bundle.py` (SSOT 갱신 후 재빌드)
- PNG 생성기: `python3 docs/whiteboards/generate_role_board.py` (역할 변경 시)
- 자주 쓰는 스킬: `ssot-board-sync` (SSOT↔HTML), `decision-broadcast` (5채널 동기화)

## Hard Rules

1. 읽기 전 편집 금지
2. 중요한 액션 전 목적 명시
3. 추측보다 구현과 실행 결과 우선
4. 검증 없는 완료 선언 금지
5. 문서 드리프트 방치 금지
6. 파일이 300줄 근처면 분리를 검토
7. 새 폴더가 경계를 가지면 로컬 `AGENTS.md` 또는 `CLAUDE.md` 추가
8. 새 요청은 `/intake` 또는 `task-intake-router` 우선
9. 완료 전 `evidence-review` 또는 `Evidence Status` 갱신
