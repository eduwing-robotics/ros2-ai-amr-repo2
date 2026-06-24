---
name: supabase-db-health-ping
description: anon 키로 Supabase REST를 핑해서 DB 생존·인증·테이블별 행수를 5초에 점검하는 read-only 헬스체크. "DB 연결됐나/살았나" 빠른 확인용. supabase-mcp(마이그레이션/Edge/ops)와 분리된 가벼운 입구. URHYNIX session_meta/events/dispatches/camera_captures/pose_logs. 2026-06-23 도출.
user_invocable: true
tags: [supabase, database, healthcheck, urhynix]
version: 1
---

# Supabase DB Health Ping

Supabase DB가 살아있는지, anon 키 인증이 되는지, 각 테이블에 행이 얼마나 있는지 **읽기 전용으로 5초에** 확인한다. 마이그레이션·배포는 [[supabase-mcp]]; 이 스킬은 "연결됐나"만 본다.

## Use When

- 세션 시작 시 DB 생존 확인
- Unity/로봇 writer가 "DB 안 써진다" 할 때 1차 분리(연결 vs 권한 vs 코드)
- pose_logs/events에 데이터가 실제로 쌓이는지 빠른 확인

## One-Liner

```bash
bash .claude/skills/supabase-db-health-ping/db_ping.sh
# 설정: unity/ControlRoom/Assets/Resources/SupabaseConfig/supabase.json 에서 url+anonKey 자동 로드
# 환경변수 SB_TABLES 로 점검 테이블 목록 덮어쓰기 가능
```

## 판정 기준

| 응답 | 의미 |
|---|---|
| `http=200` | 연결+인증+RLS 읽기 정상 |
| `http=401` | 키 누락/잘못됨 (URL은 도달) |
| `http=404` | 테이블 없음(마이그레이션 미적용) |
| timeout/000 | 네트워크/URL 문제 |
| `content-range: */0` | 테이블 비었거나 count가 RLS로 막힘 |
| `content-range: 0-0/N` | N행 존재 |

## 함정표

| 함정 | 회피 |
|---|---|
| 키 노출 | 화면/로그에 anonKey 절대 출력 금지(길이만). supabase.json은 git 제외([[secret-scan]]) |
| count 막힘 | `Prefer: count=exact` 헤더 + HEAD 요청. RLS가 select 막으면 limit=1로 200만 확인 |
| service_role 오용 | Unity/클라이언트 경로 점검엔 anon만. service_role로 점검하면 RLS 우회라 실제와 다름 |

## 검증

- 핵심 테이블(events 등)이 200 + 행수 증가가 보이면 쓰기 경로도 정상.
- 0행인데 200이면 연결은 OK, 데이터 미유입(writer 쪽 문제로 좁힘).

관련: [[supabase-mcp]] · [[api-contract-guard]] · [[secret-scan]]
