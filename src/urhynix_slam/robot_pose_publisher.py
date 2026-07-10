#!/usr/bin/env python3
# robot_pose_publisher.py — 로봇 tf(map→base_footprint)를 /<robot>/pose(PoseStamped, map프레임)로 발행.
# pose_logger.py와 Unity ControlRoom(RobotPoseFeed)이 이미 기대하는 "로봇별 위치 토픽"의 발행원.
# 듀얼로봇 런타임에서는 각 로봇을 자기 namespace로 띄워 /tb3_1/pose, /tb3_2/pose로 구분된다.
#   단일/비-ns 맵제작:   python3 robot_pose_publisher.py --robot tb3_1
#   네임스페이스 런타임: python3 robot_pose_publisher.py --robot tb3_1 \
#                          --root tb3_1/map --target tb3_1/base_footprint
# 도메인 210, AMCL 또는 SLAM이 map→base_footprint tf를 publish 중이어야 함(라이다 ON 선행).
import argparse
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException


class RobotPosePublisher(Node):
    def __init__(self, robot, root, target, rate_hz):
        super().__init__('robot_pose_publisher')
        self.root = root
        self.target = target
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.pub = self.create_publisher(PoseStamped, f'/{robot}/pose', 10)
        self.timer = self.create_timer(1.0 / max(rate_hz, 0.1), self.tick)
        self._warned = False
        self.get_logger().info(
            f'/{robot}/pose 발행: tf {root}→{target} @ {rate_hz}Hz')

    def tick(self):
        try:
            t = self.buffer.lookup_transform(self.root, self.target, rclpy.time.Time())
        except (LookupException, ConnectivityException, ExtrapolationException):
            if not self._warned:
                self.get_logger().warn(f'tf {self.root}→{self.target} 대기 중(라이다/AMCL 확인)')
                self._warned = True
            return
        self._warned = False

        msg = PoseStamped()
        msg.header.stamp = t.header.stamp
        msg.header.frame_id = self.root
        tr = t.transform.translation
        msg.pose.position.x = tr.x
        msg.pose.position.y = tr.y
        msg.pose.position.z = tr.z
        msg.pose.orientation = t.transform.rotation
        self.pub.publish(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--robot', default='tb3_1', help='tb3_1(티원)/tb3_2(젠지)')
    ap.add_argument('--root', default='map', help='기준 프레임(네임스페이스 시 tb3_1/map)')
    ap.add_argument('--target', default='base_footprint', help='로봇 프레임(네임스페이스 시 tb3_1/base_footprint)')
    ap.add_argument('--rate', type=float, default=10.0, help='발행 주파수(Hz)')
    args = ap.parse_args()

    rclpy.init()
    node = RobotPosePublisher(args.robot, args.root, args.target, args.rate)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
