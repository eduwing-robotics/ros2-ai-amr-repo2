#!/usr/bin/env python3
"""Send the fixed patrol route to Nav2's FollowWaypoints action."""

import argparse
import math
import sys
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
import yaml


class PatrolClient(Node):
    def __init__(self, poses: list[PoseStamped]) -> None:
        super().__init__("museum_patrol_client")
        self.poses = poses
        self.client = ActionClient(self, FollowWaypoints, "/follow_waypoints")
        self.controller_params = AsyncParameterClient(self, "/controller_server")
        self.exit_code = 1
        self.current_waypoint = None
        self.ignore_yaw_set = False

    def set_yaw_tolerance(self, tolerance: float, wait: bool = False) -> bool:
        if not self.controller_params.wait_for_services(timeout_sec=5.0):
            self.get_logger().error("controller_server parameter service를 찾지 못했습니다")
            return False
        future = self.controller_params.set_parameters(
            [Parameter("goal_checker.yaw_goal_tolerance", value=tolerance)]
        )
        if wait:
            rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)
            if not future.done():
                self.get_logger().error("yaw tolerance 설정 시간이 초과됐습니다")
                return False
        return True

    def start(self) -> None:
        self.get_logger().info("/follow_waypoints action server 대기 중")
        if not self.client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("/follow_waypoints action server를 찾지 못했습니다")
            rclpy.shutdown()
            return

        # Point 1 uses its saved heading; later points prioritize continuous motion.
        if not self.set_yaw_tolerance(0.25, wait=True):
            rclpy.shutdown()
            return

        goal = FollowWaypoints.Goal()
        goal.poses = self.poses
        future = self.client.send_goal_async(goal, feedback_callback=self.feedback)
        future.add_done_callback(self.goal_response)

    def feedback(self, message) -> None:
        current = int(message.feedback.current_waypoint) + 1
        if current != self.current_waypoint:
            self.current_waypoint = current
            self.get_logger().info(f"순찰 진행: {current}/{len(self.poses)}")
        if current >= 2 and not self.ignore_yaw_set:
            self.ignore_yaw_set = True
            self.set_yaw_tolerance(math.pi)
            self.get_logger().info("2번 이후 waypoint yaw 정렬 생략")

    def goal_response(self, future) -> None:
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("순찰 goal이 거부됐습니다")
            rclpy.shutdown()
            return
        self.get_logger().info("순찰 시작")
        result_future = handle.get_result_async()
        result_future.add_done_callback(self.finished)

    def finished(self, future) -> None:
        self.set_yaw_tolerance(0.25)
        wrapped = future.result()
        result = wrapped.result
        missed = [int(item.index) + 1 for item in result.missed_waypoints]
        if wrapped.status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn("순찰이 취소됐습니다")
        elif wrapped.status != GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().error(
                f"순찰 Action 실패: status={wrapped.status}, missed={missed}"
            )
        elif missed:
            self.get_logger().error(f"순찰 실패 waypoint: {missed}")
        else:
            self.get_logger().info(f"순찰 {len(self.poses)}개 waypoint 완료")
            self.exit_code = 0
        rclpy.shutdown()


def load_poses(path: Path) -> list[PoseStamped]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    frame_id = data.get("frame_id", "map")
    patrol = data.get("patrol", {})
    poses = []
    for index in range(1, 9):
        name = f"patrol_{index}"
        if name not in patrol:
            break
        item = patrol[name]
        yaw = float(item["yaw"])
        pose = PoseStamped()
        pose.header.frame_id = frame_id
        pose.pose.position.x = float(item["x"])
        pose.pose.position.y = float(item["y"])
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        poses.append(pose)
    return poses


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "config/waypoints.yaml",
    )
    args = parser.parse_args()

    try:
        poses = load_poses(args.file)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1

    rclpy.init()
    node = PatrolClient(poses)
    node.start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().warn("사용자가 순찰 실행을 중단했습니다")
    finally:
        exit_code = node.exit_code
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
