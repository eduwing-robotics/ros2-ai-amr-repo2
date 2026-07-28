#!/usr/bin/env python3
"""Publish synthetic test frames to /camera/color/image_raw for YOLO demo."""

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class TestCameraPublisher(Node):
    def __init__(self) -> None:
        super().__init__('test_camera_publisher')
        self.pub = self.create_publisher(Image, '/camera/color/image_raw', 10)
        self.bridge = CvBridge()
        self.frame_id = 0
        self.create_timer(0.1, self.publish_frame)
        self.get_logger().info('Publishing test frames to /camera/color/image_raw')

    def publish_frame(self) -> None:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (40, 40, 40)
        cv2.rectangle(img, (80, 80), (560, 400), (80, 80, 200), 2)
        cv2.putText(
            img,
            f'Museum Patrol YOLO Test  frame={self.frame_id}',
            (90, 130),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img,
            'Waiting for person/fire detections...',
            (90, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        self.frame_id += 1
        msg = self.bridge.cv2_to_imgmsg(img, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_color_optical_frame'
        self.pub.publish(msg)


def main() -> None:
    rclpy.init()
    node = TestCameraPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
