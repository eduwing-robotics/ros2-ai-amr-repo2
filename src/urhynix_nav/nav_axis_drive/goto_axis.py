#!/usr/bin/env python3
"""goto_axis.py — 목표(grid 좌표)로 '축 정렬' 방식으로 이동.

동선: X축 정렬 회전 -> X 맞을 때까지 직진 -> Y축 정렬 회전 -> Y 맞을 때까지 직진 -> 종료.
Nav2 플래너를 쓰지 않고 직접 cmd_vel(geometry_msgs/TwistStamped)을 발행하는 단순 제어.

오차범위 2종:
  - 회전: YAW_TOLERANCE (±2°)
  - 직진/도착: POS_TOLERANCE = 로봇 두께의 반 (ROBOT_WIDTH/2)

사용: python3 goto_axis.py <gx> <gy>   (0~200)
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

# 로봇 / 오차범위
ROBOT_WIDTH = 0.14                      # TurtleBot3 Burger 폭(두께) ≈ 0.14 m
POS_TOLERANCE = ROBOT_WIDTH / 2.0       # 직진/도착 위치 허용오차 = 두께의 반 (0.07 m)
YAW_TOLERANCE = math.radians(2.0)       # 회전 정렬 허용오차 ±2°

# 속도/게인
LINEAR_SPEED = 0.12                     # m/s 직진 속도 (≤ max_speed_xy 0.3)
MAX_ANGULAR = 0.5                       # rad/s 회전속도 상한
MIN_ANGULAR = 0.08                      # 정지마찰 극복 최소 회전속도
KP_ANG = 1.2                            # 회전 비례게인
KP_HEADING = 1.0                        # 직진 중 heading 유지 게인
DRIVE_HEADING_GATE = math.radians(20.0)  # heading 오차 이만큼 넘으면 직진 멈추고 먼저 회전


def grid_to_map(gx, gy):
    return (MAP_ORIGIN_X + (gx / GRID_MAX) * MAP_SIZE,
            MAP_ORIGIN_Y + (gy / GRID_MAX) * MAP_SIZE)


def yaw_from_quat(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


def normalize(a):
    return math.atan2(math.sin(a), math.cos(a))


class GotoAxis(Node):
    def __init__(self, gx, gy):
        super().__init__('goto_axis')
        self.gx, self.gy = gx, gy
        self.tx, self.ty = grid_to_map(gx, gy)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
        self.state = 'ALIGN_X'
        self.done = False
        self.timer = self.create_timer(0.05, self.loop)  # 20Hz
        self.get_logger().info(
            f'그리드({gx},{gy}) -> 맵({self.tx:.3f},{self.ty:.3f}) | '
            f'위치오차 {POS_TOLERANCE*100:.0f}cm, 회전오차 {math.degrees(YAW_TOLERANCE):.0f}°')

    # --- I/O ---
    def current_pose(self):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
        except (LookupException, ConnectivityException, ExtrapolationException):
            return None
        tr = t.transform.translation
        return tr.x, tr.y, yaw_from_quat(t.transform.rotation)

    def send(self, vx, wz):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = vx
        msg.twist.angular.z = wz
        self.pub.publish(msg)

    def stop(self):
        for _ in range(3):
            self.send(0.0, 0.0)

    def finish(self, x, y):
        self.stop()
        ex, ey = abs(self.tx - x), abs(self.ty - y)
        self.get_logger().info(
            f'✅ 도착: 맵({x:.3f},{y:.3f}) 목표({self.tx:.3f},{self.ty:.3f}) '
            f'오차 x={ex*100:.1f}cm y={ey*100:.1f}cm')
        self.done = True
        self.timer.cancel()
        rclpy.shutdown()

    # --- 제어 스텝 ---
    def rotate_step(self, yaw, target_head):
        """target_head로 회전. 정렬되면 정지 후 True."""
        err = normalize(target_head - yaw)
        if abs(err) <= YAW_TOLERANCE:
            self.send(0.0, 0.0)
            return True
        wz = max(-MAX_ANGULAR, min(MAX_ANGULAR, KP_ANG * err))
        if abs(wz) < MIN_ANGULAR:
            wz = math.copysign(MIN_ANGULAR, wz)
        self.send(0.0, wz)
        return False

    def drive_step(self, yaw, target_head):
        """target_head 유지하며 직진. heading 많이 틀어지면 직진 멈추고 회전만."""
        err = normalize(target_head - yaw)
        wz = max(-MAX_ANGULAR, min(MAX_ANGULAR, KP_HEADING * err))
        vx = 0.0 if abs(err) > DRIVE_HEADING_GATE else LINEAR_SPEED
        self.send(vx, wz)

    # --- 메인 루프 ---
    def loop(self):
        if self.done:
            return
        pose = self.current_pose()
        if pose is None:
            self.get_logger().warn('map->base_footprint TF 대기...', throttle_duration_sec=2.0)
            return
        x, y, yaw = pose

        if self.state == 'ALIGN_X':
            if abs(self.tx - x) <= POS_TOLERANCE:
                self.state = 'ALIGN_Y'
                return
            head = 0.0 if self.tx > x else math.pi   # +x 또는 -x를 정면으로
            if self.rotate_step(yaw, head):
                self.get_logger().info('X축 정렬 완료 → 직진')
                self.state = 'DRIVE_X'

        elif self.state == 'DRIVE_X':
            if abs(self.tx - x) <= POS_TOLERANCE:
                self.stop()
                self.get_logger().info(f'X 맞춤 (x={x:.3f}, 오차 {abs(self.tx-x)*100:.1f}cm) → Y 정렬')
                self.state = 'ALIGN_Y'
            else:
                head = 0.0 if self.tx > x else math.pi
                self.drive_step(yaw, head)
                self.get_logger().info(
                    f'X 직진: x={x:.3f}→{self.tx:.3f} (남음 {abs(self.tx-x)*100:.1f}cm)',
                    throttle_duration_sec=0.5)

        elif self.state == 'ALIGN_Y':
            if abs(self.ty - y) <= POS_TOLERANCE:
                self.finish(x, y)
                return
            head = math.pi / 2 if self.ty > y else -math.pi / 2  # +y 또는 -y를 정면으로
            if self.rotate_step(yaw, head):
                self.get_logger().info('Y축 정렬 완료 → 직진')
                self.state = 'DRIVE_Y'

        elif self.state == 'DRIVE_Y':
            if abs(self.ty - y) <= POS_TOLERANCE:
                self.finish(x, y)
            else:
                head = math.pi / 2 if self.ty > y else -math.pi / 2
                self.drive_step(yaw, head)
                self.get_logger().info(
                    f'Y 직진: y={y:.3f}→{self.ty:.3f} (남음 {abs(self.ty-y)*100:.1f}cm)',
                    throttle_duration_sec=0.5)


def main():
    if len(sys.argv) < 3:
        print('사용법: python3 goto_axis.py <x> <y>  (0~200)')
        sys.exit(1)
    gx, gy = float(sys.argv[1]), float(sys.argv[2])
    if not (0 <= gx <= 200 and 0 <= gy <= 200):
        print('좌표는 0~200 범위여야 합니다')
        sys.exit(1)

    rclpy.init()
    node = GotoAxis(gx, gy)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.send(0.0, 0.0)   # 안전 정지
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
