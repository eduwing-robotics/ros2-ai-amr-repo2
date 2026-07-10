#!/usr/bin/env python3
# patrol_test_seq.py — tb3_1 순회지점1 실주행 테스트 시퀀스(로봇에서 실행).
# 1) 목표 방향으로 제자리 회전(Spin) 2) 1초 정지 3) NavigateToPose로 이동
# 4) 도착 후 360도 Spin 5) 정지(Spin 종료 시 속도 0).
# ⚠️ 2026-07-01 미해결: /tb3_1/amcl_pose 첫 구독 콜백에서 터무니없는 값(x=-2931,y=14806) 수신,
#   회전각 오계산→Spin 즉시 ABORTED. 유력 원인: amcl_pose 퍼블리셔 QoS가 TRANSIENT_LOCAL인데
#   이 스크립트 구독자는 기본(VOLATILE) → durability mismatch. 재실행 전 QoS를
#   TRANSIENT_LOCAL로 맞추거나 /tb3_1/pose(robot_pose_publisher, 일반 QoS) 사용 검토.
# 좌표는 Unity 저장 순찰경로에서 가져옴: ~/Library/Application Support/DefaultCompany/turtlebot/patrols/arena_shared.json
import math
import time
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy, QoSHistoryPolicy
from nav2_msgs.action import Spin, NavigateToPose
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped

TARGET_X = 0.12104667723178864
TARGET_Y = -1.2106822729110718


def quaternion_from_euler(_r, _p, yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def yaw_from_quat(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class PatrolTest(Node):
    def __init__(self):
        super().__init__("patrol_test_seq")
        self.spin_client = ActionClient(self, Spin, "/tb3_1/spin")
        self.nav_client = ActionClient(self, NavigateToPose, "/tb3_1/navigate_to_pose")
        self.cur = None
        # amcl_pose 퍼블리셔가 TRANSIENT_LOCAL이라 구독자도 맞춰야 최신 retained 샘플을 정상 수신.
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

    def do_spin(self, target_yaw_rel, label):
        self.get_logger().info(f"[{label}] Spin target_yaw_rel={target_yaw_rel:.3f} rad")
        if not self.spin_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("spin server not available"); return False
        goal = Spin.Goal()
        goal.target_yaw = target_yaw_rel
        fut = self.spin_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error(f"[{label}] spin goal rejected"); return False
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=40.0)
        res = rfut.result()
        ok = res is not None and res.status == 4  # STATUS_SUCCEEDED
        self.get_logger().info(f"[{label}] spin done status={res.status if res else 'NONE'}")
        return ok

    def do_navigate(self, x, y, yaw):
        self.get_logger().info(f"[nav] NavigateToPose -> ({x:.3f},{y:.3f}) yaw={yaw:.3f}")
        if not self.nav_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("nav server not available"); return False
        ps = PoseStamped()
        ps.header.frame_id = "map"
        ps.header.stamp = self.get_clock().now().to_msg()
        ps.pose.position.x = x
        ps.pose.position.y = y
        qx, qy, qz, qw = quaternion_from_euler(0, 0, yaw)
        ps.pose.orientation.x = qx; ps.pose.orientation.y = qy
        ps.pose.orientation.z = qz; ps.pose.orientation.w = qw
        goal = NavigateToPose.Goal()
        goal.pose = ps
        fut = self.nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error("nav goal rejected"); return False
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=90.0)
        res = rfut.result()
        ok = res is not None and res.status == 4
        self.get_logger().info(f"[nav] navigate done status={res.status if res else 'NONE'}")
        return ok


def main():
    rclpy.init()
    node = PatrolTest()
    pose = node.wait_pose()
    if pose is None:
        node.get_logger().error("no amcl_pose received"); sys.exit(1)
    x0, y0 = pose.position.x, pose.position.y
    yaw0 = yaw_from_quat(pose.orientation)
    # 안전장치: 방(arena_shared, 약 1.9x1.9m) 범위를 크게 벗어나면 QoS/오염 데이터로 간주하고 중단.
    if abs(x0) > 5.0 or abs(y0) > 5.0:
        node.get_logger().error(f"비정상 pose 감지(x={x0:.1f},y={y0:.1f}) — 중단, QoS/토픽 재확인 필요")
        sys.exit(9)
    dx, dy = TARGET_X - x0, TARGET_Y - y0
    theta_face = math.atan2(dy, dx)
    rel = theta_face - yaw0
    rel = math.atan2(math.sin(rel), math.cos(rel))  # normalize to [-pi,pi]
    node.get_logger().info(f"cur=({x0:.3f},{y0:.3f},{math.degrees(yaw0):.1f}deg) "
                            f"target=({TARGET_X:.3f},{TARGET_Y:.3f}) "
                            f"face={math.degrees(theta_face):.1f}deg rel={math.degrees(rel):.1f}deg "
                            f"dist={math.hypot(dx,dy):.3f}m")

    if not node.do_spin(rel, "face-target"):
        node.get_logger().error("face-target spin failed, abort"); sys.exit(2)
    node.get_logger().info("1초 정지...")
    time.sleep(1.0)
    if not node.do_navigate(TARGET_X, TARGET_Y, theta_face):
        node.get_logger().error("navigate failed, abort before 360 spin"); sys.exit(3)
    if not node.do_spin(2 * math.pi, "arrival-360"):
        node.get_logger().error("arrival spin failed"); sys.exit(4)
    node.get_logger().info("완료: 도착+360도 회전+정지")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
