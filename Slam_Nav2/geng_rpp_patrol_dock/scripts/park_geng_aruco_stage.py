#!/usr/bin/env python3
"""Move Gen.G to the ArUco waiting stage and face the marker (no reverse dock).

Uses NavigateToPose with a temporarily tighter xy tolerance, then in-place
yaw alignment to the saved stage heading. No open-loop XY creep — that was
overshooting and twisting the robot away from the marker.
"""

import math
import time
from pathlib import Path

import rclpy
import yaml
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, TwistStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

ROOT = Path(__file__).resolve().parents[1]
WAYPOINTS = ROOT / "config/waypoints.yaml"
_DEFAULT_STAGE = (0.2608, -0.1477, -1.525)
NAV_XY_TOL = 0.03
DEFAULT_XY_TOL = 0.05
YAW_TOL = 0.04


def load_aruco_stage() -> tuple[float, float, float]:
    data = yaml.safe_load(WAYPOINTS.read_text(encoding="utf-8")) or {}
    pose = (data.get("waiting") or {}).get("geng_aruco_stage")
    if not pose:
        return _DEFAULT_STAGE
    return float(pose["x"]), float(pose["y"]), float(pose["yaw"])


def angle_error(target: float, current: float) -> float:
    return math.atan2(math.sin(target - current), math.cos(target - current))


class Parking(Node):
    def __init__(self, stage: tuple[float, float, float]) -> None:
        super().__init__("geng_aruco_stage")
        self.stage = stage
        self.nav = ActionClient(self, NavigateToPose, "/navigate_to_pose")
        self.cmd = self.create_publisher(TwistStamped, "/cmd_vel_nav", 10)
        self.controller_params = AsyncParameterClient(self, "/controller_server")
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
        for _ in range(8):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.02)
            time.sleep(0.04)

    def set_xy_tolerance(self, value: float) -> None:
        if not self.controller_params.wait_for_services(timeout_sec=3.0):
            self.get_logger().warn("controller_server param service 없음 — tol 유지")
            return
        future = self.controller_params.set_parameters(
            [Parameter("goal_checker.xy_goal_tolerance", value=value)]
        )
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)

    def navigate_stage(self) -> bool:
        if not self.nav.wait_for_server(timeout_sec=10.0):
            return False
        x, y, yaw = self.stage
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

    def rotate(self, target: float, timeout=15.0) -> bool:
        """In-place yaw only — no linear.x (avoids sliding off stage)."""
        deadline = time.monotonic() + timeout
        last_log = 0.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)
            try:
                _, _, yaw = self.pose()
            except Exception:
                self.publish()
                time.sleep(0.05)
                continue
            error = angle_error(target, yaw)
            if abs(error) <= YAW_TOL:
                self.stop()
                return True
            # Slow near target to reduce scrub / AMCL jump.
            if abs(error) < 0.25:
                speed = 0.10
            elif abs(error) < 0.6:
                speed = 0.16
            else:
                speed = 0.22
            self.publish(angular=math.copysign(speed, error))
            now = time.monotonic()
            if now - last_log >= 1.0:
                self.get_logger().info(
                    f"yaw={math.degrees(yaw):.1f} "
                    f"remaining={math.degrees(error):.1f}deg"
                )
                last_log = now
            time.sleep(0.04)
        self.stop()
        return False


def main() -> int:
    stage = load_aruco_stage()
    rclpy.init()
    node = Parking(stage)
    try:
        node.get_logger().info(
            f"1/2 Gen.G ArUco 대기장소로 이동 "
            f"(x={stage[0]:.4f}, y={stage[1]:.4f}, yaw={stage[2]:.4f})"
        )
        node.set_xy_tolerance(NAV_XY_TOL)
        if not node.navigate_stage():
            node.get_logger().error("Gen.G ArUco 대기장소 이동 실패")
            return 1

        x, y, yaw = node.pose()
        dist = math.hypot(stage[0] - x, stage[1] - y)
        node.get_logger().info(
            f"Nav2 도착: x={x:.3f}, y={y:.3f}, yaw={yaw:.3f} "
            f"(xy_err={dist*100:.1f}cm)"
        )

        node.get_logger().info("2/2 Gen.G ArUco 대기 각도 정렬 (제자리 회전)")
        if not node.rotate(stage[2]):
            node.get_logger().error("Gen.G ArUco 대기 각도 정렬 실패")
            return 1
        x, y, yaw = node.pose()
        dist = math.hypot(stage[0] - x, stage[1] - y)
        yaw_err = math.degrees(angle_error(stage[2], yaw))
        node.get_logger().info(
            f"대기 완료: x={x:.3f}, y={y:.3f}, yaw={yaw:.3f} "
            f"(xy_err={dist*100:.1f}cm, yaw_err={yaw_err:+.1f}deg)"
        )
        if dist > 0.06:
            node.get_logger().warn(
                "XY가 목표에서 6cm 이상 벗어남 — Pose Estimate / 로컬라이제이션 확인"
            )
        return 0
    finally:
        node.set_xy_tolerance(DEFAULT_XY_TOL)
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
