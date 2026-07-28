#!/usr/bin/env python3
"""OpenCV window viewer for ROS image topics (rqt 대안)."""

from __future__ import annotations

import argparse
import os
import threading

# OpenCV Qt 폰트 경고/창 안 뜸 완화
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.*=false')

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image

from museum_patrol_nodes.image_utils import imgmsg_to_bgr

_REALSENSE_QOS = QoSProfile(
    depth=10,
    reliability=QoSReliabilityPolicy.RELIABLE,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
)


class ImageViewer(Node):
    def __init__(self, topic: str, display_fps: float = 30.0) -> None:
        super().__init__('image_viewer')
        self._window = f'ROS: {topic}'
        self._count = 0
        self._window_ready = False
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        if topic.endswith('/compressed'):
            self.create_subscription(CompressedImage, topic, self._cb_compressed, _REALSENSE_QOS)
            self.create_subscription(CompressedImage, topic, self._cb_compressed, qos_profile_sensor_data)
        else:
            self.create_subscription(Image, topic, self._cb_image, _REALSENSE_QOS)
            self.create_subscription(Image, topic, self._cb_image, qos_profile_sensor_data)
        self.create_timer(1.0 / max(display_fps, 1.0), self._display_timer)
        self.get_logger().info(f'Waiting for images on {topic} ...')

    def _store_frame(self, frame) -> None:
        self._count += 1
        if self._count == 1:
            self.get_logger().info(f'First frame received ({frame.shape})')
        with self._frame_lock:
            self._latest_frame = frame

    def _cb_image(self, msg: Image) -> None:
        try:
            frame = imgmsg_to_bgr(msg)
        except Exception as exc:
            self.get_logger().warn(
                f'decode failed ({msg.encoding} {msg.width}x{msg.height} step={msg.step}): {exc}'
            )
            return
        self._store_frame(frame)

    def _cb_compressed(self, msg: CompressedImage) -> None:
        try:
            arr = np.frombuffer(msg.data, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError('cv2.imdecode returned None')
        except Exception as exc:
            self.get_logger().warn(f'compressed decode failed: {exc}')
            return
        self._store_frame(frame)

    def _display_timer(self) -> None:
        with self._frame_lock:
            frame = self._latest_frame
        if frame is None:
            return

        if not self._window_ready:
            try:
                cv2.namedWindow(self._window, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self._window, 960, 540)
            except cv2.error as exc:
                self.get_logger().error(f'OpenCV window failed: {exc}')
                raise SystemExit(1) from exc
            self._window_ready = True

        cv2.imshow(self._window, frame)
        cv2.waitKey(1)


def main() -> int:
    parser = argparse.ArgumentParser(description='View ROS Image topic with OpenCV')
    parser.add_argument('topic', nargs='?', default='/tb3_1/camera/color/image_raw/compressed')
    parser.add_argument('--fps', type=float, default=30.0, help='Display refresh rate')
    args = parser.parse_args()

    rclpy.init()
    node = ImageViewer(args.topic, display_fps=args.fps)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f'[ERROR] viewer stopped: {exc}', flush=True)
        return 1
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
