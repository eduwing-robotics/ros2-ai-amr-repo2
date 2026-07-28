#!/usr/bin/env python3
"""Rotate in place using map->base_footprint yaw (not odom).

Supports relative --degrees or absolute --absolute-yaw (radians).
Uses a slow approach near the target and brakes if AMCL lag causes overshoot.
"""

from __future__ import annotations

import argparse
import math
import time

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def yaw_from_q(q) -> float:
    return math.atan2(2.0 * q.w * q.z, 1.0 - 2.0 * q.z * q.z)


def ang_err(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


class MapYawRotate(Node):
    def __init__(self, cmd_topic: str) -> None:
        super().__init__("map_yaw_rotate")
        self.buf = Buffer()
        self.listener = TransformListener(self.buf, self)
        self.pub = self.create_publisher(TwistStamped, cmd_topic, 10)

    def pose_yaw(self) -> float:
        tf = self.buf.lookup_transform(
            "map", "base_footprint", Time(), timeout=Duration(seconds=0.3)
        )
        return yaw_from_q(tf.transform.rotation)

    def send(self, angular: float = 0.0) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_footprint"
        msg.twist.angular.z = float(angular)
        self.pub.publish(msg)

    def stop(self) -> None:
        for _ in range(20):
            self.send(0.0)
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.02)

    def wait_yaw(self, timeout: float) -> float:
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            try:
                return self.pose_yaw()
            except TransformException:
                continue
        raise RuntimeError("map -> base_footprint TF 없음 (Pose Estimate 필요)")

    def speed_for_error(self, err: float) -> float:
        """Conservative profile — Gen.G overshoots if AMCL lags at high ω."""
        ae = abs(err)
        if ae < math.radians(8):
            return 0.05
        if ae < math.radians(15):
            return 0.08
        if ae < math.radians(30):
            return 0.12
        if ae < math.radians(60):
            return 0.16
        return 0.20

    def run(
        self,
        degrees: float | None,
        absolute_yaw: float | None,
        timeout: float,
        tol_deg: float,
    ) -> bool:
        yaw0 = self.wait_yaw(5.0)
        if absolute_yaw is not None:
            target = absolute_yaw
            label = f"absolute {math.degrees(target):.1f}deg"
        else:
            degrees = 180.0 if degrees is None else degrees
            target = yaw0 + math.radians(degrees)
            label = f"relative {degrees:.1f}deg"

        self.get_logger().info(
            f"map-yaw rotate {label}: "
            f"start={math.degrees(yaw0):.1f} target={math.degrees(target):.1f}"
        )
        deadline = time.monotonic() + timeout
        last_log = 0.0
        prev_err: float | None = None
        settled = 0
        try:
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.02)
                try:
                    yaw = self.pose_yaw()
                except TransformException:
                    self.send(0.0)
                    continue
                err = ang_err(target, yaw)

                if abs(err) <= math.radians(tol_deg):
                    settled += 1
                    self.send(0.0)
                    # Require a few consecutive samples so inertia/AMCL lag settle.
                    if settled >= 4:
                        self.stop()
                        turned = math.degrees(ang_err(yaw, yaw0))
                        self.get_logger().info(
                            f"완료 yaw={math.degrees(yaw):.1f}deg "
                            f"err={math.degrees(err):.1f} "
                            f"turned={turned:.1f}deg"
                        )
                        return True
                    time.sleep(0.03)
                    continue
                settled = 0

                # If we crossed the target (sign flip with shrinking |err| then grow),
                # brake the other way briefly — typical AMCL-lag overshoot.
                if prev_err is not None and prev_err * err < 0.0 and abs(prev_err) < math.radians(25):
                    self.get_logger().warn(
                        f"과회전 감지 → 역방향 브레이크(절반) "
                        f"(was {math.degrees(prev_err):+.1f} now {math.degrees(err):+.1f})"
                    )
                    # Half the previous reverse impulse (was 0.08 x 6 pulses).
                    brake = math.copysign(0.08, err)
                    for _ in range(3):
                        self.send(brake)
                        rclpy.spin_once(self, timeout_sec=0.01)
                        time.sleep(0.03)
                    self.stop()
                    prev_err = err
                    continue

                speed = self.speed_for_error(err)
                self.send(math.copysign(speed, err))
                prev_err = err
                now = time.monotonic()
                if now - last_log >= 1.0:
                    self.get_logger().info(
                        f"yaw={math.degrees(yaw):.1f} remaining={math.degrees(err):.1f}"
                    )
                    last_log = now
                time.sleep(0.03)
            self.get_logger().error("map-yaw 회전 시간 초과")
            return False
        finally:
            self.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--degrees", type=float, default=None)
    parser.add_argument(
        "--absolute-yaw",
        type=float,
        default=None,
        help="Target map yaw in radians (preferred for docking).",
    )
    parser.add_argument("--timeout", type=float, default=40.0)
    parser.add_argument("--tol-deg", type=float, default=2.5)
    parser.add_argument("--cmd-topic", default="/cmd_vel_nav")
    args = parser.parse_args()

    if args.absolute_yaw is None and args.degrees is None:
        args.degrees = 180.0

    rclpy.init()
    node = MapYawRotate(args.cmd_topic)
    try:
        ok = node.run(args.degrees, args.absolute_yaw, args.timeout, args.tol_deg)
        return 0 if ok else 1
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
