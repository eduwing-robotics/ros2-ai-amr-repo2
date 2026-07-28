#!/usr/bin/env python3
"""Move T1 to its regular or ArUco docking waiting pose."""

import argparse
import math
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, TwistStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener


WAITING = (-0.066952, -0.054960, 1.633087)
ARUCO_STAGE = (-0.054, -0.038, -1.511)
DOCK = (-0.039853, -0.385125, 1.617123)


def angle_error(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


class Parking(Node):
    def __init__(self, waiting) -> None:
        super().__init__("t1_waiting_and_docking")
        self.waiting = waiting
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.cmd = self.create_publisher(TwistStamped, "/cmd_vel_nav", 10)
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

    def pose(self):
        tf = self.buffer.lookup_transform(
            "map", "base_footprint", Time(), timeout=Duration(seconds=0.3)
        )
        q = tf.transform.rotation
        yaw = math.atan2(2.0 * q.w * q.z, 1.0 - 2.0 * q.z * q.z)
        return tf.transform.translation.x, tf.transform.translation.y, yaw

    def publish(self, linear=0.0, angular=0.0) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_footprint"
        msg.twist.linear.x = linear
        msg.twist.angular.z = angular
        self.cmd.publish(msg)

    def stop(self) -> None:
        for _ in range(6):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.02)
            time.sleep(0.05)

    def navigate_waiting(self) -> bool:
        if not self.nav.wait_for_server(timeout_sec=10.0):
            return False
        x, y, yaw = self.waiting
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        goal = NavigateToPose.Goal()
        goal.pose = pose
        future = self.nav.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        handle = future.result()
        if handle is None or not handle.accepted:
            return False
        result = handle.get_result_async()
        rclpy.spin_until_future_complete(self, result)
        return result.result().status == GoalStatus.STATUS_SUCCEEDED

    def rotate(self, target: float, timeout=12.0) -> bool:
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            _, _, yaw = self.pose()
            error = angle_error(target, yaw)
            if abs(error) <= 0.05:
                self.stop()
                return True
            speed = max(0.30, min(0.65, abs(error) * 1.2))
            self.publish(angular=math.copysign(speed, error))
            time.sleep(0.05)
        self.stop()
        return False

    def drive_x(self, target_x: float, target_y: float, timeout=8.0) -> bool:
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            x, y, _ = self.pose()
            if target_x - x <= 0.015:
                self.stop()
                return True
            correction = max(-0.12, min(0.12, (target_y - y) * 2.0))
            self.publish(linear=0.04, angular=correction)
            time.sleep(0.05)
        self.stop()
        return False

    def reverse_y(self, target_x: float, target_y: float, timeout=9.0) -> bool:
        deadline = time.monotonic() + timeout
        last_y = None
        last_progress = time.monotonic()
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            x, y, _ = self.pose()
            if y - target_y <= 0.025:
                self.stop()
                return True
            if last_y is None or y < last_y - 0.003:
                last_y = y
                last_progress = time.monotonic()
            elif time.monotonic() - last_progress > 2.5:
                self.stop()
                return y - target_y <= 0.06
            correction = max(-0.10, min(0.10, (target_x - x) * 1.5))
            self.publish(linear=-0.04, angular=correction)
            time.sleep(0.05)
        self.stop()
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aruco-stage", action="store_true")
    args = parser.parse_args()

    rclpy.init()
    node = Parking(ARUCO_STAGE if args.aruco_stage else WAITING)
    try:
        node.get_logger().info("1/2 T1 대기장소로 이동")
        if not node.navigate_waiting():
            node.get_logger().error("T1 대기장소 이동 실패")
            return 1
        node.get_logger().info("2/2 T1 대기 각도 정렬")
        if not node.rotate(node.waiting[2]):
            node.get_logger().error("T1 대기 각도 정렬 실패")
            return 1
        x, y, yaw = node.pose()
        node.get_logger().warn("자동 후진 도킹은 후방 장애물 감지가 없어 비활성화됨")
        node.get_logger().info(f"대기 완료: x={x:.3f}, y={y:.3f}, yaw={yaw:.3f}")
        return 0
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
