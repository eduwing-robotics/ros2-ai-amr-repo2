#!/usr/bin/env python3
"""Align to a rear wall and reverse dock using LaserScan only."""

import math
import time

import numpy as np
import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


TARGET_DISTANCE = 0.173
BRAKE_MARGIN = 0.012
MAX_SCAN_AGE = 0.30
ALIGN_TIMEOUT = 12.0
DOCK_TIMEOUT = 6.0


class RearWallDocker(Node):
    def __init__(self) -> None:
        super().__init__("geng_rear_wall_docker")
        self.scan = None
        self.scan_at = None
        self.publisher = self.create_publisher(TwistStamped, "/cmd_vel", 10)
        self.create_subscription(
            LaserScan, "/scan", self.on_scan, qos_profile_sensor_data
        )

    def on_scan(self, message: LaserScan) -> None:
        self.scan = message
        self.scan_at = time.monotonic()

    def publish(self, linear: float = 0.0, angular: float = 0.0) -> None:
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.linear.x = linear
        message.twist.angular.z = angular
        self.publisher.publish(message)

    def stop(self) -> None:
        for _ in range(20):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.03)

    def wall(self) -> tuple[float, float, int] | None:
        if self.scan is None:
            return None
        points = []
        for index, distance in enumerate(self.scan.ranges):
            angle = self.scan.angle_min + index * self.scan.angle_increment
            rear_error = abs(
                math.atan2(math.sin(angle - math.pi), math.cos(angle - math.pi))
            )
            if (
                rear_error <= math.radians(60.0)
                and math.isfinite(distance)
                and 0.10 < distance < 1.20
            ):
                points.append(
                    (distance * math.cos(angle), distance * math.sin(angle))
                )
        if len(points) < 20:
            return None

        cloud = np.asarray(points, dtype=np.float64)
        generator = np.random.default_rng(7)
        best = None
        for _ in range(600):
            first, second = generator.choice(len(cloud), 2, replace=False)
            tangent = cloud[second] - cloud[first]
            length = np.linalg.norm(tangent)
            if length < 0.05:
                continue
            tangent /= length
            normal = np.asarray([-tangent[1], tangent[0]])
            if normal @ np.asarray([-1.0, 0.0]) < 0.0:
                normal = -normal
            normal_angle = math.atan2(normal[1], normal[0])
            error = math.atan2(
                math.sin(normal_angle - math.pi),
                math.cos(normal_angle - math.pi),
            )
            if abs(error) > math.radians(45.0):
                continue
            distances = np.abs((cloud - cloud[first]) @ normal)
            inliers = distances < 0.012
            count = int(np.count_nonzero(inliers))
            if count < 15:
                continue
            line_points = cloud[inliers]
            span = float(np.ptp(line_points @ tangent))
            if span < 0.18:
                continue
            score = count + min(span, 1.0) * 10.0
            if best is None or score > best[0]:
                wall_distance = float(np.median(line_points @ normal))
                best = score, error, wall_distance, count
        if best is None:
            return None
        _, error, distance, count = best
        return error, distance, count

    def fresh_wall(self) -> tuple[float, float, int] | None:
        if (
            self.scan_at is None
            or time.monotonic() - self.scan_at > MAX_SCAN_AGE
        ):
            return None
        return self.wall()

    def align(self) -> bool:
        deadline = time.monotonic() + ALIGN_TIMEOUT
        stable = 0
        last_log = 0.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.03)
            wall = self.fresh_wall()
            if wall is None:
                stable = 0
                self.publish()
                continue
            error, distance, count = wall
            now = time.monotonic()
            if now - last_log > 0.25:
                self.get_logger().info(
                    f"rear wall angle={math.degrees(error):+.2f}deg "
                    f"distance={distance:.3f}m points={count}"
                )
                last_log = now
            if abs(error) <= math.radians(1.5):
                stable += 1
                self.publish()
                if stable >= 8:
                    self.get_logger().info("후방 벽 각도 정렬 완료")
                    return True
                continue
            stable = 0
            speed = min(0.20, max(0.07, abs(error) * 1.2))
            self.publish(angular=math.copysign(speed, error))
        self.get_logger().error("후방 벽 각도 정렬 실패")
        return False

    def dock(self) -> bool:
        deadline = time.monotonic() + DOCK_TIMEOUT
        last_log = 0.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.03)
            wall = self.fresh_wall()
            if wall is None:
                self.get_logger().error("후방 벽 검출 또는 scan 갱신 실패")
                return False
            error, distance, _ = wall
            if distance <= TARGET_DISTANCE + BRAKE_MARGIN:
                self.get_logger().info(f"도킹 거리 도달: rear={distance:.3f}m")
                return True
            if abs(error) > math.radians(12.0):
                self.get_logger().error(
                    f"후진 중 각도 오차 과다: {math.degrees(error):+.1f}deg"
                )
                return False
            now = time.monotonic()
            if now - last_log > 0.5:
                self.get_logger().info(
                    f"도킹 중 rear={distance:.3f}m "
                    f"angle={math.degrees(error):+.2f}deg"
                )
                last_log = now
            linear = -0.05 if distance > TARGET_DISTANCE + 0.10 else -0.035
            angular = max(-0.08, min(0.08, error * 1.1))
            self.publish(linear, angular)
        self.get_logger().error("후진 도킹 시간 초과")
        return False

    def run(self) -> bool:
        try:
            if not self.align():
                return False
            return self.dock()
        finally:
            self.stop()


def main() -> int:
    rclpy.init()
    node = RearWallDocker()
    try:
        return 0 if node.run() else 1
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
