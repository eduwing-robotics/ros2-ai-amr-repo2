# scan_vs_map_check.py — 라이브 라이다 스캔 1장을 로봇 위치추정 좌표로 저장맵에 오버레이 렌더.
# "맵의 벽/장애물이 현실과 일치하는가"를 일치율(%)+그림으로 판정 (2026-07-08 젠지 98.5% PASS).
# 사용: ①로봇에서 스캔 캡처(rclpy로 tf map→scan프레임 + /scan 1장을 JSON 덤프 — urhynix-t1-amcl-saved-map
#   스킬 "맵-현실 정합 검증" 절 참조) ②python3 scan_vs_map_check.py <scan.json> <out.png> [--fit]
# --fit: (dx,dy,dyaw) 그리드 탐색으로 포즈 오차를 분리 — 보정 후 일치율이 높으면 맵은 맞고 위치추정이
#   틀린 것(그 보정값으로 AMCL 재시딩 가능), 보정해도 낮으면 맵≠현실(재SLAM 검토).
import json
import math
import sys
import os

from PIL import Image, ImageDraw

_MAPS = os.environ.get("URHYNIX_MAPS",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "urhynix_nav", "maps"))
MAP_PGM = os.path.join(_MAPS, "arena_shared", "arena_shared.pgm")
MAP_YAML = os.path.join(_MAPS, "arena_shared", "arena_shared.yaml")
SCAN_JSON = sys.argv[1]
OUT_PNG = sys.argv[2]
SCALE = 8  # 확대 배율

meta = {}
for line in open(MAP_YAML):
    if ":" in line:
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()
res = float(meta["resolution"])
ox, oy = [float(v) for v in meta["origin"].strip("[]").split(",")[:2]]

img = Image.open(MAP_PGM).convert("L")
W, H = img.size
px = img.load()

scan = json.load(open(SCAN_JSON))
rx, ry, ryaw = scan["x"], scan["y"], scan["yaw"]

rays = [(scan["amin"] + i * scan["ainc"], r) for i, r in enumerate(scan["ranges"])
        if scan["rmin"] < r < scan["rmax"] and math.isfinite(r)]
pts = [(rx + r * math.cos(ryaw + a), ry + r * math.sin(ryaw + a)) for a, r in rays]

def to_px(wx, wy):
    return (wx - ox) / res, H - (wy - oy) / res  # pgm은 y 뒤집힘

# 일치율: 스캔점이 점유(occupied, 어두운 픽셀) 셀에서 2셀(10cm) 이내인가
def occupied_near(cx, cy, rad=2):
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            x, y = int(cx) + dx, int(cy) + dy
            if 0 <= x < W and 0 <= y < H and px[x, y] < 100:
                return True
    return False

match = sum(1 for wx, wy in pts if occupied_near(*to_px(wx, wy)))

out = img.convert("RGB").resize((W * SCALE, H * SCALE), Image.NEAREST)
d = ImageDraw.Draw(out)
for wx, wy in pts:
    cx, cy = to_px(wx, wy)
    ok = occupied_near(cx, cy)
    color = (255, 40, 40) if ok else (255, 160, 0)  # 빨강=맵과 일치, 주황=맵에 없는 것
    d.ellipse([cx * SCALE - 3, cy * SCALE - 3, cx * SCALE + 3, cy * SCALE + 3], fill=color)
gx, gy = to_px(rx, ry)
d.ellipse([gx * SCALE - 7, gy * SCALE - 7, gx * SCALE + 7, gy * SCALE + 7],
          fill=(0, 200, 90), outline=(0, 0, 0))
out.save(OUT_PNG)
print(f"points={len(pts)} match={match} rate={match/len(pts)*100:.1f}% robot=({rx:.3f},{ry:.3f},{ryaw:.3f}) map={W}x{H}@{res}m origin=({ox},{oy})")

if "--fit" in sys.argv:
    def rate(dx, dy, dyaw):
        m = 0
        for a, r in rays:
            wx = rx + dx + r * math.cos(ryaw + dyaw + a)
            wy = ry + dy + r * math.sin(ryaw + dyaw + a)
            if occupied_near(*to_px(wx, wy)):
                m += 1
        return m / len(rays)
    best = (rate(0, 0, 0), 0.0, 0.0, 0.0)
    for dg in range(-6, 7):
        dyaw = math.radians(dg)
        for ix in range(-5, 6):
            for iy in range(-5, 6):
                v = rate(ix * 0.02, iy * 0.02, dyaw)
                if v > best[0]:
                    best = (v, ix * 0.02, iy * 0.02, dyaw)
    print(f"fit: best={best[0]*100:.1f}% at dx={best[1]:.2f} dy={best[2]:.2f} dyaw={math.degrees(best[3]):.1f}deg"
          f" → corrected pose=({rx+best[1]:.3f},{ry+best[2]:.3f},{ryaw+best[3]:.3f})")
