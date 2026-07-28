#!/usr/bin/env bash
# AI-Hub 다운로드 zip 압축 해제 (VS/VL/TL/TS 등)
set -eo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)/datasets/aihub_71472}"

find "${ROOT}" -name '*.zip' -type f | while read -r zip; do
  dir="$(dirname "${zip}")"
  echo "[INFO] Extracting ${zip} → ${dir}"
  unzip -o -q "${zip}" -d "${dir}"
done

echo "[OK] Extraction done under ${ROOT}"
find "${ROOT}" -name '*.jpg' 2>/dev/null | wc -l | xargs -I{} echo "  JPG files: {}"
find "${ROOT}" -name '*.txt' 2>/dev/null | wc -l | xargs -I{} echo "  TXT labels: {}"
