#!/usr/bin/env python3
"""Save the robot's current map pose as a named fixed waypoint."""

import argparse
import math
import os
import sys
import tempfile
import time
from pathlib import Path

import rclpy
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener
import yaml


PATROL_NAMES = {f"patrol_{index}" for index in range(1, 9)}
WAITING_NAMES = {"waiting_geng"}
DOCK_NAMES = {"waiting_geng_dock"}
ARUCO_STAGE_NAMES = {"waiting_geng_aruco_stage"}
VALID_NAMES = PATROL_NAMES | WAITING_NAMES | DOCK_NAMES | ARUCO_STAGE_NAMES


def yaw_from_quaternion(z: float, w: float) -> float:
    return math.atan2(2.0 * w * z, 1.0 - 2.0 * z * z)


class PoseReader(Node):
    def __init__(self) -> None:
        super().__init__("save_current_waypoint")
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

    def read(self, timeout_seconds: float):
        deadline = time.monotonic() + timeout_seconds
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            try:
                return self.buffer.lookup_transform(
                    "map",
                    "base_footprint",
                    Time(),
                    timeout=Duration(seconds=0.2),
                )
            except TransformException:
                continue
        raise RuntimeError("map -> base_footprint TF를 읽지 못했습니다")


def save_pose(path: Path, name: str, transform) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("frame_id", "map")
    data.setdefault("map", "museum_map.yaml")
    data.setdefault("patrol", {})
    data.setdefault("waiting", {})

    translation = transform.transform.translation
    rotation = transform.transform.rotation
    pose = {
        "x": round(float(translation.x), 4),
        "y": round(float(translation.y), 4),
        "yaw": round(yaw_from_quaternion(rotation.z, rotation.w), 4),
    }

    if name in PATROL_NAMES:
        data["patrol"][name] = pose
    else:
        data["waiting"][name.removeprefix("waiting_")] = pose

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)
    return pose


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", choices=sorted(VALID_NAMES))
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config/waypoints.yaml",
    )
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    rclpy.init()
    node = PoseReader()
    try:
        transform = node.read(args.timeout)
        pose = save_pose(args.file, args.name, transform)
    except (RuntimeError, OSError, yaml.YAMLError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()

    print(
        f"[OK] {args.name}: x={pose['x']:.4f}, y={pose['y']:.4f}, "
        f"yaw={pose['yaw']:.4f} rad"
    )
    print(f"     file={args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
