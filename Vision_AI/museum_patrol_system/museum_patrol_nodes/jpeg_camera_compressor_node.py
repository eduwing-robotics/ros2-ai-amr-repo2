"""Subscribe to raw camera Image and publish JPEG CompressedImage for Wi-Fi streaming."""

from __future__ import annotations

import threading
import time

import rclpy
from museum_patrol_nodes.image_utils import bgr_to_compressed_imgmsg, imgmsg_to_bgr
from museum_patrol_nodes.robot_topics import t1_color_compressed, t1_color_raw
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy
)
from sensor_msgs.msg import CompressedImage, Image

# Live video: drop stale frames instead of delaying TF/scan with retries.
COMPRESSED_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.VOLATILE,
)


class JpegCameraCompressorNode(Node):
    def __init__(self) -> None:
        super().__init__('jpeg_camera_compressor')

        self.declare_parameter('input_topic', t1_color_raw())
        self.declare_parameter('output_topic', t1_color_compressed())
        self.declare_parameter('jpeg_quality', 75)
        self.declare_parameter('max_publish_fps', 10.0)

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        self._jpeg_quality = int(
            self.get_parameter('jpeg_quality').get_parameter_value().integer_value
        )
        self._publish_period = 1.0 / max(
            self.get_parameter('max_publish_fps').get_parameter_value().double_value,
            1.0,
        )

        self._lock = threading.Lock()
        self._latest: tuple[object, object] | None = None
        self._stop = threading.Event()
        self._pub_count = 0
        self._byte_sum = 0
        self._last_log = time.monotonic()

        self._pub = self.create_publisher(CompressedImage, output_topic, COMPRESSED_QOS)
        # BEST_EFFORT depth=1: drop stale raw frames (do not backlog on Pi)
        self.create_subscription(Image, input_topic, self._raw_cb, COMPRESSED_QOS)
        threading.Thread(target=self._publish_loop, daemon=True).start()

        self.get_logger().info(
            f'JPEG bridge {input_topic} -> {output_topic} '
            f'(quality={self._jpeg_quality}, max_fps={1.0 / self._publish_period:.1f})'
        )

    def _raw_cb(self, msg: Image) -> None:
        with self._lock:
            self._latest = (msg, msg.header)

    def _publish_loop(self) -> None:
        while not self._stop.is_set():
            loop_start = time.monotonic()
            with self._lock:
                packet = self._latest
            if packet is None:
                time.sleep(0.02)
                continue

            msg, header = packet
            try:
                frame = imgmsg_to_bgr(msg)
                out = bgr_to_compressed_imgmsg(frame, header, self._jpeg_quality)
            except Exception as exc:
                self.get_logger().warn(f'jpeg encode failed: {exc}', throttle_duration_sec=5.0)
                continue

            self._pub.publish(out)
            self._pub_count += 1
            self._byte_sum += len(out.data)

            now = time.monotonic()
            if now - self._last_log >= 5.0:
                kb = (self._byte_sum / max(self._pub_count, 1)) / 1024.0
                fps = self._pub_count / (now - self._last_log)
                self.get_logger().info(
                    f'JPEG stream ~{fps:.1f} fps, ~{kb:.0f} KB/frame, quality={self._jpeg_quality}'
                )
                self._pub_count = 0
                self._byte_sum = 0
                self._last_log = now

            elapsed = time.monotonic() - loop_start
            sleep_for = self._publish_period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def destroy_node(self) -> None:
        self._stop.set()
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = JpegCameraCompressorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        try:
            rclpy.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
