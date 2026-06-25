#!/usr/bin/env python3
"""rotate_to_goal.py — 목표(grid 좌표)를 정면으로 바라볼 때까지 제자리 회전.

이동은 하지 않고 로봇 heading만 목표 방향으로 정렬한다.
현재 pose는 map->base_footprint TF에서 읽고, /cmd_vel(geometry_msgs/TwistStamped)로
angular.z만 비례제어로 발행한다. 오차가 허용범위에 들면 정지 후 종료.

사용: python3 rotate_to_goal.py <gx> <gy>   (0~200)
전제: AMCL localize 정상 (map->base_footprint TF 유효).
"""
import math
import sys

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

# 좌표계 (CLAUDE.md SSOT — nav2_goal.py와 동일)
MAP_ORIGIN_X = -0.737
MAP_ORIGIN_Y = -2.118
MAP_SIZE = 2.8
GRID_MAX = 200.0

# 회전 튜닝
YAW_TOLERANCE = math.radians(2.0)   # 정렬 완료 허용오차 ±2°
MAX_ANGULAR = 0.5                    # rad/s 회전속도 상한 (max_vel_theta 1.0 밑)
MIN_ANGULAR = 0.08                  # 정지마찰 극복 최소 회전속도
KP = 1.2                            # 비례 게인 (error[rad] -> angular.z)


def grid_to_map(gx, gy):
    return (MAP_ORIGIN_X + (gx / GRID_MAX) * MAP_SIZE,
            MAP_ORIGIN_Y + (gy / GRID_MAX) * MAP_SIZE)


def yaw_from_quat(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


def normalize(a):
    return math.atan2(math.sin(a), math.cos(a))


class RotateToGoal(Node):
    def __init__(self, gx, gy):
        super().__init__('rotate_to_goal')
        self.gx, self.gy = gx, gy
        self.tx, self.ty = grid_to_map(gx, gy)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.done = False
        self.timer = self.create_timer(0.05, self.loop)  # 20Hz
        self.get_logger().info(
            f'그리드({gx},{gy}) -> 맵({self.tx:.3f},{self.ty:.3f}) 방향 정렬 시작')

    def current_pose(self):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
        except (LookupException, ConnectivityException, ExtrapolationException):
            return None
        tr = t.transform.translation
        return tr.x, tr.y, yaw_from_quat(t.transform.rotation)

    def send(self, wz):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.angular.z = wz
        self.pub.publish(msg)

    def loop(self):
        if self.done:
            return
        pose = self.current_pose()
        if pose is None:
            self.get_logger().warn('map->base_footprint TF 대기...', throttle_duration_sec=2.0)
            return

        x, y, yaw = pose
        bearing = math.atan2(self.ty - y, self.tx - x)  # 로봇->목표 방향
        err = normalize(bearing - yaw)

        if abs(err) <= YAW_TOLERANCE:
            for _ in range(3):
                self.send(0.0)
            self.get_logger().info(
                f'✅ 정렬 완료: 잔여오차 {math.degrees(err):.1f}° '
                f'(목표방향 {math.degrees(bearing):.1f}°)')
            self.done = True
            self.timer.cancel()
            rclpy.shutdown()
            return

        wz = max(-MAX_ANGULAR, min(MAX_ANGULAR, KP * err))
        if abs(wz) < MIN_ANGULAR:
            wz = math.copysign(MIN_ANGULAR, wz)
        self.send(wz)
        self.get_logger().info(
            f'회전 중: heading {math.degrees(yaw):.1f}° -> 목표 {math.degrees(bearing):.1f}° '
            f'(오차 {math.degrees(err):.1f}°, wz={wz:.2f})', throttle_duration_sec=0.5)


def main():
    if len(sys.argv) < 3:
        print('사용법: python3 rotate_to_goal.py <x> <y>  (0~200)')
        sys.exit(1)
    gx, gy = float(sys.argv[1]), float(sys.argv[2])
    if not (0 <= gx <= 200 and 0 <= gy <= 200):
        print('좌표는 0~200 범위여야 합니다')
        sys.exit(1)

    rclpy.init()
    node = RotateToGoal(gx, gy)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.send(0.0)   # 안전 정지
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
