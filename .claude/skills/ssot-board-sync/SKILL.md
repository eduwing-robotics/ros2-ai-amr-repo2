---
name: ssot-board-sync
description: SSOT(docs/ref/*, docs/status/*) 변경을 dev-plan HTML 보드(7페이지 + 단일 번들)에 한 번에 동기화하는 스킬. 결정·하드웨어·역할·Sprint·시나리오·위험·제외 변경 시 사용.
user_invocable: true
tags: [documentation, ssot, html-board, sync, post-edit]
trigger: "SSOT 한 줄 바뀌면 dev-plan*.html과 번들도 같이 고쳐야 할 때"
version: 1
---

# SSOT ↔ Board Sync

## 목적

URHYNIX 프로젝트는 SSOT(`docs/ref/*`, `docs/status/*`)와 팀 공유용 HTML 보드(`docs/dev-plan*.html` 7페이지 + `docs/dev-plan-bundle.html` 단일 번들)를 동시에 운영한다. 한쪽만 고치면 즉시 드리프트가 발생하므로, **한 번의 변경 단위가 양쪽을 모두 갱신**하는 패턴을 강제한다.

## Use When

- SSOT 본문(PRD/ARCHITECTURE/CONTRACT/SCHEMA/PROJECT-PLAN/PROJECT-STATUS/JIRA-MAP/STACK-PROFILES) 1줄 이상 바꿨을 때
- 하드웨어 구성(센서·보드·적층) 결정이 들어왔을 때
- 역할 매트릭스(M1~M5 ↔ 4명)가 바뀌었을 때
- Sprint 구성 또는 병렬 작업 매트릭스가 바뀌었을 때
- 시나리오/위험/제외 범위가 추가·수정·삭제됐을 때
- DECISION-LOG에 새 항목이 추가됐을 때

## Skip When

- 단순 오타·문법 수정만 한 경우
- 코드 디렉토리(`ros2_ws/`, `unity-src/`, `arduino/`)만 변경한 경우 (그건 `doc-sync` 영역)

## 매핑 표 (SSOT 변경 → HTML 어디 손볼지)

| SSOT 변경 위치 | dev-plan HTML 갱신 대상 | 번들 갱신 |
|---|---|---|
| `PRD.md` MVP/성공기준/리스크/하드웨어 | `dev-plan.html` mvp 블록, `dev-plan-risks.html` 5장 카드 | 메인 + risks 섹션 |
| `PROJECT-PLAN.md` 병렬 매트릭스/Sprint | `dev-plan-sprints.html` 매트릭스 + Sprint 카드 | sprints 섹션 |
| `PROJECT-STATUS.md` 역할표/마일스톤 | `dev-plan-roles.html` 4인 카드 | roles 섹션 |
| `ARCHITECTURE.md` 모듈 경계/적층 | `dev-plan-modules.html` M1~M5 카드 + 하드웨어 적층 카드 | modules 섹션 |
| `CONTRACT.md` 토픽/메시지/시리얼 포맷 | `dev-plan-modules.html` M2/M4 핵심 산출물, `dev-plan-scenarios.html` 흐름 코드 | modules + scenarios |
| `SCHEMA.md` 테이블 정의 | (요약 표가 보드엔 없음, 필요 시 modules 카드에 추가) | — |
| `JIRA-MAP.md` 티켓 제목/담당자 | `dev-plan-sprints.html` 티켓 카드 18개 | sprints 섹션 |
| `STACK-PROFILES.md` URHYNIX 프로필 | (보드엔 직접 노출 없음, file map만) | — |
| `DECISION-LOG.md` 새 결정 | 영향받는 카드 모두 (위 표 참조) | 모두 |
| `whiteboards/role_matrix.png`, `role_graph.png` | `dev-plan-roles.html` 하단 PNG 토글 | 자동 base64 인라인 (재빌드만) |

## 실행 순서

1. **SSOT 먼저 갱신** — 정본이 항상 SSOT다.
2. **DECISION-LOG에 한 줄 결정 기록 (큰 변경 시)** — 무엇을, 왜, 영향이 무엇인지.
3. **매핑 표 따라 dev-plan-*.html 갱신** — 위 표 참조. 7페이지 중 영향받는 것만.
4. **번들 빌더 동기화** — 같은 변경을 `docs/whiteboards/build_bundle.py`의 HTML 템플릿에도 반영.
5. **번들 재빌드**:
   ```bash
   python3 docs/whiteboards/build_bundle.py
   ```
6. **검증** (아래 Verify 섹션)
7. **PROJECT-STATUS.md Evidence Status 갱신** — 검증 결과 ✅/⚠️/❌ 기재

## Verify

```bash
# 1) 모든 HTML 파싱 OK
python3 -c "
from html.parser import HTMLParser
import glob
for f in sorted(glob.glob('docs/dev-plan*.html')):
    HTMLParser().feed(open(f).read())
    print('OK', f)
"

# 2) 옛 방향/제거된 표현이 잔재하는지 (활성 문서만, DECISION-LOG는 예외)
grep -rn "LiDAR only vs\|장애물 비교\|미확정.*센서 연결" docs/ref docs/dev-plan*.html 2>/dev/null

# 3) tb3_1/tb3_2 일관 사용 확인 (핵심 6개 파일 이상)
grep -rln "tb3_1\|tb3_2" docs/ref docs/status docs/dev-plan*.html

# 4) 역할 매트릭스 일치 (M4 담당자 3명 등)
grep -A2 "data-module=\"M4\"\|M4 = \|M4) |" docs/ref/PROJECT-PLAN.md docs/status/PROJECT-STATUS.md docs/dev-plan-modules.html 2>/dev/null

# 5) 번들 크기 (~450KB 기준)
ls -lh docs/dev-plan-bundle.html
```

## 주의사항

- **번들은 자동 생성물이다.** `docs/dev-plan-bundle.html`을 직접 손으로 편집하지 말 것. 항상 `build_bundle.py`를 통해서만 갱신.
- **PNG 두 장**(`role_matrix.png`, `role_graph.png`)은 base64로 번들에 인라인된다. 그림이 바뀌면 `generate_role_board.py` 다시 실행 → `build_bundle.py` 재실행.
- **하드코딩된 텍스트 중복**에 주의: build_bundle.py의 HTML 템플릿과 개별 `dev-plan-*.html`은 의도적으로 중복돼 있다. 한쪽만 고치면 즉시 드리프트 — 항상 양쪽 같이 고친다.
- 큰 변경 후에는 `evidence-review` 스킬을 같이 돌려 Evidence Status를 갱신한다.

## 산출물

- 동기화된 SSOT 8종 + dev-plan 7페이지 + 단일 번들
- `DECISION-LOG.md`에 결정 1줄
- `PROJECT-STATUS.md` Evidence Status 행 ✅
- 위 Verify 명령 출력 (선택, evidence-review에 첨부)

## 참고

- 빌더 스크립트: `docs/whiteboards/build_bundle.py`
- 역할 PNG 생성기: `docs/whiteboards/generate_role_board.py`
- 정합 체인: Confluence 1540099 (브레인스토밍) → 1605636 (역할 분배 보드) → 본 SSOT/HTML

## 한줄정리

SSOT 한 줄 바꾸면 dev-plan 7페이지 + 번들도 같은 변경을 받아야 한다 — 매핑 표 따라 양쪽 고치고 `build_bundle.py` 한 번 실행하면 끝.
