#!/usr/bin/env python3
# patrol_waypoints_bridge.py — Unity ControlRoom이 발행한 /<robot>/goal_pose(PoseStamped)와
# /<robot>/patrol_waypoints(PoseArray)를 받아 Nav2 goToPose/FollowWaypoints로 실행하는 로봇측 브리지.
# ROS-TCP는 액션 미지원이라 이 노드가 다리 역할.
# 로봇/Nav2 PC(같은 저장맵+AMCL, 도메인 210)에서 실행:
#   python3 patrol_waypoints_bridge.py --robot tb3_1
import argparse
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


class PatrolBridge(Node):
    def __init__(self, robot):
        super().__init__('patrol_waypoints_bridge')
        self.nav = BasicNavigator()
        self.nav.initial_pose_received = True  # tf로 localize 확인 후 실행하는 현장 표준 우회.
        self.nav_ready = False
        self.busy = False

        goal_topic = f'/{robot}/goal_pose'
        route_topic = f'/{robot}/patrol_waypoints'
        self.goal_sub = self.create_subscription(PoseStamped, goal_topic, self.on_goal, 10)
        self.route_sub = self.create_subscription(PoseArray, route_topic, self.on_route, 10)
        self.get_logger().info(f'구독: {goal_topic}, {route_topic} — Unity 명령 대기')

    def ensure_nav_ready(self):
        if self.nav_ready:
            return True
        self.get_logger().info('Nav2 활성 대기...')
        try:
            self.nav.waitUntilNav2Active()
        except Exception as e:
            self.get_logger().error(f'Nav2 활성 실패: {e}')
            return False
        self.nav_ready = True
        self.get_logger().info('Nav2 활성 확인')
        return True

    def wait_result(self, label):
        while not self.nav.isTaskComplete():
            fb = self.nav.getFeedback()
            if fb and hasattr(fb, 'current_waypoint'):
                self.get_logger().info(f'{label}: 현재 웨이포인트 #{fb.current_waypoint + 1}', throttle_duration_sec=2.0)
            time.sleep(0.1)
        result = self.nav.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info(f'{label}: 성공')
        elif result == TaskResult.CANCELED:
            self.get_logger().warn(f'{label}: 취소됨')
        else:
            self.get_logger().error(f'{label}: 실패 result={result}')

    def on_goal(self, msg: PoseStamped):
        if self.busy:
            self.get_logger().warn('Nav2 작업 중 goal_pose 수신 — 무시')
            return
        if not self.ensure_nav_ready():
            return
        self.busy = True
        try:
            msg.header.stamp = self.get_clock().now().to_msg()
            if not msg.header.frame_id:
                msg.header.frame_id = 'map'
            self.get_logger().info(
                f'goal_pose 수신 → goToPose 시작 ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})')
            self.nav.goToPose(msg)
            self.wait_result('goToPose')
        finally:
            self.busy = False

    def on_route(self, msg: PoseArray):
        if self.busy:
            self.get_logger().warn('Nav2 작업 중 순찰 경로 수신 — 무시')
            return
        if not msg.poses:
            self.get_logger().warn('빈 PoseArray 수신 — 무시')
            return
        if not self.ensure_nav_ready():
            return
        self.busy = True
        goals = []
        try:
            for p in msg.poses:
                ps = PoseStamped()
                ps.header.frame_id = msg.header.frame_id or 'map'
                ps.header.stamp = self.get_clock().now().to_msg()
                ps.pose = p
                goals.append(ps)
            self.get_logger().info(f'{len(goals)}개 웨이포인트 수신 → FollowWaypoints 시작')
            self.nav.followWaypoints(goals)
            self.wait_result('FollowWaypoints')
        finally:
            self.busy = False


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
