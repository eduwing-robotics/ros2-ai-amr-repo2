# patrol_presets.py — arena_shared 맵에서 "찍어도 되는" 검증된 순찰 프리셋 5종.
# 모든 점을 거리변환(DT)으로 벽·장애물에서 클리어런스 이상 떨어지게 스냅/검증한다.
# 오른쪽 장애물(B)은 실물이 맵보다 ~8cm 삐져나옴(2026-07-08 라이다 실측) → 가상 마진 주입.
# 사용: python3 scripts/patrol_presets.py                → 5종 검증 표
#       python3 scripts/patrol_presets.py --emit N       → Unity patrols json 출력
#       python3 scripts/patrol_presets.py --pubcmd N     → 로봇에서 실행할 ros2 pub 명령 출력(bridge가 수신)
#       python3 scripts/patrol_presets.py --render out.png → 5종 몽타주 렌더
import json
import math
import sys

from PIL import Image, ImageDraw

MAP_PGM = "/Users/family/jason/URHYNIX/docs/evidence/maps/arena_shared/arena_shared.pgm"
RES = 0.02
OX, OY = -0.241, -0.236
CLEAR = 0.25          # 최소 클리어런스(m) — patrol_safe_clearance 표준과 동일
BULGE = [(1.12, 0.48, 0.10)]  # 장애물B 실물 삐짐 가상 마진 (x, y, r)

PRESETS = {
    1: ("좌측방 세로", [(0.10, 1.15), (0.13, 0.65), (0.16, 0.30)]),
    2: ("중앙 크로스", [(0.16, 0.30), (0.70, 0.40), (1.05, 0.30), (1.42, 0.75)]),
    3: ("우측방 순회", [(1.40, 1.35), (1.00, 1.15), (1.45, 0.80), (1.05, 0.30)]),
    4: ("외곽 대순환", [(0.10, 1.15), (0.15, 0.30), (0.70, 0.32), (1.08, 0.28), (1.45, 0.80), (1.35, 1.35)]),
    5: ("전시물A 점검링", [(0.10, 0.55), (0.38, 0.85), (0.66, 0.48), (0.35, 0.22)]),
}

img = Image.open(MAP_PGM).convert("L")
W, H = img.size
px = img.load()
occ = [(x, y) for x in range(W) for y in range(H) if px[x, y] < 100]
for bx, by, br in BULGE:
    cx, cy = (bx - OX) / RES, H - (by - OY) / RES
    r = br / RES
    for x in range(int(cx - r), int(cx + r) + 1):
        for y in range(int(cy - r), int(cy + r) + 1):
            if 0 <= x < W and 0 <= y < H and (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                occ.append((x, y))

def dt(wx, wy):
    cx, cy = (wx - OX) / RES, H - (wy - OY) / RES
    if not (0 <= cx < W and 0 <= cy < H) or px[int(cx), int(cy)] < 250:
        return -1.0  # 맵 밖/미탐사/점유
    return min(math.hypot(cx - x, cy - y) for x, y in occ) * RES

def snap(wx, wy):
    if dt(wx, wy) >= CLEAR:
        return wx, wy
    best, bd = None, 9e9
    for gx in range(W):
        for gy in range(H):
            w2x, w2y = OX + (gx + 0.5) * RES, OY + (H - gy - 0.5) * RES
            if dt(w2x, w2y) >= CLEAR:
                d = math.hypot(w2x - wx, w2y - wy)
                if d < bd:
                    best, bd = (w2x, w2y), d
    return best

def validated(n):
    name, pts = PRESETS[n]
    return name, [snap(x, y) for x, y in pts]

if "--emit" in sys.argv:
    n = int(sys.argv[sys.argv.index("--emit") + 1])
    name, pts = validated(n)
    print(json.dumps({"routeId": "arena_shared", "mapId": "arena_shared", "robotId": "tb3_2",
        "points": [{"seq": i + 1, "x": round(x, 4), "y": round(y, 4), "theta": 0.0}
                   for i, (x, y) in enumerate(pts)]}, indent=2, ensure_ascii=False))
elif "--pubcmd" in sys.argv:
    n = int(sys.argv[sys.argv.index("--pubcmd") + 1])
    name, pts = validated(n)
    poses = ", ".join(f"{{position: {{x: {x:.3f}, y: {y:.3f}, z: 0.0}}, orientation: {{w: 1.0}}}}" for x, y in pts)
    print(f"ros2 topic pub --once /tb3_2/patrol_waypoints geometry_msgs/msg/PoseArray "
          f"\"{{header: {{frame_id: map}}, poses: [{poses}]}}\"")
elif "--emit-unity" in sys.argv:
    # Unity StreamingAssets/Maps/<mapId>.presets.json — PatrolPresetCatalog.cs가 로드
    out_path = sys.argv[sys.argv.index("--emit-unity") + 1]
    data = {"presets": [
        {"name": f"P{n} {PRESETS[n][0]}",
         "points": [{"seq": i + 1, "x": round(x, 4), "y": round(y, 4), "theta": 0.0}
                    for i, (x, y) in enumerate(validated(n)[1])]}
        for n in PRESETS]}
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("written:", out_path)
elif "--render" in sys.argv:
    out_path = sys.argv[sys.argv.index("--render") + 1]
    S = 8
    colors = {1: (230, 60, 60), 2: (40, 120, 255), 3: (0, 170, 90), 4: (200, 60, 200), 5: (255, 150, 0)}
    panels = []
    for n in PRESETS:
        name, pts = validated(n)
        p = img.convert("RGB").resize((W * S, H * S), Image.NEAREST)
        d = ImageDraw.Draw(p)
        xy = [((x - OX) / RES * S, (H - (y - OY) / RES) * S) for x, y in pts]
        d.line(xy, fill=colors[n], width=4)
        for i, (cx, cy) in enumerate(xy):
            d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=colors[n], outline=(0, 0, 0))
            d.text((cx - 4, cy - 7), str(i + 1), fill=(255, 255, 255))
        d.text((10, 10), f"P{n} {name}", fill=colors[n])
        panels.append(p)
    m = Image.new("RGB", (panels[0].width * 3 + 20, panels[0].height * 2 + 10), (255, 255, 255))
    for i, p in enumerate(panels):
        m.paste(p, ((i % 3) * (p.width + 10), (i // 3) * (p.height + 5)))
    m.save(out_path)
    print("rendered:", out_path)
else:
    for n in PRESETS:
        name, pts0 = PRESETS[n]
        name, pts = validated(n)
        rows = [f"({x0:.2f},{y0:.2f})→({x:.2f},{y:.2f}) dt={dt(x, y):.2f}"
                for (x0, y0), (x, y) in zip(pts0, pts)]
        ok = all(dt(x, y) >= CLEAR for x, y in pts)
        print(f"P{n} {name} [{'OK' if ok else 'FAIL'}]: " + " | ".join(rows))
