#!/usr/bin/env python3
# patrol_route_optimizer.py — 저장맵(pgm)에서 데이터 기반 최적 순찰 루프를 산출한다.
#   전제(2026-07-10 사용자 확인): 중앙 세로벽으로 좌·우 두 구역 + 사이 좁은 회랑, 두 구역 다 순찰 필수,
#   내부 기둥 2개는 실물이 맵보다 ~8cm 큼(grazing).
# 전략:
#   ① 내부 기둥을 GROW_PX(8cm) 팽창(진실맵) → ② clearance field →
#   ③ 안전영역(여유≥SAFE)에서 farthest-point 앵커 뽑기(양 구역·구석 자동 포함) →
#   ④ 앵커를 독 기준 nearest-neighbor 순회 → 각 구간을 '최대-병목여유(widest) 경로'로 연결(스퀴즈 최소) →
#   ⑤ 여유보장 그리디 단순화(모든 레그 직선 최소여유≥ROBOT) → 웨이포인트 →
#   ⑥ 레그·커버리지 검증 + ASCII. 왕복(out-and-back)이 기본(벽 분리 위상).
import math, heapq, json, sys, os
from collections import deque

_MAPS = os.environ.get("URHYNIX_MAPS",
                       os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "urhynix_nav", "maps"))
PGM = os.path.join(_MAPS, "arena_shared", "arena_shared.pgm")
RES, OX, OY = 0.020, -0.241, -0.236
GROW_PX = 0        # 기둥 팽창 안 함 — 팽창은 좌·우 연결 회랑(0.18→0.14)을 inflation 아래로 좁혀 막음.
                   #   grazing은 경로 정중앙화로 해결(방 중심 여유 0.42, 회랑 정중앙 0.18). 2026-07-10 측정.
ROBOT = 0.13       # 로봇 반폭(레그 직선 최소여유 하한)
SAFE = 0.15        # 안전영역/앵커 임계(회랑 정중앙 0.18보다 낮아 두 구역 연결 유지)
N_ANCHOR = 6       # farthest-point 앵커 수


def load(pgm):
    with open(pgm, 'rb') as f:
        assert f.readline().strip() == b'P5'
        l = f.readline()
        while l.startswith(b'#'):
            l = f.readline()
        W, H = map(int, l.split()); int(f.readline()); data = f.read()
    return W, H, [[(255 - data[r * W + c]) / 255.0 > 0.65 for c in range(W)] for r in range(H)]


def interior(W, H, occ):
    lab = [[0] * W for _ in range(H)]; cells = []
    for r in range(H):
        for c in range(W):
            if occ[r][c] and lab[r][c] == 0:
                q = deque([(r, c)]); lab[r][c] = 1; px = []; bd = False
                while q:
                    y, x = q.popleft(); px.append((y, x))
                    if y in (0, H - 1) or x in (0, W - 1): bd = True
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W and occ[ny][nx] and lab[ny][nx] == 0:
                                lab[ny][nx] = 1; q.append((ny, nx))
                if not bd: cells += px
    return cells


