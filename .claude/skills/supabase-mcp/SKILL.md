---
name: toss-supabase-mcp
description: TaillogToss Supabase MCP 운영 스킬 — 마이그레이션, Edge 배포, 로그/키 점검, 안전한 실행 순서 표준화.
---

> **ℹ️ URHYNIX 이식 노트 (2026-05-26)**
> 이 스킬은 `/Users/family/jason/TaillogToss/.claude/skills/toss-guide/` 에서 복사됐어요.
> Toss/TaillogToss 특화 용어(userKey, IAP, AIT 등)는 URHYNIX 컨텍스트(HW 자격증명, ROS, Unity)로 직접 치환·다듬어서 사용하세요.
> 원본 보존: `/Users/family/jason/TaillogToss/.claude/skills/toss-guide/...` (절대 수정 금지)


# Toss Supabase MCP Ops

Supabase MCP 작업을 안전한 순서로 수행하고, 변경 영향과 증적을 남기는 운영 스킬.

## 언제 사용하나
- 마이그레이션 적용/점검
- Edge Function 배포/호출 검증
- 프로젝트 키/URL/함수 상태 점검
- DB 브랜치 생성/병합 작업

## 기본 원칙
- DDL은 `apply_migration` 사용 (임의 SQL로 DDL 실행 지양)
- 프로덕션 영향 작업 전 상태 스냅샷 확보
- 배포 후에는 반드시 `호출 검증 + 로그 확인` 수행

## 표준 절차
1. Preflight
- `get_project_url`
- `get_publishable_keys`
- `list_edge_functions` 또는 `list_migrations`

2. 변경 수행
- DB: `apply_migration`
- Edge: `deploy_edge_function` (`verify_jwt` 정책 명시)

3. 사후 검증
- 함수: HTTP 스모크 호출(메서드/인증 정책 확인)
- 로그: `get_logs(service=\"edge-function\")`
- DB: 필요한 경우 테이블/정책 확인 SQL

4. 문서 동기화
- 변경 버전, 시간(KST), 증적(request id/status) 기록

## 자주 쓰는 점검 항목
- `verify_jwt`가 함수 용도와 일치하는가
- 공유 모듈 import 누락으로 bundling 실패하지 않는가
- 공개 함수(`verify_jwt=false`)는 최소 범위로 제한되었는가
- Edge 로그의 최신 버전이 기대 버전과 일치하는가

## 실패 대응
- 배포 실패: 누락 파일 추가 후 재배포
- 호출 실패: 인증 헤더/메서드/payload 스키마 확인
- 문서 불일치: `CLAUDE.md`를 단일 기준으로 재정렬

## Failure Modes
<!-- enrich:a3f1c8d2e901 -->
- Edge Function 번들 사이즈가 10MB를 초과하면 배포가 거부되므로, 의존성 최소화 또는 함수 분할이 필요하다. (source: https://supabase.com/docs/guides/functions/troubleshooting)
- 546 오류는 Edge Function의 wall-clock timeout 또는 메모리/CPU 한계 초과를 의미하며, 함수 재구성 또는 작업 분할로 해소해야 한다. (source: https://supabase.com/docs/guides/functions/troubleshooting)
- `_shared/*` 파일이 배포 payload에 누락되면 런타임 첫 호출에서 import 에러(500)가 발생하므로, 배포 직후 스모크 호출로 즉시 확인해야 한다.

## Operational Guardrails
<!-- enrich:b7d4e2f0c512 -->
- Static egress IP 허용 목록은 Supabase Edge에서 지원하지 않으므로, 외부 방화벽 IP 화이트리스트 정책이 필요한 경우 대안 아키텍처를 설계해야 한다. (source: https://supabase.com/docs/guides/functions/troubleshooting)
- CI/CD 환경에서 배포 전 `supabase link --project-ref <id>` 선행 없이 `deploy` 실행 시 프로젝트 미지정 오류가 발생하므로, 링크 단계를 파이프라인 앞에 배치해야 한다. (source: https://supabase.com/docs/guides/functions/deploy)
