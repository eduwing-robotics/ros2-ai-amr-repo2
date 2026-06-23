---
name: doc-health-audit
description: 프로젝트 문서 건강성을 진단하고 선택적으로 고치는 스킬. "문서건강성체크", "문서 건강성 체크해줘", "문서 건강성 점검", "doc health", "문서 정리 상태 봐줘", "진입 문서 토큰 너무 큰지 확인" 같은 요청에 발동. 3대 기준(① 인덱싱성: 프로젝트/태스크 첫 시작 시 필요 정보를 바로 찾아 들어갈 수 있는가, 죽은 링크 여부 ② 파일크기/토큰: 매 세션 로딩되는 진입 문서가 비대해 토큰을 낭비하는가 ③ 폴더/정리: 폴더 경계·중복·스테일·방치 파일 상태)으로 등급 판정 후 즉시개선/깔끔개선 편집을 소넷 에이전트로 실행한다.
user_invocable: true
tags: [documentation, health, audit, indexing, token-budget, ssot, drift]
trigger: "문서 건강성 체크 / 진입 문서가 비대해진 것 같을 때 / docs 폴더 정리 상태 점검 / 주 1회 문서 위생 점검"
version: 1
---

<!-- doc-health-audit/SKILL.md · 생성 2026-06-17 · URHYNIX 문서 건강성 1회차 성공 패턴 자산화. frontmatter는 반드시 파일 첫 줄(헤더주석 룰의 예외). -->

# Doc Health Audit

프로젝트 문서가 "첫 진입에 빠르게 인덱싱되고, 토큰을 낭비하지 않고, 폴더별로 잘 정리됐는가"를 진단하고, 승인 시 편집까지 닫는다.

## Use When

- 주인님이 "문서 건강성 체크해줘" 류로 요청할 때 (1차 트리거)
- 진입 문서(HANDOFF/STATUS/DECISION/TECH-INDEX)가 커진 것 같아 매 세션 토큰이 아까울 때
- 새 폴더/문서가 늘어 정리 상태가 의심될 때
- 주 1회 문서 위생 점검

## 3대 기준 (판정축)

| 기준 | 본다 | 적신호 |
|---|---|---|
| **① 인덱싱성** | 진입 경로(CLAUDE→HANDOFF→STATUS→DECISION→TECH-INDEX)가 실제로 라우팅되나, 죽은 링크 없나 | "가장 아래 항목" 같이 실제와 어긋난 안내, 깨진 상호참조 |
| **② 파일크기/토큰** | 매 세션 로딩되는 진입 문서 라인수 합 | "1페이지"라더니 500줄 캡슐, 1000줄+ 결정로그를 매번 읽으라는 지침 |
| **③ 폴더/정리** | docs/ 하위 폴더 경계, 스테일/중복/방치/빈 파일, 폴더 README 유무 | 1달+ 방치 daily, 영구 미체크 checklist, README 없는 폴더(룰7 위반) |

## Steps

1. **스캔(직접, 싸게)** — Bash로 문서 지도를 만든다. `ls`는 rtk 필터로 빈 출력이 날 수 있으니 `find`를 쓴다.
   ```bash
   find docs -name "*.md" -type f -exec wc -l {} + | sort -rn | head -50   # 큰 파일
   find docs -type d | sort                                                  # 폴더 경계
   wc -l CLAUDE.md AGENTS.md AGENT.md docs/status/HANDOFF.md docs/status/DECISION-CURRENT.md docs/ref/TECH-INDEX.md
   ```
2. **분석(소넷 에이전트)** — `general-purpose` + `model="sonnet"`로 진입 문서를 실제로 읽고 3대 기준 등급(A~F) + 적신호를 판정시킨다. 큰 결정로그는 처음 50줄/마지막 80줄만. 죽은 링크는 grep으로 점검. **추측 금지, 파일경로:라인 인용 강제.**
3. **보고 + 승인** — 종합 등급표 + 🔴즉시/🟡권장/🟢양호 + 편집 제안을 주인님께 제시. `AskUserQuestion`으로 편집 범위 선택(빠른개선 / 깔끔개선 / 보류).
4. **편집(소넷 에이전트)** — 승인 범위만큼 `general-purpose` + `model="sonnet"`로 실행. 아래 불변식을 프롬프트에 박는다.
5. **검증(직접)** — 편집 결과를 `find`/`wc`/`grep`으로 직접 확인. 에이전트가 "준비함"이라 모호하게 보고한 이동/생성은 반드시 직접 재검증.

## 편집 불변식 (소넷 프롬프트에 필수 주입)

- **내용 삭제 금지 = 이관(move)만.** 큰 문서를 줄일 때 잘라낸 내용은 다른 파일로 옮긴다. 정보 손실 0. (메모리: 원본 보존)
- 파일/폴더 이동은 `git mv` (히스토리 보존).
- 새 파일은 최상단 1~5줄 헤더 주석(목적/생성일). 새 폴더는 README.md 또는 CLAUDE.md. (룰7)
- 편집 전 Read 필수, 추측 금지.
- `git commit`은 하지 않는다 — 주인님이 직접.

## 표준 처방 (1회차 검증된 패턴)

- **HANDOFF 비대화** → 원본을 `HANDOFF-FULL.md`로 `git mv` 보존 후, 새 HANDOFF는 ~80줄 캡슐(Top 액션 + 5분 체크리스트 + If stuck + More Info 링크).
- **DECISION-LOG 비대화** → 최신 5건을 `DECISION-CURRENT.md`로 원문 복사 분리, 본체 상단에 네비 헤더. CLAUDE.md 로딩순서도 함께 정정.
- **스테일 daily/임시** → `docs/archive/`로 `git mv`, 폴더에 README + 분기 아카이브 정책.
- **README 없는 폴더** → 용도 1~5줄 README 추가.

## Outputs

- 종합 등급표(3기준 A~F + 한줄 근거)
- 🔴 즉시 고칠 것 / 🟡 개선 권장 / 🟢 양호 + 파일별 편집 제안
- (승인 시) 변경/신규/이동 파일 목록 + 진입 문서 최종 라인수 + 죽은 링크 0건 확인

## Verify

```bash
find docs -name "*.md" -exec wc -l {} + | sort -rn | head -10   # 진입 문서 축소 확인
git status --short | grep -E "docs/|CLAUDE"                       # 이동/신규 실제 반영(R/A/M)
# 진입 문서 상호참조 죽은 링크 0건 grep
```
- HANDOFF가 목표 라인 이하인가, 옮긴 파일이 git에 `R`(rename)로 잡혔나, 죽은 링크 0건인가.

## Failure / Fallback

- `ls`가 빈 출력 → rtk 필터. `find`로 재확인.
- 소넷이 "폴더 생성 준비"처럼 모호하게 보고 → 실제 `git mv` 누락일 수 있음. `find`로 직접 확인 후 메인이 마무리.
- 분석만 필요하면 4번(편집) 생략, 보고서만 산출.

## References

- 1회차 성공 사례: 이 스킬 도입 세션(2026-06-17) — HANDOFF 506→77줄, DECISION-CURRENT 분리, 매 세션 ~1000토큰 절약.
- 자매 스킬: `doc-sync`(코드 변경 후 문서 누락), `ssot-trio-update`(작업 후 3종 SSOT 갱신), `session-handoff`(진입 캡슐 생성).
