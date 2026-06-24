#!/usr/bin/env bash
# db_ping.sh — Supabase DB 생존·인증·테이블별 행수를 anon 키로 read-only 점검(5초).
# 키는 노출하지 않음(길이만). supabase.json에서 url+anonKey 자동 로드.
# 사용: bash db_ping.sh   /   SB_TABLES="events pose_logs" bash db_ping.sh
set -euo pipefail

CFG="${SB_CONFIG:-/Users/family/jason/URHYNIX/unity/ControlRoom/Assets/Resources/SupabaseConfig/supabase.json}"
TABLES="${SB_TABLES:-session_meta events dispatches camera_captures pose_logs}"

URL=$(python3 -c "import json;print(json.load(open('$CFG')).get('url',''))")
KEY=$(python3 -c "import json;d=json.load(open('$CFG'));print(d.get('anonKey') or d.get('anon_key') or d.get('key') or '')")
echo "URL=$URL  (anonKey ${#KEY}자)"

echo "--- 연결/인증 ---"
curl -s -o /dev/null -w "REST root http=%{http_code} time=%{time_total}s\n" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" "$URL/rest/v1/" --max-time 8

echo "--- 테이블 행수 ---"
for t in $TABLES; do
  cr=$(curl -s -I -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Prefer: count=exact" \
       "$URL/rest/v1/$t?select=*&limit=1" --max-time 8 | grep -i content-range | tr -d '\r' || true)
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
       "$URL/rest/v1/$t?select=*&limit=1" --max-time 8)
  echo "  $t -> http=$code  ${cr:-(count 없음)}"
done
