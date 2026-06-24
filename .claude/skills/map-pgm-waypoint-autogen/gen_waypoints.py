#!/usr/bin/env python3
# gen_waypoints.py — 점유격자맵(.pgm/.yaml)에서 벽 클리어런스 띄운 자유공간 순찰 웨이포인트 N개 자동 생성.
# 클리어런스 침식 + farthest-point sampling + 폴라 정렬 + yaw(다음점 향함) → FollowWaypoints YAML + ASCII 오버레이.
# 사용: python3 gen_waypoints.py --pgm map.pgm --yaml map.yaml --n 8 --clearance 0.15 --start 0,0 --robot tb3_1 --out wp.yaml
import argparse, math, re

def load_pgm(path):
    d = open(path, 'rb').read()
    assert d[:2] == b'P5', "P5(binary) PGM만 지원"
    i, vals = 2, []
    while len(vals) < 3:
        while d[i] in b' \t\n\r': i += 1
        if d[i:i+1] == b'#':
            while d[i] not in b'\n': i += 1
            continue
        s = i
        while d[i] not in b' \t\n\r': i += 1
        vals.append(int(d[s:i]))
    w, h, _ = vals
    i += 1
    return w, h, d[i:i+w*h]

def load_yaml(path):
    txt = open(path).read()
    res = float(re.search(r"resolution:\s*([-\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    return res, float(o.group(1)), float(o.group(2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pgm', required=True); ap.add_argument('--yaml', required=True)
    ap.add_argument('--n', type=int, default=8); ap.add_argument('--clearance', type=float, default=0.15)
    ap.add_argument('--start', default=None, help='x,y (생략 시 첫 안전셀)')
    ap.add_argument('--robot', default='tb3_1'); ap.add_argument('--out', default='waypoints.yaml')
    a = ap.parse_args()

    w, h, pix = load_pgm(a.pgm); res, ox, oy = load_yaml(a.yaml)
    val = lambda r, c: pix[r*w+c]
    free = lambda r, c: val(r, c) >= 250
    occ = lambda r, c: val(r, c) <= 50
    R = max(1, round(a.clearance/res))

    def safe(r, c):
        if not free(r, c): return False
        for dr in range(-R, R+1):
            for dc in range(-R, R+1):
                rr, cc = r+dr, c+dc
                if 0 <= rr < h and 0 <= cc < w and occ(rr, cc): return False
        return True

    cells = [(r, c) for r in range(h) for c in range(w) if safe(r, c)]
    if len(cells) < a.n:
        print(f"⚠️ 안전셀 {len(cells)}개 < n={a.n}. clearance를 줄이세요.");
    to_world = lambda r, c: (ox+(c+0.5)*res, oy+(h-1-r+0.5)*res)
    pts = [to_world(r, c) for r, c in cells]
    d2 = lambda p, q: (p[0]-q[0])**2+(p[1]-q[1])**2

    if a.start:
        sx, sy = map(float, a.start.split(','))
        seed = min(range(len(pts)), key=lambda i: d2(pts[i], (sx, sy)))
        start = (sx, sy)
    else:
        seed = 0; start = pts[0]
    chosen = [seed]
    for _ in range(a.n):
        chosen.append(max(range(len(pts)), key=lambda i: min(d2(pts[i], pts[j]) for j in chosen)))
    wps = [pts[i] for i in chosen[1:a.n+1]]
    cx = sum(p[0] for p in wps)/len(wps); cy = sum(p[1] for p in wps)/len(wps)
    wps.sort(key=lambda p: math.atan2(p[1]-cy, p[0]-cx))

    seq = [start]+wps
    poses = []
    for i, p in enumerate(seq):
        nxt = seq[i+1] if i+1 < len(seq) else seq[0]
        yaw = math.atan2(nxt[1]-p[1], nxt[0]-p[0])
        poses.append((round(p[0], 3), round(p[1], 3), round(math.sin(yaw/2), 4), round(math.cos(yaw/2), 4), math.degrees(yaw)))
    labels = ['START']+[f'WP{i}' for i in range(1, a.n+1)]

    with open(a.out, 'w') as f:
        f.write(f"# {a.robot} 자동생성 순찰 웨이포인트 (clearance {a.clearance}m, n={a.n})\n")
        f.write(f"# frame_id: map (origin [{ox},{oy}], res {res}) — 같은 저장맵+AMCL에서 구동\n\n")
        f.write("frame_id: map\nposes:\n")
        for lab, (x, y, qz, qw, _) in zip(labels, poses):
            f.write(f"  - name: {lab}\n    header: {{frame_id: map}}\n    pose:\n")
            f.write(f"      position: {{x: {x}, y: {y}, z: 0.0}}\n")
            f.write(f"      orientation: {{x: 0.0, y: 0.0, z: {qz}, w: {qw}}}\n")

    print(f"안전셀 {len(cells)} / R={R}칸. {len(labels)}점 생성 → {a.out}")
    for lab, (x, y, _, _, yd) in zip(labels, poses):
        print(f"  {lab:6} x={x:7.3f} y={y:7.3f} yaw={yd:6.1f}°")
    # ASCII overlay
    mark = {}
    for lab, (x, y, *_), idx in zip(labels, poses, range(len(poses))):
        c = int((x-ox)/res-0.5); r = int(h-1-((y-oy)/res-0.5))
        mark[(r, c)] = 'S' if idx == 0 else str(idx)
    print("\n(S=start, 숫자=waypoint):")
    rows = [r for r, _ in cells] or [0]
    cols = [c for _, c in cells] or [0]
    for r in range(max(0, min(rows)-2), min(h, max(rows)+3)):
        line = ''
        for c in range(max(0, min(cols)-2), min(w, max(cols)+3)):
            line += mark.get((r, c)) or ('.' if free(r, c) else ('#' if occ(r, c) else ' '))
        print(line)

if __name__ == '__main__':
    main()
