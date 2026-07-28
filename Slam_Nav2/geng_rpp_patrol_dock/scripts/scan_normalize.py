#!/usr/bin/env python3
# LDS scan beam-count normalizer — /scan -> /scan_fixed (400 beams).
# Copied as standalone utility from robot_project (not a navigation orchestration script).
import os
import sys
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import LaserScan

IN = sys.argv[1] if len(sys.argv) > 1 else '/scan'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/scan_fixed'
N = int(sys.argv[3]) if len(sys.argv) > 3 else 400
MIN_RANGE = float(os.environ.get('SCAN_MIN_RANGE', '0.12'))
MAX_RANGE = float(os.environ.get('SCAN_MAX_RANGE', '2.3'))
FRAME_ID = os.environ.get('SCAN_FRAME_ID', '')
RESTAMP = os.environ.get('SCAN_RESTAMP', '0') == '1'


class Norm(Node):
    def __init__(self):
        super().__init__('scan_normalize')
        self.pub = self.create_publisher(LaserScan, OUT, qos_profile_sensor_data)
        self.create_subscription(LaserScan, IN, self.cb, qos_profile_sensor_data)
        self.get_logger().info(f'scan_normalize: {IN} -> {OUT}, N={N}')

    def cb(self, m):
        n_in = len(m.ranges)
        if n_in == 0:
            return
        new_inc = (m.angle_max - m.angle_min) / (N - 1)
        out = LaserScan()
        out.header = m.header
        if RESTAMP:
            out.header.stamp = self.get_clock().now().to_msg()
        if FRAME_ID:
            out.header.frame_id = FRAME_ID
        out.angle_min = m.angle_min
        out.angle_max = m.angle_max
        out.angle_increment = new_inc
        out.time_increment = m.time_increment
        out.scan_time = m.scan_time
        out.range_min = MIN_RANGE
        out.range_max = MAX_RANGE
        ranges = [0.0] * N
        inten = [0.0] * N
        has_int = len(m.intensities) == n_in
        for i in range(N):
            ang = out.angle_min + i * new_inc
            j = int(round((ang - m.angle_min) / m.angle_increment)) if m.angle_increment else i
            j = max(0, min(j, n_in - 1))
            r = m.ranges[j]
            if r < MIN_RANGE or r > MAX_RANGE or r != r:
                r = float('inf')
            ranges[i] = r
            if has_int:
                inten[i] = m.intensities[j]
        out.ranges = ranges
        out.intensities = inten if has_int else []
        self.pub.publish(out)


def main():
    rclpy.init()
    node = Norm()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
