#!/usr/bin/env python3
# make_pretty_map_slot.py — 기존 Unity 맵 슬롯을 발표용 고해상도 2D 천장뷰 슬롯으로 변환.
# 좌표 정합은 원본 슬롯 JSON의 origin/resolution/widthPx/heightPx를 그대로 복사해 유지한다.
import argparse
import json
import math
import os
import uuid
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
MAP_DIR = ROOT / "UNITY/Assets/StreamingAssets/Maps"


def load_slot(slot_id):
    png = MAP_DIR / f"{slot_id}.png"
    meta_path = MAP_DIR / f"{slot_id}.json"
    if not png.exists() or not meta_path.exists():
        raise SystemExit(f"슬롯 파일 없음: {png} / {meta_path}")
    with meta_path.open(encoding="utf-8") as f:
        meta = json.load(f)
    return Image.open(png).convert("L"), meta


def mask_from_luma(src, predicate):
    return Image.new("L", src.size, 0).point(lambda _: 0) if False else src.point(
        lambda v: 255 if predicate(v) else 0
    )


def paste_color(base, color, mask):
    layer = Image.new("RGBA", base.size, color)
    base.alpha_composite(Image.composite(layer, Image.new("RGBA", base.size, (0, 0, 0, 0)), mask))


def draw_grid(draw, width, height, scale, resolution):
    if resolution <= 0:
        return
    meter_px = max(1, int(round((1.0 / resolution) * scale)))
    half_px = max(1, meter_px // 2)

    minor = (110, 142, 168, 34)
    major = (99, 128, 158, 70)
    for x in range(0, width + 1, half_px):
        draw.line([(x, 0), (x, height)], fill=minor, width=1)
    for y in range(0, height + 1, half_px):
        draw.line([(0, y), (width, y)], fill=minor, width=1)
    for x in range(0, width + 1, meter_px):
        draw.line([(x, 0), (x, height)], fill=major, width=1)
    for y in range(0, height + 1, meter_px):
        draw.line([(0, y), (width, y)], fill=major, width=1)


def draw_hatch(draw, width, height, step):
    color = (55, 65, 81, 42)
    for x in range(-height, width, step):
        draw.line([(x, height), (x + height, 0)], fill=color, width=1)


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except TypeError:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)