def grow(W, H, occ, cells, rad):
    o = [row[:] for row in occ]
    for (y, x) in cells:
        for dy in range(-rad, rad + 1):
            for dx in range(-rad, rad + 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W: o[ny][nx] = True
    return o


def clearance(W, H, occ):
    INF = 10 ** 9; d = [[INF] * W for _ in range(H)]; q = deque()
    for r in range(H):
        for c in range(W):
            if occ[r][c]: d[r][c] = 0; q.append((r, c))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and d[ny][nx] > d[y][x] + 1:
                    d[ny][nx] = d[y][x] + 1; q.append((ny, nx))
    return d


def widest_path(safe, clrp, src, dst, W, H):
    """src→dst 경로 중 '최소여유(병목)를 최대화'하는 경로(maximin). 스퀴즈를 최대한 피함."""
    best = [[-1.0] * W for _ in range(H)]; prev = {}
    br, bc = src; best[br][bc] = clrp(br, bc)
    pq = [(-best[br][bc], br, bc)]
    while pq:
        nb, y, x = heapq.heappop(pq); nb = -nb
        if nb < best[y][x]: continue
        if (y, x) == dst: break
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == dx == 0: continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and safe[ny][nx]:
                    bottleneck = min(nb, clrp(ny, nx))
                    if bottleneck > best[ny][nx]:
                        best[ny][nx] = bottleneck; prev[(ny, nx)] = (y, x)
                        heapq.heappush(pq, (-bottleneck, ny, nx))
    if best[dst[0]][dst[1]] < 0: return []
    path = [dst]; cur = dst
    while cur != src:
        cur = prev[cur]; path.append(cur)
    return path[::-1]


def main():
    W, H, occ0 = load(PGM)
    occ = grow(W, H, occ0, interior(W, H, occ0), GROW_PX)
    d = clearance(W, H, occ)
    clrp = lambda r, c: d[r][c] * RES
    w2p = lambda wx, wy: (int(round((wx - OX) / RES)), H - 1 - int(round((wy - OY) / RES)))
    p2w = lambda c, r: (round(OX + c * RES, 2), round(OY + (H - 1 - r) * RES, 2))
    safe = [[(not occ[r][c]) and clrp(r, c) >= SAFE for c in range(W)] for r in range(H)]
    # 독 최근접 안전셀
    dc, dr = w2p(0.038, 1.405)
    if not safe[dr][dc]:
        dr, dc = min(((r, c) for r in range(H) for c in range(W) if safe[r][c]),
                     key=lambda rc: (rc[0] - dr) ** 2 + (rc[1] - dc) ** 2)
    # 도달 안전영역
    reach = [[False] * W for _ in range(H)]; q = deque([(dr, dc)]); reach[dr][dc] = True
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and safe[ny][nx] and not reach[ny][nx]:
                    reach[ny][nx] = True; q.append((ny, nx))
    cells = [(r, c) for r in range(H) for c in range(W) if reach[r][c]]

    # 방 중심(구역별 최고여유점) + 독을 잇는 단일 스파인. 왕복은 브리지가 역순 복귀.
    #   과거 난잡함의 교훈: 다수 앵커 NN 순회는 widest-path가 서로 교차 → 단일 스파인이 최적·최소.
    Lc = max((rc for rc in cells if OX + rc[1] * RES < 0.5), key=lambda rc: clrp(*rc))
    Rc = max((rc for rc in cells if OX + rc[1] * RES > 0.9), key=lambda rc: clrp(*rc))
    spine = []
    for a, b in [((dr, dc), Lc), (Lc, Rc)]:
        seg = widest_path(reach, clrp, a, b, W, H)
        spine += seg if not spine else seg[1:]

    def segmin(a, b, n=None):
        n = n or max(2, int(math.hypot(a[0] - b[0], a[1] - b[1]) * 2))
        m = 9
        for k in range(n + 1):
            r = a[0] + (b[0] - a[0]) * k / n; c = a[1] + (b[1] - a[1]) * k / n
            m = min(m, clrp(int(round(r)), int(round(c))))
        return m

    def perp(p, a, b):
        if a == b:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        num = abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1]))
        return num / math.hypot(b[0] - a[0], b[1] - a[1])

    import sys as _sys
    _sys.setrecursionlimit(10000)

    def simplify(i, j):
        # 재귀 분할: 레그 직선 최소여유≥ROBOT 이고 스파인 이탈≤3px면 유지, 아니면 최대이탈점서 분할
        if j <= i + 1:
            return [i, j]
        mp, idx = 0, i
        for k in range(i + 1, j):
            dd = perp(spine[k], spine[i], spine[j])
            if dd > mp:
                mp, idx = dd, k
        if segmin(spine[i], spine[j]) >= ROBOT and mp <= 3.0:
            return [i, j]
        if idx <= i or idx >= j:
            idx = (i + j) // 2
        return simplify(i, idx)[:-1] + simplify(idx, j)
    keep = simplify(0, len(spine) - 1)
    fwd = [p2w(spine[k][1], spine[k][0]) for k in keep]
    ded = [fwd[0]]
    for p in fwd[1:]:
        if p != ded[-1]: ded.append(p)
    fwd = ded
    wps = fwd + fwd[-2::-1]   # 왕복(순방향 + 역순 복귀)

    print(f"맵 {W}x{H} · 팽창 {GROW_PX*RES*100:.0f}cm · 안전임계 {SAFE}m · 앵커 {N_ANCHOR} · 왕복 웨이포인트 {len(wps)}")
    worst = 9
    for i in range(len(wps) - 1):
        a, b = wps[i], wps[i + 1]
        pa = w2p(*a); pb = w2p(*b)
        m = segmin((pa[1], pa[0]), (pb[1], pb[0]))
        worst = min(worst, m)
        print(f"  wp{i+1}({a[0]:+.2f},{a[1]:+.2f})→wp{i+2}({b[0]:+.2f},{b[1]:+.2f}) 여유{m:.2f}m{'  ✗' if m < ROBOT else ''}")
    fs = [(r, c) for r in range(H) for c in range(W) if not occ[r][c]]

    def p2seg(px, py, a, b):
        ax, ay, bx, by = a[0], a[1], b[0], b[1]; dx, dy = bx - ax, by - ay
        if dx == dy == 0: return math.hypot(px - ax, py - ay)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
    segs = [(wps[i], wps[i + 1]) for i in range(len(wps) - 1)]
    cov = sum(1 for r, c in fs if min(p2seg(*p2w(c, r), a, b) for a, b in segs) <= 0.7)
    print(f"최악 레그여유={worst:.2f}m (기존=0.04m) · 커버리지(0.7m내)={100*cov//len(fs)}%")
    # 순방향 유니크 웨이포인트(브리지 입력용) = 왕복 전 절반
    fwd = wps[:len(wps) // 2 + 1]
    print("순방향(브리지 입력) 웨이포인트:", [(x, y) for x, y in fwd])
    json.dump({"forward": fwd, "full": wps, "worst_clr": worst,
               "coverage": 100 * cov // len(fs)},
              open("/tmp/patrol_route.json", "w"))
    return wps


if __name__ == "__main__":
    main()
