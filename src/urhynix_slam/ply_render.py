#!/usr/bin/env python3
# ply_render.py — 컬러 PLY를 numpy+PIL로 탑다운/정면 2뷰 PNG로 렌더(3D 뷰어 없이 육안 검증).
# matplotlib 불필요. 각 픽셀 빈에 '카메라쪽' 점 색을 마지막에 찍어 occlusion 근사
#   (탑다운=최고 z가 보임, 정면=가장 가까운 -y가 보임).
#   /tmp/plyenv/bin/python ply_render.py <in.ply> -o <out.png> [--px 0.02] [--cap 1400]
import argparse
import numpy as np
from PIL import Image


def read_ply(path):
    with open(path, 'rb') as f:
        n = 0
        while True:
            line = f.readline()
            if line.startswith(b'element vertex'):
                n = int(line.split()[-1])
            if line.strip() == b'end_header':
                break
        dt = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'),
                       ('r', 'u1'), ('g', 'u1'), ('b', 'u1')])
        return np.fromfile(f, dtype=dt, count=n)


def bin_view(h, v, key_last_wins, rgb, px, cap, flip_v=True):
    hmin, hmax = np.percentile(h, [0.5, 99.5])
    vmin, vmax = np.percentile(v, [0.5, 99.5])
    W = min(cap, max(2, int((hmax - hmin) / px)))
    H = min(cap, max(2, int((vmax - vmin) / px)))
    ih = np.clip((h - hmin) / max(hmax - hmin, 1e-6) * (W - 1), 0, W - 1).astype(np.int32)
    iv = np.clip((v - vmin) / max(vmax - vmin, 1e-6) * (H - 1), 0, H - 1).astype(np.int32)
    if flip_v:
        iv = (H - 1) - iv
    order = np.argsort(key_last_wins)        # 오름차순 → 마지막(=큰 값)이 덮어씀 = 카메라쪽 우선
    img = np.zeros((H, W, 3), np.uint8)
    img[iv[order], ih[order]] = rgb[order]
    return img


def view(arr, hk, vk, key_last_wins, px, cap, flip_v=True):
    rgb = np.stack([arr['r'], arr['g'], arr['b']], axis=1)
    return bin_view(arr[hk].astype(np.float32), arr[vk].astype(np.float32),
                    key_last_wins, rgb, px, cap, flip_v)


def oblique(arr, az_deg, el_deg, px, cap):
    """az(방위)·el(올려본 각)으로 점군을 회전해 비스듬한 3D 시점 렌더(직교투영, occlusion 근사)."""
    az, el = np.radians(az_deg), np.radians(el_deg)
    x = arr['x'].astype(np.float32); y = arr['y'].astype(np.float32); z = arr['z'].astype(np.float32)
    x = x - x.mean(); y = y - y.mean(); z = z - z.mean()
    xr = x * np.cos(az) - y * np.sin(az)            # yaw about z
    yr = x * np.sin(az) + y * np.cos(az)
    yr2 = yr * np.cos(el) - z * np.sin(el)          # pitch about x (tilt)
    zr2 = yr * np.sin(el) + z * np.cos(el)
    rgb = np.stack([arr['r'], arr['g'], arr['b']], axis=1)
    # 화면: h=xr, v=zr2(위), 깊이=yr2(카메라 -y) → 가까운(작은 yr2)이 마지막에 덮어씀
    return bin_view(xr, zr2, -yr2, rgb, px, cap, flip_v=True)


def label(img, text):
    # 상단 좌측에 간단 텍스트(흰 바탕 박스) — PIL 기본 폰트
    from PIL import ImageDraw
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 + 7 * len(text), 14], fill=(0, 0, 0))
    d.text((3, 2), text, fill=(255, 255, 255))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ply')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--px', type=float, default=0.02)
    ap.add_argument('--cap', type=int, default=1400)
    ap.add_argument('--turntable', action='store_true', help='비스듬한 3D 시점 여러 각도')
    ap.add_argument('--el', type=float, default=25.0, help='턴테이블 올려본 각(도)')
    a = ap.parse_args()
    arr = read_ply(a.ply)
    print(f'points={len(arr)}')

    if a.turntable:
        gap = 12
        panels = []
        for az in (0, 60, 120, 180):
            p = oblique(arr, az, a.el, a.px, a.cap)
            panels.append(label(p, f'az={az} el={int(a.el)}'))
        H = max(p.shape[0] for p in panels)
        Wt = sum(p.shape[1] for p in panels) + gap * (len(panels) - 1)
        canvas = np.full((H, Wt, 3), 30, np.uint8)
        x = 0
        for p in panels:
            canvas[:p.shape[0], x:x + p.shape[1]] = p
            x += p.shape[1] + gap
        Image.fromarray(canvas).save(a.out)
        print(f'wrote {a.out}  ({canvas.shape[1]}x{canvas.shape[0]})')
        return

    # 탑다운: 화면 x=x, y=y, 최고 z가 보임(위에서 내려다봄)
    top = label(view(arr, 'x', 'y', arr['z'].astype(np.float32), a.px, a.cap), 'TOP-DOWN (x-y)')
    # 정면: 화면 x=x, y=z(높이), 가장 가까운 -y가 보임
    front = label(view(arr, 'x', 'z', (-arr['y']).astype(np.float32), a.px, a.cap), 'FRONT (x-z, height up)')

    H = max(top.shape[0], front.shape[0])
    gap = 12
    canvas = np.full((H, top.shape[1] + gap + front.shape[1], 3), 30, np.uint8)
    canvas[:top.shape[0], :top.shape[1]] = top
    canvas[:front.shape[0], top.shape[1] + gap:] = front
    Image.fromarray(canvas).save(a.out)
    print(f'wrote {a.out}  ({canvas.shape[1]}x{canvas.shape[0]})')


if __name__ == '__main__':
    main()