def make_pretty(src, meta, long_edge):
    w, h = src.size
    if w <= 0 or h <= 0:
        raise SystemExit("잘못된 원본 이미지 크기")

    scale = long_edge / max(w, h)
    out_w = max(1, int(round(w * scale)))
    out_h = max(1, int(round(h * scale)))

    # ROS map_saver PGM convention: 0=occupied, 205=unknown, 254=free.
    occupied = mask_from_luma(src, lambda v: v <= 80)
    free = mask_from_luma(src, lambda v: v >= 230)
    unknown = ImageChops.invert(ImageChops.lighter(occupied, free))

    up_nearest = Image.Resampling.NEAREST
    occupied_hi = occupied.resize((out_w, out_h), up_nearest)
    free_hi = free.resize((out_w, out_h), up_nearest)
    unknown_hi = unknown.resize((out_w, out_h), up_nearest)

    canvas = Image.new("RGBA", (out_w, out_h), (15, 23, 42, 255))

    paste_color(canvas, (224, 232, 241, 255), free_hi)
    paste_color(canvas, (25, 34, 49, 255), unknown_hi)
    draw_hatch(ImageDraw.Draw(canvas, "RGBA"), out_w, out_h, max(10, int(scale * 0.75)))

    draw = ImageDraw.Draw(canvas, "RGBA")
    resolution = float(meta.get("map", {}).get("resolution", 0.05))
    draw_grid(draw, out_w, out_h, scale, resolution)

    # Wall styling: source-cell dilation gives SLAM dots enough visual weight without moving coordinates.
    wall_soft = occupied.filter(ImageFilter.MaxFilter(5)).resize((out_w, out_h), up_nearest)
    wall_hard = occupied.filter(ImageFilter.MaxFilter(3)).resize((out_w, out_h), up_nearest)
    wall_shadow = wall_soft.filter(ImageFilter.GaussianBlur(max(2, int(scale * 0.25))))

    paste_color(canvas, (30, 41, 59, 180), wall_shadow)
    paste_color(canvas, (12, 20, 33, 255), wall_hard)

    # Subtle bevel/highlight so the ceiling view reads less like a raw occupancy grid.
    edge = wall_hard.filter(ImageFilter.FIND_EDGES)
    paste_color(canvas, (125, 211, 252, 80), edge.filter(ImageFilter.GaussianBlur(0.5)))

    # Map extent and small scale chip. These are visual aids; coordinates still come from JSON.
    pad = max(8, int(scale * 0.35))
    draw.rectangle((pad, pad, out_w - pad - 1, out_h - pad - 1),
                   outline=(148, 163, 184, 95), width=max(1, int(scale * 0.08)))

    chip_w = min(out_w - pad * 2, max(160, int(out_w * 0.26)))
    chip_h = max(34, int(scale * 1.55))
    chip_x = pad * 2
    chip_y = max(pad * 2, out_h - chip_h - pad * 2)
    rounded_rect(draw, (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
                 radius=max(4, int(scale * 0.2)), fill=(15, 23, 42, 190),
                 outline=(148, 163, 184, 80), width=1)
    line_y = chip_y + chip_h // 2
    line_x0 = chip_x + max(18, int(scale * 0.8))
    line_len = max(50, int(round((1.0 / resolution) * scale)))
    line_x1 = min(chip_x + chip_w - max(18, int(scale * 0.8)), line_x0 + line_len)
    draw.line((line_x0, line_y, line_x1, line_y), fill=(226, 232, 240, 220), width=max(2, int(scale * 0.12)))
    draw.line((line_x0, line_y - 5, line_x0, line_y + 5), fill=(226, 232, 240, 220), width=1)
    draw.line((line_x1, line_y - 5, line_x1, line_y + 5), fill=(226, 232, 240, 220), width=1)

    return canvas


def write_meta(src_meta, dst_slot, display_name):
    out = json.loads(json.dumps(src_meta, ensure_ascii=False))
    out.setdefault("map", {})
    out["map"]["mapId"] = dst_slot
    out["map"]["displayName"] = display_name
    out.setdefault("waypoints", [])
    out.setdefault("protectedTargets", [])
    return out


def write_unity_meta(path):
    meta = path.with_suffix(path.suffix + ".meta")
    if meta.exists():
        return
    meta.write_text(
        "fileFormatVersion: 2\n"
        f"guid: {uuid.uuid4().hex}\n"
        "DefaultImporter:\n"
        "  externalObjects: {}\n"
        "  userData: \n"
        "  assetBundleName: \n"
        "  assetBundleVariant: \n",
        encoding="utf-8",
    )


def create_pretty_slot(source_slot, dest_slot=None, display_name="", long_edge=1024):
    dst_slot = dest_slot or f"{source_slot}_pretty"
    src, src_meta = load_slot(source_slot)
    display = display_name or f"{src_meta.get('map', {}).get('displayName', source_slot)} 관제 천장뷰"

    pretty = make_pretty(src, src_meta, max(256, long_edge))
    out_png = MAP_DIR / f"{dst_slot}.png"
    out_json = MAP_DIR / f"{dst_slot}.json"

    pretty.save(out_png)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(write_meta(src_meta, dst_slot, display), f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_unity_meta(out_png)
    write_unity_meta(out_json)

    m = src_meta["map"]
    return (
        f"{dst_slot}: tex={pretty.width}x{pretty.height}, "
        f"map={m['widthPx']}x{m['heightPx']} @ {m['resolution']}m, "
        f"origin=({m['originX']},{m['originY']})"
    )


def main():
    ap = argparse.ArgumentParser(description="Create a high-res pretty ControlRoom map slot from an existing slot.")
    ap.add_argument("source_slot", help="Existing slot id, e.g. arena_v4")
    ap.add_argument("dest_slot", nargs="?", help="Output slot id (default: <source>_pretty)")
    ap.add_argument("--display-name", default="", help="Display name stored in JSON")
    ap.add_argument("--long-edge", type=int, default=1024, help="Output image long edge in pixels")
    args = ap.parse_args()

    print(create_pretty_slot(args.source_slot, args.dest_slot, args.display_name, args.long_edge))


if __name__ == "__main__":
    main()
