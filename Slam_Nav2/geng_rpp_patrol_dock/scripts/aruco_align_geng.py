#!/usr/bin/env python3
"""Align Gen.G with normalized image_error yaw control: normalized image_error yaw control.

Uses ROS JPEG (/tb3_2/camera/...) instead of H.264 UDP, but the same control law:
  image_error = (marker_cx - width/2) / width
  cmd = -sign(image_error - target) * speed
Plus reverse-search if the marker is lost after being seen.
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from aruco_marker_config import marker_for_robot  # noqa: E402

VIDEO_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class GengImageErrorAligner(Node):
    def __init__(
        self,
        marker_id: int,
        image_topic: str,
        cmd_topic: str,
        target_image_error: float,
        tolerance: float,
        invert_yaw: bool,
    ) -> None:
        super().__init__("aruco_align_geng")
        self.marker_id = marker_id
        self.target_image_error = target_image_error
        self.tolerance = tolerance
        self.invert_yaw = invert_yaw
        self.last_image_at = None
        self.last_error = None
        self.aligned_frames = 0
        self.publisher = self.create_publisher(TwistStamped, cmd_topic, 10)

        if hasattr(cv2.aruco, "getPredefinedDictionary"):
            dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        else:
            dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
        if hasattr(cv2.aruco, "DetectorParameters_create"):
            parameters = cv2.aruco.DetectorParameters_create()
        else:
            parameters = cv2.aruco.DetectorParameters()
        self.detector = (
            cv2.aruco.ArucoDetector(dictionary, parameters)
            if hasattr(cv2.aruco, "ArucoDetector")
            else None
        )
        self.dictionary = dictionary
        self.parameters = parameters
        self.create_subscription(CompressedImage, image_topic, self.on_image, VIDEO_QOS)

    def on_image(self, message: CompressedImage) -> None:
        self.last_image_at = time.monotonic()
        image = cv2.imdecode(np.frombuffer(message.data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            self.last_error = None
            return
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(image)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(
                image, self.dictionary, parameters=self.parameters
            )
        self.last_error = None
        if ids is None:
            return
        height, width = image.shape[:2]
        for index, detected_id in enumerate(ids.flatten()):
            # Only accept the robot's docking ID (ignore false positives like ID 17).
            if int(detected_id) != self.marker_id:
                continue
            pts = corners[index][0]
            center_x = float(np.mean(pts[:, 0]))
            image_error = (center_x - width * 0.5) / width
            self.last_error = image_error - self.target_image_error
            if self.invert_yaw:
                self.last_error = -self.last_error
            return

    def publish(self, angular: float = 0.0) -> None:
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.angular.z = angular
        self.publisher.publish(message)

    def stop(self) -> None:
        for _ in range(12):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.03)

    def run(self, timeout: float = 90.0) -> bool:
        deadline = time.monotonic() + timeout
        last_log = 0.0
        ever_seen = False
        last_cmd_sign = 0.0
        recover_sign = 0.0
        recover_until = 0.0
        lost_since = None
        try:
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.03)
                now = time.monotonic()
                stale = self.last_image_at is None or now - self.last_image_at > 0.5
                seen = (not stale) and self.last_error is not None

                if not seen:
                    self.aligned_frames = 0
                    if ever_seen:
                        if lost_since is None:
                            lost_since = now
                            recover_sign = -last_cmd_sign if last_cmd_sign != 0.0 else 1.0
                            recover_until = now + 2.5
                            self.get_logger().warn(
                                f"ID {self.marker_id} 놓침 → 반대 방향 재탐색 "
                                f"(sign={recover_sign:+.0f})"
                            )
                        if now < recover_until:
                            self.publish(recover_sign * 0.05)
                        else:
                            phase = int((now - recover_until) / 2.0) % 2
                            sweep = recover_sign if phase == 0 else -recover_sign
                            self.publish(sweep * 0.045)
                    else:
                        phase = int(now / 2.5) % 2
                        self.publish((1.0 if phase == 0 else -1.0) * 0.05)
                        if now - last_log > 1.0:
                            self.get_logger().info(
                                f"Searching ArUco ID {self.marker_id} only "
                                "(other IDs ignored)"
                            )
                            last_log = now
                    continue

                if lost_since is not None:
                    self.get_logger().info(
                        f"ID {self.marker_id} 재검출 ({now - lost_since:.1f}s) → 미세 정렬"
                    )
                    lost_since = None
                ever_seen = True

                marker_error = self.last_error
                if now - last_log >= 0.25:
                    self.get_logger().info(
                        f"marker image error={marker_error:+.4f} "
                        f"(target={self.target_image_error:+.4f} tol={self.tolerance:.3f})"
                    )
                    last_log = now

                if abs(marker_error) <= self.tolerance:
                    self.aligned_frames += 1
                    self.publish()
                    last_cmd_sign = 0.0
                    if self.aligned_frames >= 5:
                        self.get_logger().info("ArUco 몸체 각도 정렬 완료 (image_error 방식)")
                        return True
                    continue

                self.aligned_frames = 0
                # Same gain band as 기존 H.264 aligner.
                speed = min(0.08, max(0.055, abs(marker_error) * 1.2))
                cmd = float(np.copysign(speed, -marker_error))
                last_cmd_sign = 1.0 if cmd > 0 else -1.0
                self.publish(cmd)

            self.get_logger().error("ArUco 각도 정렬 시간 초과")
            return False
        finally:
            self.stop()


def main() -> int:
    import argparse

    cfg = marker_for_robot("geng")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker-id", type=int, default=int(cfg["marker_id"]))
    parser.add_argument("--cmd-topic", default="/cmd_vel_nav")
    parser.add_argument("--image-topic", default=cfg["image_topic"])
    parser.add_argument(
        "--target-image-error",
        type=float,
        default=float(cfg.get("target_image_error", 0.0)),
        help="Normalized horizontal offset when body is correctly aligned (기존값 ~0.052).",
    )
    parser.add_argument("--tolerance", type=float, default=0.018)
    parser.add_argument("--invert-yaw", action="store_true")
    parser.add_argument("--timeout", type=float, default=90.0)
    # Keep unused bearing flag so old dock_geng_aruco.sh still works.
    parser.add_argument("--marker-size", type=float, default=float(cfg["marker_size_m"]))
    parser.add_argument("--camera-info-topic", default=cfg["camera_info_topic"])
    parser.add_argument("--target-bearing-deg", type=float, default=0.0)
    parser.add_argument("--max-speed", type=float, default=0.08)
    parser.add_argument("--min-speed", type=float, default=0.055)
    parser.add_argument("--tol-deg", type=float, default=2.0)
    args = parser.parse_args()

    print(
        f"[aruco_align_geng] Gen.G image_error | id={args.marker_id} "
        f"target_image_error={args.target_image_error:+.3f} tol={args.tolerance:.3f}"
    )

    rclpy.init()
    node = GengImageErrorAligner(
        args.marker_id,
        args.image_topic,
        args.cmd_topic,
        args.target_image_error,
        args.tolerance,
        args.invert_yaw,
    )
    try:
        return 0 if node.run(timeout=args.timeout) else 1
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
