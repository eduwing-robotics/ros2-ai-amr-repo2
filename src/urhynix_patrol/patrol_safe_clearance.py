#!/usr/bin/env python3
# patrol_safe_clearance.py — 순찰 웨이포인트가 벽 안전여유(로봇반경+inflation) 안쪽이면
# 가장 가까운 안전 지점으로 밀어낸다. arena_shared.pgm 점유격자 기준 거리변환으로 계산.
# 웨이포인트끼리 뭉치지 않도록 이미 확정된 지점 반경 안도 배제한다.
# 사용: python3 patrol_safe_clearance.py <patrol.json> <out.json> [min_clearance_m=0.25] [min_separation_m=0.2]
import json
import re
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from pgm_to_sdf_walls import load_pgm

MAP_PGM = "docs/evidence/maps/arena_shared/arena_shared.pgm"
MAP_YAML = "docs/evidence/maps/arena_shared/arena_shared.yaml"


def main():
    if len(sys.argv) < 3:
        print("사용: patrol_safe_clearance.py <patrol.json> <out.json> [min_clearance_m=0.4]")
        sys.exit(1)
    src_json, out_json = sys.argv[1], sys.argv[2]
    min_clear_m = float(sys.argv[3]) if len(sys.argv) > 3 else 0.25
    min_sep_m = float(sys.argv[4]) if len(sys.argv) > 4 else 0.2

    txt = open(MAP_YAML).read()
    res = float(re.search(r"resolution:\s*([\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    ox, oy = float(o.group(1)), float(o.group(2))
    w, h, data = load_pgm(MAP_PGM)

    grid = np.frombuffer(data, dtype=np.uint8).reshape(h, w).astype(np.int16)
    occ_ys, occ_xs = np.where(grid < 50)  # 점유(벽) 픽셀 좌표들

    yy, xx = np.mgrid[0:h, 0:w]
    # 각 free 픽셀 -> 가장 가까운 점유 픽셀까지 최소거리(px). 벽 픽셀 수가 적어 브로드캐스트로 충분히 빠름.
    clearance_px = np.full((h, w), 1e9)
    for oy_px, ox_px in zip(occ_ys, occ_xs):
        d2 = (yy - oy_px) ** 2 + (xx - ox_px) ** 2
        np.minimum(clearance_px, d2, out=clearance_px)
    clearance_px = np.sqrt(clearance_px)

    min_clear_px = min_clear_m / res
    safe_mask = clearance_px >= min_clear_px

    def world_to_px(wx, wy):
        return (wx - ox) / res, h - 1 - (wy - oy) / res

    def px_to_world(px, py):
        return ox + px * res, oy + (h - 1 - py) * res

    safe_ys, safe_xs = np.where(safe_mask)
    min_sep_px = min_sep_m / res

    patrol = json.load(open(src_json))
    report = []
    placed_px = []  # 이미 확정된 웨이포인트들의 (px,py) — 뒤 웨이포인트가 여기 뭉치지 않게 배제
    for pt in patrol["points"]:
        wx, wy = pt["x"], pt["y"]
        px, py = world_to_px(wx, wy)
        iy, ix = int(round(py)), int(round(px))
        cur_clear_m = clearance_px[max(0, min(h - 1, iy)), max(0, min(w - 1, ix))] * res

        cand_xs, cand_ys = safe_xs, safe_ys
        for ppx, ppy in placed_px:
            keep = (cand_xs - ppx) ** 2 + (cand_ys - ppy) ** 2 >= min_sep_px ** 2
            cand_xs, cand_ys = cand_xs[keep], cand_ys[keep]

        too_close_to_others = any(
            (px - ppx) ** 2 + (py - ppy) ** 2 < min_sep_px ** 2 for ppx, ppy in placed_px)
        if cur_clear_m >= min_clear_m and not too_close_to_others:
            report.append((pt["seq"], wx, wy, wx, wy, cur_clear_m, cur_clear_m, 0.0))
            placed_px.append((px, py))
            continue

        d2 = (cand_xs - px) ** 2 + (cand_ys - py) ** 2
        best = np.argmin(d2)
        npx, npy = int(cand_xs[best]), int(cand_ys[best])
        nwx, nwy = px_to_world(npx, npy)
        new_clear_m = clearance_px[npy, npx] * res
        disp = ((nwx - wx) ** 2 + (nwy - wy) ** 2) ** 0.5
        report.append((pt["seq"], wx, wy, nwx, nwy, cur_clear_m, new_clear_m, disp))
        pt["x"], pt["y"] = float(nwx), float(nwy)
        placed_px.append((npx, npy))

    json.dump(patrol, open(out_json, "w"), indent=4, ensure_ascii=False)

    print(f"{'seq':>3} {'old(x,y)':>18} {'new(x,y)':>18} {'clear m→m':>12} {'이동(m)':>8}")
    for seq, ox0, oy0, nx, ny, c0, c1, disp in report:
        moved = "이동" if disp > 0.001 else "그대로"
        print(f"{seq:>3} ({ox0:6.3f},{oy0:6.3f}) ({nx:6.3f},{ny:6.3f}) {c0:5.2f}->{c1:5.2f}  {disp:5.3f}  {moved}")
    print(f"\n{out_json} 저장 완료 (최소 여유거리 {min_clear_m}m, 웨이포인트 간 최소간격 {min_sep_m}m 기준)")


if __name__ == "__main__":
    main()
