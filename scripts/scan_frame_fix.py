#!/usr/bin/env python3
# scan_frame_fix.py — /<robot>/scan을 frame_id=<robot>/base_scan + stamp=현재ROS시각으로 교정해 /<robot>/scan_fixed로 republish.
# 왜(frame): coin_d4 드라이버가 scan frame_id를 'base_scan'으로 하드코딩 → ns tf(tb3_X/base_scan)와 불일치 → AMCL이 scan 폐기.
# 왜(stamp): coin_d4/OpenCR 디바이스 시계가 시스템보다 수초 미래(2026-06-29 측정: scan +4.6s, odom +3.7s, 서로 ~1s 차)
#     → AMCL message filter "timestamp earlier than all data in transform cache"로 scan 전부 폐기. stamp를 구독노드 now로
#     덮어 odom tf 캐시 범위 안으로 끌어와 정합. (정지/저속이면 위치오차 무시 가능, ceiling: 고속주행 시 stamp 오차.)
# 새 토픽(/scan_fixed)이라 원본 /scan 발행자에 0 영향(비침습). QoS는 sensor_data(best_effort)로 AMCL과 정합.
#   python3 scan_frame_fix.py --robot tb3_1
import argparse
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


class ScanFrameFix(Node):
    def __init__(self, robot):
        super().__init__('scan_frame_fix')
        self.frame = f'{robot}/base_scan'
        self.pub = self.create_publisher(LaserScan, f'/{robot}/scan_fixed', qos_profile_sensor_data)
        self.create_subscription(LaserScan, f'/{robot}/scan', self.cb, qos_profile_sensor_data)
        self.get_logger().info(f'/{robot}/scan → /{robot}/scan_fixed (frame_id={self.frame})')

    def cb(self, m):
        m.header.frame_id = self.frame
        m.header.stamp = self.get_clock().now().to_msg()
        self.pub.publish(m)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--robot', required=True, help='tb3_1(티원)/tb3_2(젠지)')
    g = a.parse_args()
    rclpy.init()
    n = ScanFrameFix(g.robot)
    try:
        rclpy.spin(n)
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
