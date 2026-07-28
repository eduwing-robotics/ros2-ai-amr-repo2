#!/usr/bin/env python3
"""카메라 토픽 1프레임 받아 메타데이터 출력 + /tmp/camera_debug.jpg 저장."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from museum_patrol_nodes.image_utils import imgmsg_to_bgr
from rclpy.node import Node
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image

# RealSense2 camera default publisher QoS (see ros2 topic info -v)
_REALSENSE_QOS = QoSProfile(
    depth=10,
    reliability=QoSReliabilityPolicy.RELIABLE,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
)


class OneShot(Node):
    def __init__(self, topic: str) -> None:
        super().__init__('camera_debug')
        self._got = False
        self._topic = topic
        self._start = time.monotonic()
        if topic.endswith('/compressed'):
            self.create_subscription(CompressedImage, topic, self._cb_compressed, _REALSENSE_QOS)
            self.create_subscription(CompressedImage, topic, self._cb_compressed, qos_profile_sensor_data)
        else:
            self.create_subscription(Image, topic, self._cb_image, _REALSENSE_QOS)
            self.create_subscription(Image, topic, self._cb_image, qos_profile_sensor_data)
            compressed = f'{topic}/compressed' if '/compressed' not in topic else topic
            if not topic.endswith('/compressed'):
                self.create_subscription(
                    CompressedImage, compressed, self._cb_compressed, _REALSENSE_QOS
                )
        self.create_timer(1.0, self._tick)

    def _tick(self) -> None:
        if self._got:
            return
        elapsed = time.monotonic() - self._start
        if elapsed < 3.0:
            return
        topics = [n for n, _ in self.get_topic_names_and_types() if 'camera' in n]
        self.get_logger().info(
            f'still waiting ({elapsed:.0f}s) — camera topics: {topics[:8] or "NONE"}'
        )

    def _save_bgr(self, bgr) -> None:
        out = Path('/tmp/camera_debug.jpg')
        cv2.imwrite(str(out), bgr)
        print(f'  saved    : {out}  shape={bgr.shape}')

    def _cb_image(self, msg: Image) -> None:
        if self._got:
            return
        self._got = True
        print('--- Image metadata ---')
        print(f'  encoding : {msg.encoding}')
        print(f'  size     : {msg.width} x {msg.height}')
        print(f'  step     : {msg.step}  (expected rgb8/bgr8: {msg.width * 3})')
        print(f'  data len : {len(msg.data)}  (expected >= {msg.height * msg.step})')
        try:
            bgr = imgmsg_to_bgr(msg)
            self._save_bgr(bgr)
        except Exception as exc:
            print(f'  decode ERROR: {exc}')

    def _cb_compressed(self, msg: CompressedImage) -> None:
        if self._got:
            return
        self._got = True
        print('--- CompressedImage metadata ---')
        print(f'  format   : {msg.format}')
        print(f'  data len : {len(msg.data)}')
        try:
            arr = np.frombuffer(msg.data, dtype=np.uint8)
            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if bgr is None:
                raise RuntimeError('cv2.imdecode returned None')
            self._save_bgr(bgr)
        except Exception as exc:
            print(f'  decode ERROR: {exc}')


def main() -> int:
    topic = sys.argv[1] if len(sys.argv) > 1 else '/tb3_1/camera/color/image_raw/compressed'
    domain = os.environ.get('ROS_DOMAIN_ID', '(not set)')
    print(f'ROS_DOMAIN_ID={domain}')
    if domain == '(not set)':
        print('[ERROR] export ROS_DOMAIN_ID=210 후 다시 실행하세요.')
        print('        source scripts/setup_ros_env.sh')
        return 1

    timeout = float(os.environ.get('CAMERA_DEBUG_TIMEOUT', '30'))
    rclpy.init()
    node = OneShot(topic)
    print(f'Waiting one frame from {topic} (timeout {timeout:.0f}s) ...')
    deadline = time.monotonic() + timeout
    try:
        while rclpy.ok() and time.monotonic() < deadline and not node._got:
            rclpy.spin_once(node, timeout_sec=0.5)
    except KeyboardInterrupt:
        pass

    ok = node._got
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()

    if not ok:
        print('')
        print(f'[FAIL] {timeout:.0f}초 안에 프레임을 못 받았습니다.')
        print('  1) 로봇에서 카메라 실행:')
        print('       export ROS_DOMAIN_ID=210 LAPTOP_IP=<노트북IP>')
        print('       ./scripts/phase_a_top_camera_check.sh robot-bg')
        print('  2) 노트북 DDS:')
        print('       export ROS_DOMAIN_ID=210 LAPTOP_IP=$(hostname -I|awk "{print \\$1}")')
        print('       source scripts/setup_ros_env.sh')
        print('  3) compressed 토픽으로 재시도:')
        print('       python3 scripts/debug_camera_frame.py /tb3_1/camera/color/image_raw/compressed')
        return 1

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
