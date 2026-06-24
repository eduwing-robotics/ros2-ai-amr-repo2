#!/usr/bin/env python3
# patrol_waypoints_bridge.py — Unity ControlRoom이 발행한 /<robot>/patrol_waypoints(PoseArray)를 받아
# Nav2 FollowWaypoints 액션으로 실행하는 로봇측 브리지. ROS-TCP는 액션 미지원이라 이 노드가 다리 역할.
# 로봇/Nav2 PC(같은 저장맵+AMCL, 도메인 210)에서 실행:
#   python3 patrol_waypoints_bridge.py --robot tb3_1
import argparse
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator


class PatrolBridge(Node):
    def __init__(self, robot):
        super().__init__('patrol_waypoints_bridge')
        self.nav = BasicNavigator()
        topic = f'/{robot}/patrol_waypoints'
        self.sub = self.create_subscription(PoseArray, topic, self.on_route, 10)
        self.get_logger().info(f'구독: {topic} — Unity 순찰 시작 대기')

    def on_route(self, msg: PoseArray):
        if not msg.poses:
            self.get_logger().warn('빈 PoseArray 수신 — 무시'); return
        goals = []
        for p in msg.poses:
            ps = PoseStamped()
            ps.header.frame_id = msg.header.frame_id or 'map'
            ps.header.stamp = self.get_clock().now().to_msg()
            ps.pose = p
            goals.append(ps)
        self.get_logger().info(f'{len(goals)}개 웨이포인트 수신 → FollowWaypoints 시작')
        self.nav.followWaypoints(goals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--robot', default='tb3_1')
    a = ap.parse_args()
    rclpy.init()
    node = PatrolBridge(a.robot)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
