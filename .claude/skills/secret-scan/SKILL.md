---
name: secret-scan
description: 커밋/푸시 전에 토큰·키·비밀번호 노출 위험을 빠르게 점검. URHYNIX에 슬랙 토큰, Supabase URL/키, Jira API 토큰, Telegram 봇 토큰이 있을 수 있어 정기 점검 필요.
---

# secret-scan — 비밀 노출 점검

## When to use

- `git commit` 또는 `git push` 직전
- 새 환경변수/.env 파일을 추가했을 때
- 외부에 코드 공유(PR/지라/슬랙) 직전
- 주 1회 정기 감사

## Quick Run

```bash
# URHYNIX 루트에서
bash .claude/skills/secret-scan/scan.sh
```

스크립트가 없으면 아래 inline 명령으로 즉시 실행:

```bash
cd /Users/family/jason/URHYNIX
git ls-files | xargs grep -nE \
  '(xox[baprs]-[0-9a-zA-Z-]{10,}|sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z_-]{35}|ghp_[a-zA-Z0-9]{36}|eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+|supabase\.co.*service_role|postgres://[^@]+:[^@]+@|bot[0-9]+:[A-Za-z0-9_-]{35,})' \
  2>/dev/null | grep -vE '\.lock|node_modules|\.env\.example'
```

## 패턴 (URHYNIX 환경 가정)

| 패턴 | 의미 | 정규식 |
|---|---|---|
| Slack Bot Token | `xoxb-...` | `xox[baprs]-[0-9a-zA-Z-]{10,}` |
| OpenAI/Anthropic key | `sk-...` | `sk-[a-zA-Z0-9]{20,}` |
| Google API key | `AIza...` | `AIza[0-9A-Za-z_-]{35}` |
| GitHub PAT | `ghp_...` | `ghp_[a-zA-Z0-9]{36}` |
| JWT | `eyJ...` | `eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+` |
| Supabase service_role | `*.supabase.co...service_role` | `supabase\.co.*service_role` |
| Postgres URL | `postgres://user:pass@...` | `postgres://[^@]+:[^@]+@` |
| Telegram Bot | `123456:ABC...` | `bot[0-9]+:[A-Za-z0-9_-]{35,}` |

## 단계

1. `git ls-files`로 추적 중인 파일만 스캔 (node_modules, .env.example 등 제외)
2. 위 정규식 8종으로 grep
3. 매칭 시: 파일경로:라인번호 + 마스킹된 매치 표시 (앞 4자 + `***` + 뒤 4자)
4. 발견 시: `.gitignore` 추가 또는 환경변수로 분리 권고
5. 결과를 `docs/status/SECRET-SCAN-{YYYY-MM-DD}.md` 에 기록

## 제외 규칙

- `.env.example` (의도된 placeholder)
- `*.lock`, `node_modules/`
- `unity-src/Library/`, `unity-src/Temp/`
- `docs/_archived-fr5/` (legacy 참고 문서)

## 출력 형식

```
🔍 secret-scan 결과 (2026-MM-DD)
스캔: 79 files
발견: 0건 ✅
```

또는

```
🔍 secret-scan 결과 (2026-MM-DD)
스캔: 79 files
발견: 2건 ⚠️
1. src/config.ts:12  Slack Bot Token (xoxb***abcd)
2. .env:3            Supabase service_role
→ 즉시 .gitignore 추가 또는 환경변수로 이동 필요
```

## 한줄정리

URHYNIX 루트에서 `bash .claude/skills/secret-scan/scan.sh` 한 번이면 8종 시크릿 패턴 자동 점검.
