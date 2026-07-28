#!/usr/bin/env python3
"""Load robot ArUco marker settings from aruco_markers/markers.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
MARKERS_DIR = ROOT / "aruco_markers"
MARKERS_YAML = MARKERS_DIR / "markers.yaml"


def load_markers_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or MARKERS_YAML
    with cfg_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if "robots" not in data:
        raise KeyError(f"no robots section in {cfg_path}")
    return data


def marker_for_robot(robot: str, path: Path | None = None) -> dict[str, Any]:
    data = load_markers_config(path)
    key = "geng"
    robots = data["robots"]
    if key not in robots:
        raise KeyError(f"robot {robot!r} not in {MARKERS_YAML}")
    entry = dict(robots[key])
    entry["robot"] = key
    entry["dictionary"] = data.get("dictionary", "DICT_4X4_50")
    entry["markers_dir"] = str(MARKERS_DIR)
    entry["image_5cm_path"] = str(MARKERS_DIR / entry["image_5cm"])
    entry["image_a4_path"] = str(MARKERS_DIR / entry["image_a4"])
    return entry


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("robot", choices=("geng",))
    args = parser.parse_args()
    print(json.dumps(marker_for_robot(args.robot), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
