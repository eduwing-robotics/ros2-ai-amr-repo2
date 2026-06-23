#!/usr/bin/env python3
# 시나리오 다이어그램을 단일 자기완결 HTML로 번들 — 외부 <script src> 8개(vendor·data·engine)를 본문에 inline.
# 산출물: scenarios-bundle.html (더블클릭 1파일, 슬랙 업로드용). 소스 수정 후 재실행: python3 build_bundle.py
import re, pathlib, sys

HERE = pathlib.Path(__file__).parent
SRC = HERE / "index.html"
OUT = HERE / "scenarios-bundle.html"

html = SRC.read_text(encoding="utf-8")

# <script src="path"></script> 를 파일 내용 inline 으로 치환 (순서 보존)
pat = re.compile(r'<script src="([^"]+)"></script>')

def inline(m):
    rel = m.group(1)
    p = (HERE / rel).resolve()
    if not p.exists():
        print(f"  ! 누락: {rel}", file=sys.stderr); sys.exit(1)
    code = p.read_text(encoding="utf-8")
    code = code.replace("</script", "<\\/script")  # 조기 종료 방지
    print(f"  + inline {rel} ({len(code):,} bytes)")
    return f"<script>/* inlined: {rel} */\n{code}\n</script>"

bundled = pat.sub(inline, html)
note = "<!-- 단일 파일 번들(자동생성). 원본/재빌드: docs/presentation/scenarios/build_bundle.py -->\n"
bundled = bundled.replace("<!doctype html>", "<!doctype html>\n" + note, 1)

OUT.write_text(bundled, encoding="utf-8")
print(f"\n✓ {OUT.name} 생성 ({OUT.stat().st_size:,} bytes) — 이 파일 하나만 슬랙에 올리면 됩니다.")
