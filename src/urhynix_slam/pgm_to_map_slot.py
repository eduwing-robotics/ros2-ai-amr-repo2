#!/usr/bin/env python3
# pgm_to_map_slot.py — ROS map_saver 산출(.pgm+.yaml)을 Unity ControlRoom 맵 슬롯(.png+.json)으로 변환.
# 슬롯은 StreamingAssets/Maps/<id>.png + <id>.json(MapConfigData). 맵을 언제든 추가/교체할 때 한 줄로 사용.
# 사용: python3 scripts/pgm_to_map_slot.py <src.pgm> <src.yaml> <slotId> [displayName] [--no-pretty]
import sys, re, os
from pathlib import Path
from PIL import Image
from make_pretty_map_slot import create_pretty_slot, write_unity_meta

ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = ROOT / "client/UNITY/Assets/StreamingAssets/Maps"

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
        print("사용: pgm_to_map_slot.py <src.pgm> <src.yaml> <slotId> [displayName] [--no-pretty]"); sys.exit(1)
    auto_pretty = "--no-pretty" not in sys.argv[4:]
    args = [a for a in sys.argv[1:] if a != "--no-pretty"]
    pgm, yaml, slot = args[0], args[1], args[2]
    disp = args[3] if len(args) > 3 else slot
    txt = open(yaml).read()
    res = float(re.search(r"resolution:\s*([-\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    ox, oy = float(o.group(1)), float(o.group(2))
    w, h, pix = load_pgm(pgm)

    out_dir = str(MAP_DIR)
    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, slot + '.png')
    json_path = os.path.join(out_dir, slot + '.json')
    Image.frombytes('L', (w, h), pix).save(png_path)
    with open(json_path, 'w') as f:
        f.write('{\n')
        f.write('  "map": {\n')
        f.write(f'    "mapId": "{slot}",\n    "displayName": "{disp}",\n')
        f.write(f'    "originX": {ox},\n    "originY": {oy},\n    "resolution": {res},\n')
        f.write(f'    "widthPx": {w},\n    "heightPx": {h},\n    "displayRotationDeg": 0\n')
        f.write('  },\n  "waypoints": [],\n  "protectedTargets": []\n}\n')
    write_unity_meta(Path(png_path))
    write_unity_meta(Path(json_path))
    print(f"슬롯 '{slot}' 생성: {w}x{h} origin({ox},{oy}) res {res} → {out_dir}")
    # ponytail: watcher 없이 변환 진입점에서 후처리한다. 다른 경로로 파일을 직접 복사하면 이 자동 생성은 안 돈다.
    if auto_pretty:
        print(create_pretty_slot(slot, f"{slot}_pretty", f"{disp} 관제 천장뷰"))

if __name__ == '__main__':
    main()
