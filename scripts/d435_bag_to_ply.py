#!/usr/bin/env python3
# d435_bag_to_ply.py — D435 rosbag(mcap)의 aligned depth+color를 deproject해 컬러 점군 PLY 생성.
# ROS 설치 불필요(rosbags 순수 python). Mac 전용 venv: /tmp/plyenv.
#   /tmp/plyenv/bin/python scripts/d435_bag_to_ply.py <bagdir...> -o out.ply [--frames N] [--frame-step K] [--zmax 4.0] [--stride 2]
#   다중 bag(같은 odom 세션) 합치기 + 긴 주행은 --frame-step으로 프레임 솎기(점 폭주 방지).
# 입력 토픽: /tb3_1/camera/aligned_depth_to_color/{image_raw,camera_info}, /tb3_1/camera/color/image_raw/compressed
# aligned depth는 color frame에 1:1 정렬 → 같은 intrinsics(color camera_info)로 deproject + color[v,u] 직접 매핑.
# 좌표계: camera_color_optical_frame (x右 y下 z前). Unity(y上 z前 왼손) 변환은 뷰어 레이어에서.
import sys, argparse
from io import BytesIO
from pathlib import Path
import numpy as np
from PIL import Image
from rosbags.highlevel import AnyReader

DEPTH_TOPIC = '/tb3_1/camera/aligned_depth_to_color/image_raw'
INFO_TOPIC = '/tb3_1/camera/aligned_depth_to_color/camera_info'
COLOR_TOPIC = '/tb3_1/camera/color/image_raw/compressed'


def quat_to_R(x, y, z, w):
    n = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def tf_mat(t):
    M = np.eye(4)
    M[:3, :3] = quat_to_R(t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w)
    M[:3, 3] = [t.translation.x, t.translation.y, t.translation.z]
    return M


