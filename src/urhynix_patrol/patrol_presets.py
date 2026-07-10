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
import os

from PIL import Image, ImageDraw

_MAPS = os.environ.get("URHYNIX_MAPS",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "urhynix_nav", "maps"))
MAP_PGM = os.path.join(_MAPS, "arena_shared", "arena_shared.pgm")
RES = 0.02
OX, OY = -0.241, -0.236
CLEAR = 0.25          # 최소 클리어런스(m) — patrol_safe_clearance 표준과 동일
BULGE = [(1.12, 0.48, 0.10)]  # 장애물B 실물 삐짐 가상 마진 (x, y, r)

# 레거시 프리셋(구 P1~5: 구 지형 이해 기반·좁은 틈 관통·오늘 grazing/잠김의 원인) 전량 제거(2026-07-10).
#   데이터 검증 최적 경로 하나로 통일 — patrol_route_optimizer.py 산출(방 중심 스파인 + 회랑 정중앙).
#   좌·우 두 구역 순찰 필수 + 회랑이 물리적 0.18m라 CLEAR 0.25 불가 → NO_SNAP(옵티마이저가 레그 0.13 검증).
PRESETS = {
    1: ("최적 안전순찰(2구역)", [(0.04, 1.40), (0.24, 1.20), (0.24, 0.96), (0.04, 0.74), (0.10, 0.28),
                                (0.52, 0.26), (0.60, 0.58), (0.90, 0.60), (0.92, 1.18), (1.14, 0.96)]),
}
NO_SNAP = {1}   # 회랑 통과 필수 → 0.25 snap이 경로를 파괴하므로 우회(옵티마이저가 레그 0.13 별도 검증)

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
    if n in NO_SNAP:                     # 옵티마이저 검증 경로 — 0.25 snap이 회랑 통과점을 파괴하므로 원본 유지
        return name, list(pts)
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
