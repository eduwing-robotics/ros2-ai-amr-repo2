#!/usr/bin/env python3
# patrol_multi_waypoint.py — 저장된 순회경로(arena_shared.json) 7개 웨이포인트를 순서대로
#   회전(Spin)→1초정지→NavigateToPose→도착 1초정지→다음 웨이포인트 반복.
#   마지막 웨이포인트 이후 시작 위치(최초 amcl_pose)로 복귀해 시작 방향 그대로 정차("주차").
#   [[urhynix-t1-nav2-patrol-drive]] 확장 — QoS/사전check 안전가드는 patrol_test_seq.py와 동일 패턴.
import math
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav2_msgs.action import NavigateToPose, Spin
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import (QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile,
                        QoSReliabilityPolicy)

# 충전독 고정좌표(AMCL 시딩값과 동일) — 복귀(주차) 목표. 2026-07-03 맵 교체(arena_shared2)로 재확정
# — 절차는 [[urhynix-t1-amcl-saved-map]] "맵 교체 시 초기포즈 재확보" 참고.
DOCK_X, DOCK_Y, DOCK_YAW = 0.038, 1.405, 0.293

# ⚠️ 2026-07-03 맵 교체로 원점이 달라져 아래 좌표는 옛 arena_shared(구) 기준 — 새 맵에서 재계산 전까지 무효.
# 재계산: scripts/patrol_safe_clearance.py 또는 Unity에서 새로 클릭.
WAYPOINTS = [  # arena_shared(구), 벽 안전여유(0.25m)로 재계산됨 — scripts/patrol_safe_clearance.py
    (0.045999999999999985, -1.1190000000000002),
    (1.286, -1.219),
    (1.286, -0.359),
    (0.9059999999999999, -0.359),
    (0.8535234332084656, -1.0220140218734741),
    (0.316373735666275, -0.8755187392234802),
    (0.36600000000000005, -0.119),
]


def quaternion_from_yaw(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def yaw_of(pose):
    q = pose.orientation
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class MultiWaypointPatrol(Node):
    def __init__(self):
        super().__init__("patrol_multi_waypoint")
        self.nav_client = ActionClient(self, NavigateToPose, "/tb3_1/navigate_to_pose")
        self.spin_client = ActionClient(self, Spin, "/tb3_1/spin")
        self.cur = None
        qos = QoSProfile(depth=10,
                          reliability=QoSReliabilityPolicy.RELIABLE,
                          durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
                          history=QoSHistoryPolicy.KEEP_LAST)
        self.create_subscription(PoseWithCovarianceStamped, "/tb3_1/amcl_pose", self._on_pose, qos)

    def _on_pose(self, msg):
        self.cur = msg.pose.pose

    def wait_pose(self, timeout=10.0):
        # self.cur를 비우지 않는다 — 로봇이 이미 목표 근처(허용오차 이내)라 AMCL이 새 메시지를
        # 안 낼 수도 있음(update_min_d/a 미달). 그런 경우도 "최근값 유효"로 취급해야 정상.
        t0 = time.time()
        while self.cur is None and time.time() - t0 < timeout:
            rclpy.spin_once(self, timeout_sec=0.5)
        rclpy.spin_once(self, timeout_sec=0.2)  # 대기 중 들어온 갱신이 있으면 마저 반영
        return self.cur

    def sane(self, pose):
        return pose is not None and abs(pose.position.x) <= 5.0 and abs(pose.position.y) <= 5.0

    def do_spin(self, target_yaw_rel):
        if not self.spin_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("spin server not available"); return False
        goal = Spin.Goal()
        goal.target_yaw = target_yaw_rel
        self.get_logger().info(f"[spin] target_yaw_rel={target_yaw_rel:.3f} rad")
        fut = self.spin_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error("spin goal rejected"); return False
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=30.0)
        res = rfut.result()
        ok = res is not None and res.status == GoalStatus.STATUS_SUCCEEDED
        self.get_logger().info(f"[spin] done status={res.status if res else 'NONE'}")
        return ok

    def do_navigate(self, x, y, yaw):
        if not self.nav_client.wait_for_server(timeout_sec=8.0):
            self.get_logger().error("navigate server not available"); return False
        goal = NavigateToPose.Goal()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        qx, qy, qz, qw = quaternion_from_yaw(yaw)
        goal.pose.pose.orientation.x = qx
        goal.pose.pose.orientation.y = qy
        goal.pose.pose.orientation.z = qz
        goal.pose.pose.orientation.w = qw
        self.get_logger().info(f"[nav] NavigateToPose -> ({x:.3f},{y:.3f}) yaw={yaw:.3f}")
        fut = self.nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=8.0)
        gh = fut.result()
        if gh is None or not gh.accepted:
            self.get_logger().error("navigate goal rejected"); return False
        rfut = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rfut, timeout_sec=120.0)
        res = rfut.result()
        ok = res is not None and res.status == GoalStatus.STATUS_SUCCEEDED
        self.get_logger().info(f"[nav] done status={res.status if res else 'NONE'}")
        return ok

    def go_to(self, tx, ty, final_yaw=None):
        pose = self.cur
        cx, cy = pose.position.x, pose.position.y
        cyaw = yaw_of(pose)
        bearing = math.atan2(ty - cy, tx - cx)
        rel = math.atan2(math.sin(bearing - cyaw), math.cos(bearing - cyaw))
        dist = math.hypot(tx - cx, ty - cy)
        self.get_logger().info(
            f"cur=({cx:.3f},{cy:.3f},{math.degrees(cyaw):.1f}deg) target=({tx:.3f},{ty:.3f}) dist={dist:.3f}m")
        if not self.do_spin(rel):
            return False
        time.sleep(1.0)
        if not self.do_navigate(tx, ty, final_yaw if final_yaw is not None else bearing):
            return False
        time.sleep(1.0)
        return self.sane(self.wait_pose(timeout=5.0))


def main():
    rclpy.init()
    node = MultiWaypointPatrol()
    start = node.wait_pose()
    if not node.sane(start):
        node.get_logger().error(f"비정상 시작 pose — 중단 ({start})")
        return
    node.get_logger().info(f"현재위치: ({start.position.x:.3f},{start.position.y:.3f}) / 복귀목표(충전독): ({DOCK_X:.3f},{DOCK_Y:.3f})")

    legs = [(tx, ty, None) for tx, ty in WAYPOINTS] + [(DOCK_X, DOCK_Y, DOCK_YAW)]  # 마지막=충전독 복귀(주차)
    for i, (tx, ty, fyaw) in enumerate(legs, 1):
        label = f"웨이포인트 {i}/{len(WAYPOINTS)}" if i <= len(WAYPOINTS) else "복귀(주차)"
        node.get_logger().info(f"=== {label} -> ({tx:.3f},{ty:.3f}) ===")
        if not node.sane(node.cur):
            node.get_logger().error("현재 pose 비정상 — 중단")
            return
        if not node.go_to(tx, ty, fyaw):
            node.get_logger().error(f"{label} 실패 — 중단")
            return
    node.get_logger().info("완료: 전 웨이포인트 순회 + 출발위치 복귀 주차")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
