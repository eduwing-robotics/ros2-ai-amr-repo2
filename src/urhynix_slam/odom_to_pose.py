#!/usr/bin/env python3
# opencode: 2026-06-26 - non-namespace bringup(티원)용 --odom-topic 인자 추가.
#   /<robot>/odom(nav_msgs/Odometry)를 /<robot>/pose(PoseStamped, map프레임)로 릠이.
#   robot_pose_publisher.py(tf 기반)의 odom-only 대체: AMCL/SLAM 없이 마커 표시·이동만 검증할 때.
#   ponytail: odom-only 위치추정 — 절대위치는 부팅(odom 원점) 기준이고 장시간 주행 시 드리프트.
#   ceiling: 전역 보정 없음. upgrade 경로 = robot_pose_publisher.py + AMCL(arena_v4 공유맵).
# Coded with OpenCode; high-cost model review recommended.
# 두 로봇 마커가 겹치지 않게 --ox/--oy로 시작 오프셋을 다르게 준다(같은 map 프레임 내).
#   python3 odom_to_pose.py --robot tb3_1 --ox 0.4 --oy -0.7
import argparse
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseStamped


class OdomToPose(Node):
    def __init__(self, robot, odom_topic, ox, oy):
        super().__init__(f'odom_to_pose_{robot}')
        self.ox, self.oy = ox, oy
        self.pub = self.create_publisher(PoseStamped, f'/{robot}/pose', 10)
        self.create_subscription(Odometry, odom_topic, self.cb, 10)
        self.get_logger().info(f'{odom_topic} → /{robot}/pose (map, offset {ox},{oy})')

    def cb(self, m):
        p = PoseStamped()
        p.header = m.header
        p.header.frame_id = 'map'
        p.pose = m.pose.pose
        p.pose.position.x += self.ox
        p.pose.position.y += self.oy
        self.pub.publish(p)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--robot', required=True, help='tb3_1(티원)/tb3_2(젠지)')
    a.add_argument('--odom-topic', default=None, help='구독할 odom 토픽 (비우면 /{robot}/odom)')
    a.add_argument('--ox', type=float, default=0.0, help='map 프레임 x 오프셋')
    a.add_argument('--oy', type=float, default=0.0, help='map 프레임 y 오프셋')
    g = a.parse_args()
    odom_topic = g.odom_topic if g.odom_topic else f'/{g.robot}/odom'
    rclpy.init()
    n = OdomToPose(g.robot, odom_topic, g.ox, g.oy)
    try:
        rclpy.spin(n)
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
