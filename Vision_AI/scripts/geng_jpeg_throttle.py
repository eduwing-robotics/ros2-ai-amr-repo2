#!/usr/bin/env python3
"""On-robot: throttle + JPEG-compress /tb3_2/camera/image_raw for smooth Wi-Fi viewing."""

from __future__ import annotations

import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image

SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class JpegThrottle(Node):
    def __init__(self, max_fps: float, jpeg_quality: int) -> None:
        super().__init__("geng_jpeg_throttle")
        self.min_interval = 1.0 / max_fps
        self.jpeg_quality = jpeg_quality
        self.last_pub = 0.0
        # ArUco dock uses image_raw/compressed; viewer can use either.
        self.pub = self.create_publisher(
            CompressedImage,
            "/tb3_2/camera/image_raw/compressed",
            SENSOR_QOS,
        )
        self.pub_view = self.create_publisher(
            CompressedImage,
            "/tb3_2/camera/image_view/compressed",
            SENSOR_QOS,
        )
        self.create_subscription(
            Image, "/tb3_2/camera/image_raw", self.on_image, SENSOR_QOS
        )
        self.get_logger().info(
            f"raw -> /tb3_2/camera/image_raw/compressed (+ image_view) "
            f"max_fps={max_fps} quality={jpeg_quality}"
        )

    def on_image(self, msg: Image) -> None:
        now = time.monotonic()
        if now - self.last_pub < self.min_interval:
            return
        h, w = msg.height, msg.width
        step = msg.step
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        try:
            if msg.encoding == "rgb8":
                # Respect row stride (camera_ros may pad rows).
                row_bytes = max(step, w * 3)
                flat = arr.reshape(h, row_bytes)[:, : w * 3]
                img = cv2.cvtColor(flat.reshape(h, w, 3), cv2.COLOR_RGB2BGR)
            elif msg.encoding == "bgr8":
                row_bytes = max(step, w * 3)
                flat = arr.reshape(h, row_bytes)[:, : w * 3]
                img = flat.reshape(h, w, 3).copy()
            elif msg.encoding in ("yuv422_yuy2", "yuyv", "YUYV"):
                row_bytes = max(step, w * 2)
                flat = arr.reshape(h, row_bytes)[:, : w * 2]
                img = cv2.cvtColor(flat.reshape(h, w, 2), cv2.COLOR_YUV2BGR_YUY2)
            else:
                self.get_logger().warn(f"unsupported encoding {msg.encoding}")
                return
        except ValueError as exc:
            self.get_logger().warn(
                f"reshape failed: {exc} enc={msg.encoding} "
                f"{w}x{h} step={step} nbytes={len(msg.data)}"
            )
            return

        ok, buf = cv2.imencode(
            ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            return
        out = CompressedImage()
        out.header = msg.header
        out.format = "jpeg"
        out.data = buf.tobytes()
        self.pub.publish(out)
        self.pub_view.publish(out)
        self.last_pub = now


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-fps", type=float, default=15.0,
                        help="Publish cap (BEST_EFFORT, depth=1)")
    parser.add_argument("--jpeg-quality", type=int, default=45,
                        help="OpenCV JPEG quality 0–100 (40–50 for Wi-Fi live view)")
    args = parser.parse_args()

    rclpy.init()
    node = JpegThrottle(args.max_fps, args.jpeg_quality)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
