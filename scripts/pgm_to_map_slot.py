#!/usr/bin/env python3
# pgm_to_map_slot.py — ROS map_saver 산출(.pgm+.yaml)을 Unity ControlRoom 맵 슬롯(.png+.json)으로 변환.
# 슬롯은 StreamingAssets/Maps/<id>.png + <id>.json(MapConfigData). 맵을 언제든 추가/교체할 때 한 줄로 사용.
# 사용: python3 scripts/pgm_to_map_slot.py <src.pgm> <src.yaml> <slotId> [displayName]
import sys, re, os
from PIL import Image

def load_pgm(path):
    with open(path, 'rb') as f: d = f.read()
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
    w, h, _ = vals; i += 1
    return w, h, d[i:i+w*h]

def main():
    if len(sys.argv) < 4:
        print("사용: pgm_to_map_slot.py <src.pgm> <src.yaml> <slotId> [displayName]"); sys.exit(1)
    pgm, yaml, slot = sys.argv[1], sys.argv[2], sys.argv[3]
    disp = sys.argv[4] if len(sys.argv) > 4 else slot
    txt = open(yaml).read()
    res = float(re.search(r"resolution:\s*([-\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    ox, oy = float(o.group(1)), float(o.group(2))
    w, h, pix = load_pgm(pgm)

    out_dir = os.path.join(os.path.dirname(__file__), '..',
                           'unity/ControlRoom/Assets/StreamingAssets/Maps')
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    Image.frombytes('L', (w, h), pix).save(os.path.join(out_dir, slot + '.png'))
    with open(os.path.join(out_dir, slot + '.json'), 'w') as f:
        f.write('{\n')
        f.write('  "map": {\n')
        f.write(f'    "mapId": "{slot}",\n    "displayName": "{disp}",\n')
        f.write(f'    "originX": {ox},\n    "originY": {oy},\n    "resolution": {res},\n')
        f.write(f'    "widthPx": {w},\n    "heightPx": {h},\n    "displayRotationDeg": 0\n')
        f.write('  },\n  "waypoints": [],\n  "protectedTargets": []\n}\n')
    print(f"슬롯 '{slot}' 생성: {w}x{h} origin({ox},{oy}) res {res} → {out_dir}")

if __name__ == '__main__':
    main()
