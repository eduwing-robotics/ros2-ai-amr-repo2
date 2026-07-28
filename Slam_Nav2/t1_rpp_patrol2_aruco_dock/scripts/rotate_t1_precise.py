#!/usr/bin/env python3
"""Perform a decelerating odom-referenced T1 in-place rotation."""

import math
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


def yaw(q) -> float:
    return math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z),
    )


def delta(current: float, previous: float) -> float:
    return math.atan2(
        math.sin(current - previous), math.cos(current - previous)
    )


class PreciseRotation(Node):
    def __init__(self) -> None:
        super().__init__("t1_precise_rotation")
        self.previous = None
        self.total = 0.0
        self.last_odom_at = None
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.create_subscription(Odometry, "/odom", self.on_odom, 20)

    def on_odom(self, msg: Odometry) -> None:
        current = yaw(msg.pose.pose.orientation)
        if self.previous is not None:
            self.total += delta(current, self.previous)
        self.previous = current
        self.last_odom_at = time.monotonic()

    def publish(self, angular: float = 0.0) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_footprint"
        msg.twist.angular.z = angular
        self.publisher.publish(msg)

    def stop(self) -> None:
        for _ in range(20):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.025)

    def run(self) -> bool:
        deadline = time.monotonic() + 5.0
        while rclpy.ok() and self.previous is None and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
        if self.previous is None:
            self.get_logger().error("odom 데이터 없음")
            return False

        self.total = 0.0
        target = math.radians(180.0)
        deadline = time.monotonic() + 30.0
        last_log = 0.0
        try:
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.02)
                now = time.monotonic()
                if self.last_odom_at is None or now - self.last_odom_at > 0.4:
                    self.get_logger().error("odom 지연으로 회전 중단")
                    return False
                remaining = target - self.total
                if remaining <= math.radians(0.6):
                    self.stop()
                    self.get_logger().info(
                        f"정밀 회전 완료: {math.degrees(self.total):.2f}deg"
                    )
                    return True
                if remaining <= math.radians(8.0):
                    speed = 0.06
                elif remaining <= math.radians(30.0):
                    speed = 0.10
                else:
                    speed = 0.18
                if now - last_log >= 1.0:
                    self.get_logger().info(
                        f"rotation={math.degrees(self.total):.1f}deg "
                        f"remaining={math.degrees(remaining):.1f}deg"
                    )
                    last_log = now
                self.publish(speed)
            self.get_logger().error("30초 회전 시간 초과")
            return False
        finally:
            self.stop()


def main() -> int:
    rclpy.init()
    node = PreciseRotation()
    try:
        return 0 if node.run() else 1
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
