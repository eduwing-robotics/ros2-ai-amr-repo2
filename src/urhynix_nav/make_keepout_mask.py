#!/usr/bin/env python3
# make_keepout_mask.py — arena_shared.pgm/yaml과 같은 해상도/원점으로 원형 keepout 마스크(pgm+yaml)를 굽는다.
# nav2 KeepoutFilter가 읽는 마스크: 흰색(254)=자유, 검정(0)=진입금지(lethal). [[urhynix-t1-nav2-patrol-drive]] 확장.
# 사용: python3 make_keepout_mask.py <src.pgm> <src.yaml> <out.pgm> <out.yaml> <cx> <cy> <radius_m>
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgm_to_sdf_walls import load_pgm


def main():
    if len(sys.argv) < 8:
        print("사용: make_keepout_mask.py <src.pgm> <src.yaml> <out.pgm> <out.yaml> <cx> <cy> <radius_m>")
        sys.exit(1)
    src_pgm, src_yaml, out_pgm, out_yaml = sys.argv[1:5]
    cx, cy, radius_m = (float(v) for v in sys.argv[5:8])

    txt = open(src_yaml).read()
    res = float(re.search(r"resolution:\s*([\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    ox, oy = float(o.group(1)), float(o.group(2))

    w, h, _data = load_pgm(src_pgm)

    def world_to_px(wx, wy):
        return (wx - ox) / res, h - 1 - (wy - oy) / res

    pcx, pcy = world_to_px(cx, cy)
    r_px = radius_m / res

    mask = bytearray(b"\xfe" * (w * h))  # 254 = free
    x0, x1 = max(0, int(pcx - r_px) - 1), min(w - 1, int(pcx + r_px) + 1)
    y0, y1 = max(0, int(pcy - r_px) - 1), min(h - 1, int(pcy + r_px) + 1)
    for py in range(y0, y1 + 1):
        for px in range(x0, x1 + 1):
            if (px - pcx) ** 2 + (py - pcy) ** 2 <= r_px ** 2:
                mask[py * w + px] = 0  # occupied = keepout

    with open(out_pgm, "wb") as f:
        f.write(f"P5\n{w} {h}\n255\n".encode())
        f.write(bytes(mask))

    with open(out_yaml, "w") as f:
        f.write(f"image: {os.path.basename(out_pgm)}\n")
        f.write("mode: trinary\n")
        f.write(f"resolution: {res}\n")
        f.write(f"origin: [{ox}, {oy}, 0]\n")
        f.write("negate: 0\n")
        f.write("occupied_thresh: 0.65\n")
        f.write("free_thresh: 0.196\n")

    print(f"{out_pgm}: keepout 반경 {radius_m}m @ ({cx},{cy}) -> px({pcx:.1f},{pcy:.1f}) r={r_px:.1f}px")


if __name__ == "__main__":
    main()
