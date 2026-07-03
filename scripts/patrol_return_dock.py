#!/usr/bin/env python3
# patrol_return_dock.py — 티원을 현재 위치에서 충전독으로 복귀시킨다.
#   ComputePathToPose(현재→충전독)를 한 번만 계산해 FollowPath로 그 경로를 고정 추종한다
#   (NavigateToPose처럼 주행 중 재계획하지 않음 — 같은 정적 맵/플래너로 나가는 길의 역방향을
#   그대로 따라가는 "왔던 길 복귀" 요청 반영. [[urhynix-t1-nav2-patrol-drive]]).
import math
import sys
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy, QoSHistoryPolicy
from nav2_msgs.action import ComputePathToPose, FollowPath
from geometry_msgs.msg import PoseWithCovarianceStamped

DOCK_X = 0.05
DOCK_Y = 0.028
DOCK_YAW = 0.0


def quaternion_from_euler(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


class ReturnToDock(Node):
    def __init__(self):
        super().__init__("patrol_return_dock")
        self.compute_client = ActionClient(self, ComputePathToPose, "/tb3_1/compute_path_to_pose")
        self.follow_client = ActionClient(self, FollowPath, "/tb3_1/follow_path")
        self.cur = None
        qos = QoSProfile(depth=10,
                          reliability=QoSReliabilityPolicy.RELIABLE,
                          durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                          history=QoSHistoryPolicy.KEEP_LAST)
        self.create_subscription(PoseWithCovarianceStamped, "/tb3_1/amcl_pose", self._on_pose, qos)

    def _on_pose(self, msg):
        self.cur = msg.pose.pose

    def wait_pose(self, timeout=10.0):
        t0 = time.time()
        while self.cur is None and time.time() - t0 < timeout:
            rclpy.spin_once(self, timeout_sec=0.5)
        return self.cur

    def compute_path(self, x, y, yaw):
        if not self.compute_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("compute_path_to_pose server not available"); return None
        goal = ComputePathToPose.Goal()
        goal.goal.header.frame_id = "map"
        goal.goal.header.stamp = self.get_clock().now().to_msg()
        goal.goal.pose.position.x = x
        goal.goal.pose.position.y = y
        qx, qy, qz, qw = quaternion_from_euler(yaw)
        goal.goal.pose.orientation.x = qx; goal.goal.pose.orientation.y = qy
        goal.goal.pose.orientation.z = qz; goal.goal.pose.orientation.w = qw
        goal.use_start = False  # 현재 로봇 위치를 시작점으로 사용
        fut = self.compute_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error("compute_path goal rejected"); return None
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=20.0)
        res = rfut.result()
        if res is None or res.result.error_code != 0:
            self.get_logger().error(f"compute_path failed error_code={res.result.error_code if res else 'NONE'}")
            return None
        return res.result.path

    def follow_path(self, path):
        if not self.follow_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("follow_path server not available"); return False
        goal = FollowPath.Goal()
        goal.path = path
        fut = self.follow_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error("follow_path goal rejected"); return False
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=90.0)
        res = rfut.result()
        ok = res is not None and res.status == 4  # STATUS_SUCCEEDED
        self.get_logger().info(f"follow_path done status={res.status if res else 'NONE'}")
        return ok


def main():
    rclpy.init()
    node = ReturnToDock()
    pose = node.wait_pose()
    if pose is None:
        node.get_logger().error("no amcl_pose received"); sys.exit(1)
    x0, y0 = pose.position.x, pose.position.y
    if abs(x0) > 5.0 or abs(y0) > 5.0:
        node.get_logger().error(f"비정상 pose 감지(x={x0:.1f},y={y0:.1f}) — 중단")
        sys.exit(9)
    node.get_logger().info(f"cur=({x0:.3f},{y0:.3f}) -> dock=({DOCK_X:.3f},{DOCK_Y:.3f})")

    path = node.compute_path(DOCK_X, DOCK_Y, DOCK_YAW)
    if path is None or len(path.poses) == 0:
        node.get_logger().error("경로 계산 실패, 중단"); sys.exit(2)
    node.get_logger().info(f"경로 {len(path.poses)}포인트 계산됨, 추종 시작")

    if not node.follow_path(path):
        node.get_logger().error("follow_path 실패"); sys.exit(3)
    node.get_logger().info("완료: 충전독 복귀")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