def lookup(static_edges, dyn, target, source, ts):
    """target_from_source 4x4 at time ts. dyn: list of (ts, parent, child, M)."""
    edges = dict(static_edges)
    best = {}  # (p,c) -> (dt, M) nearest in time
    for dts, p, c, M in dyn:
        dt = abs(dts - ts)
        if (p, c) not in best or dt < best[(p, c)][0]:
            best[(p, c)] = (dt, M)
    for (p, c), (_, M) in best.items():
        edges[(p, c)] = M
    graph = {}
    for (p, c), M in edges.items():
        graph.setdefault(p, []).append((c, M))
        graph.setdefault(c, []).append((p, np.linalg.inv(M)))
    # BFS from source up to target, accumulating target_from_source
    from collections import deque
    seen = {source: np.eye(4)}  # frame -> source_from_frame? we accumulate X_from_source
    dq = deque([source])
    acc = {source: np.eye(4)}  # acc[f] = f_from_source
    while dq:
        f = dq.popleft()
        if f == target:
            return acc[target]
        for nb, M in graph.get(f, []):  # M = f_from_nb
            if nb not in acc:
                acc[nb] = np.linalg.inv(M) @ acc[f]  # nb_from_source = nb_from_f @ f_from_source
                dq.append(nb)
    return acc.get(target)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bag', nargs='+', help='bag 디렉토리 1개 이상(같은 odom 세션이면 한 클라우드로 합쳐짐)')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--frames', type=int, default=1, help='누적할 depth 프레임 수 (0=전체)')
    ap.add_argument('--frame-step', type=int, default=1, help='프레임 솎기(긴 주행: 매 N번째만 — 15Hz 시간 다운샘플)')
    ap.add_argument('--zmin', type=float, default=0.15)
    ap.add_argument('--zmax', type=float, default=4.0)
    ap.add_argument('--stride', type=int, default=2, help='픽셀 샘플 간격(다운샘플)')
    ap.add_argument('--accumulate', action='store_true', help='tf로 target frame 누적(회전 캡처용)')
    ap.add_argument('--target-frame', default='tb3_1/odom')
    ap.add_argument('--source-frame', default='camera_color_optical_frame')
    args = ap.parse_args()

    depths, colors, K = [], [], None
    static_edges, dyn = {}, []
    with AnyReader([Path(b) for b in args.bag]) as reader:
        for conn, ts, raw in reader.messages():
            msg = reader.deserialize(raw, conn.msgtype)
            if conn.topic == INFO_TOPIC and K is None:
                k = np.array(msg.k).reshape(3, 3)
                K = (float(k[0, 0]), float(k[1, 1]), float(k[0, 2]), float(k[1, 2]))  # fx fy cx cy
            elif conn.topic == DEPTH_TOPIC:
                d = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width)
                depths.append((ts, d))
            elif conn.topic == COLOR_TOPIC:
                img = np.asarray(Image.open(BytesIO(bytes(msg.data))).convert('RGB'))
                colors.append((ts, img))
            elif conn.topic == '/tf_static':
                for tr in msg.transforms:
                    static_edges[(tr.header.frame_id, tr.child_frame_id)] = tf_mat(tr.transform)
            elif conn.topic == '/tf':
                for tr in msg.transforms:
                    dyn.append((ts, tr.header.frame_id, tr.child_frame_id, tf_mat(tr.transform)))

    if K is None or not depths or not colors:
        print(f'ERR: K={K} depths={len(depths)} colors={len(colors)}')
        sys.exit(1)
    fx, fy, cx, cy = K
    print(f'intrinsics fx={fx:.1f} fy={fy:.1f} cx={cx:.1f} cy={cy:.1f} | depth={len(depths)} color={len(colors)}')

    if args.accumulate:
        print(f'accumulate: static_edges={len(static_edges)} dyn_tf={len(dyn)} target={args.target_frame}')

    color_ts = np.array([c[0] for c in colors])
    use = depths if args.frames == 0 else depths[:args.frames]
    use = sorted(use, key=lambda x: x[0])[::args.frame_step]   # 시간순 정렬 후 솎기(다중 bag 합칠 때 순서 보장)
    print(f'depth frames: total={len(depths)} used={len(use)} (frame_step={args.frame_step})')
    blocks, skipped = [], 0
    for ts, d in use:
        rgb = colors[int(np.argmin(np.abs(color_ts - ts)))][1]
        h, w = d.shape
        vs, us = np.mgrid[0:h:args.stride, 0:w:args.stride]
        z = d[vs, us].astype(np.float32) * 0.001  # mm → m
        m = (z > args.zmin) & (z < args.zmax)
        zz, uu, vv = z[m], us[m], vs[m]
        xx = (uu - cx) * zz / fx
        yy = (vv - cy) * zz / fy
        cc = rgb[vv, uu] if rgb.shape[:2] == (h, w) else np.full((len(zz), 3), 200, np.uint8)
        if args.accumulate:
            M = lookup(static_edges, dyn, args.target_frame, args.source_frame, ts)
            if M is None:
                skipped += 1
                continue
            P = M @ np.column_stack([xx, yy, zz, np.ones(len(xx))]).T  # 4xN
            xx, yy, zz = P[0], P[1], P[2]
        blocks.append((xx, yy, zz, cc))
    if args.accumulate and skipped:
        print(f'WARN: {skipped} frames skipped (tf lookup 실패)')

    n = sum(len(b[0]) for b in blocks)
    print(f'points={n}')
    if n == 0:
        print('ERR: 0 valid points (depth 범위/정렬 확인)')
        sys.exit(1)

    dt = np.dtype([('x', '<f4'), ('y', '<f4'), ('z', '<f4'), ('r', 'u1'), ('g', 'u1'), ('b', 'u1')])
    arr = np.empty(n, dt)
    i = 0
    for xx, yy, zz, cc in blocks:
        j = i + len(xx)
        arr['x'][i:j], arr['y'][i:j], arr['z'][i:j] = xx, yy, zz
        arr['r'][i:j], arr['g'][i:j], arr['b'][i:j] = cc[:, 0], cc[:, 1], cc[:, 2]
        i = j

    hdr = ('ply\nformat binary_little_endian 1.0\n'
           f'element vertex {n}\n'
           'property float x\nproperty float y\nproperty float z\n'
           'property uchar red\nproperty uchar green\nproperty uchar blue\n'
           'end_header\n')
    with open(args.out, 'wb') as f:
        f.write(hdr.encode())
        arr.tofile(f)
    print(f'wrote {args.out}  ({n} pts)')


if __name__ == '__main__':
    main()
