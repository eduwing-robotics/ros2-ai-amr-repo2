#!/usr/bin/env python3
# drive_rotate.py — /<topic>(geometry_msgs/TwistStamped)으로 제자리 회전 명령을 현재 stamp로 N초간 발행 후 정지.
# 용도: AMCL 수렴용 안전 주행(병진 0 = 벽 충돌 없음). 회전으로 scan 시점을 바꿔 particle을 실제 위치로 수렴시킴.
# TwistStamped는 stamp가 과거면 diff_drive_controller가 stale로 무시 → 매 틱 현재시각 stamp 필수(ros2 topic pub로는 불가).
#   python3 drive_rotate.py /tb3_1/cmd_vel 0.4 10   # topic wz(rad/s) secs
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped


class Rotate(Node):
    def __init__(self, topic, wz, secs):
        super().__init__('amcl_converge_drive')
        self.pub = self.create_publisher(TwistStamped, topic, 10)
        self.wz = wz
        self.n = 0
        self.spin_ticks = int(secs * 10)
        self.timer = self.create_timer(0.1, self.tick)

    def tick(self):
        m = TwistStamped()
        m.header.stamp = self.get_clock().now().to_msg()
        m.header.frame_id = 'base_link'
        m.twist.angular.z = self.wz if self.n < self.spin_ticks else 0.0
        self.pub.publish(m)
        self.n += 1
        if self.n >= self.spin_ticks + 5:   # 정지 명령 몇 틱 더 보내고 종료
            rclpy.shutdown()


def main():
    topic, wz, secs = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    rclpy.init()
    n = Rotate(topic, wz, secs)
    rclpy.spin(n)


if __name__ == '__main__':
    main()
