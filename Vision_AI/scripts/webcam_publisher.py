#!/usr/bin/env python3
"""Publish live webcam frames to /camera/color/image_raw."""

import sys

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class WebcamPublisher(Node):
    def __init__(self, device_index: int = 0) -> None:
        super().__init__('webcam_publisher')
        self.declare_parameter('device_index', device_index)
        self.declare_parameter('topic', '/camera/color/image_raw')
        self.declare_parameter('fps', 30.0)

        device_index = int(self.get_parameter('device_index').value)
        topic = str(self.get_parameter('topic').value)
        fps = float(self.get_parameter('fps').value)

        self.cap = cv2.VideoCapture(device_index, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(device_index)
        if not self.cap.isOpened():
            self.get_logger().error(f'Cannot open webcam device index {device_index}')
            sys.exit(1)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        # 드라이버 버퍼에 쌓인 오래된 프레임 버리기 (지연·끊김 완화)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.bridge = CvBridge()
        self.pub = self.create_publisher(Image, topic, qos_profile_sensor_data)
        period = 1.0 / max(fps, 1.0)
        self.create_timer(period, self.publish_frame)
        self.get_logger().info(
            f'Publishing webcam device={device_index} to {topic} at {fps:.1f} fps'
        )

    def publish_frame(self) -> None:
        # 최신 프레임만 사용 (버퍼에 남은 구 프레임 스킵)
        ok, frame = False, None
        for _ in range(3):
            ok, frame = self.cap.read()
            if not ok:
                break

        if not ok or frame is None:
            self.get_logger().warn('Webcam read failed')
            return

        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'camera_color_optical_frame'
        self.pub.publish(msg)

    def destroy_node(self) -> None:
        self.cap.release()
        super().destroy_node()


def main() -> None:
    rclpy.init()
    node = WebcamPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
