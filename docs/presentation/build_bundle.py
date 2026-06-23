#!/usr/bin/env python3
# 발표(7덱)를 단일 자기완결 HTML로 번들 — 외부 <script src>(engine·decks)를 inline + img/*.png 를 base64 data URI로 내장.
# 산출물: presentation-bundle.html (더블클릭 1파일, 슬랙/메일/USB 공유용). 소스 수정 후 재실행: python3 build_bundle.py
# 주의: 🗺 시나리오 링크는 별도 트랙 — 필요하면 scenarios/scenarios-bundle.html 을 같이 공유한다.
import re, base64, mimetypes, pathlib, sys

HERE = pathlib.Path(__file__).parent
SRC = HERE / "index.html"
OUT = HERE / "presentation-bundle.html"
IMGDIR = HERE / "img"

html = SRC.read_text(encoding="utf-8")

# 1) <script src="path"></script> → 파일 내용 inline (순서 보존)
script_pat = re.compile(r'<script src="([^"]+)"></script>')

def inline_script(m):
    rel = m.group(1)
    p = (HERE / rel).resolve()
    if not p.exists():
        print(f"  ! 스크립트 누락: {rel}", file=sys.stderr); sys.exit(1)
    code = p.read_text(encoding="utf-8").replace("</script", "<\\/script")  # 조기 종료 방지
    print(f"  + inline {rel} ({len(code):,} bytes)")
    return f"<script>/* inlined: {rel} */\n{code}\n</script>"

bundled = script_pat.sub(inline_script, html)

# 2) img/<name> 참조를 base64 data URI 로 치환 (덱 데이터의 src: "img/xxx.png")
img_count = 0
total_b64 = 0
for f in sorted(IMGDIR.glob("*")):
    if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        continue
    ref = f"img/{f.name}"
    if ref not in bundled:
        continue  # 덱에서 안 쓰는 이미지는 건너뜀
    mime = mimetypes.guess_type(f.name)[0] or "image/png"
    b64 = base64.b64encode(f.read_bytes()).decode("ascii")
    data_uri = f"data:{mime};base64,{b64}"
    n = bundled.count(ref)
    bundled = bundled.replace(ref, data_uri)
    img_count += 1
    total_b64 += len(b64)
    print(f"  + image {ref} → base64 ({len(b64):,} chars, {n}곳)")

note = ("<!-- 단일 파일 번들(자동생성). 원본/재빌드: docs/presentation/build_bundle.py\n"
        "     이미지 내장 완료. 🗺 시나리오는 별도(scenarios/scenarios-bundle.html). -->\n")
bundled = bundled.replace("<!doctype html>", "<!doctype html>\n" + note, 1)

OUT.write_text(bundled, encoding="utf-8")
print(f"\n✓ {OUT.name} 생성 ({OUT.stat().st_size:,} bytes, 이미지 {img_count}장 내장)")
print("  → 이 파일 하나만 공유하면 어디서나 오프라인으로 열립니다.")
