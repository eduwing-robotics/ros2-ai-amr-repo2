#!/usr/bin/env python3
# teleop_stamped.py — 키보드 teleop을 geometry_msgs/TwistStamped로 발행(매 틱 현재 stamp).
# 용도: 동료가 3D 매핑 중 티원을 수동 주행. turtlebot3_node가 /tb3_1/cmd_vel을 TwistStamped로 구독하고
#   stale(과거) stamp는 무시 → 표준 teleop_twist_keyboard(Twist 발행)는 안 먹는다. 이 스크립트가 그 갭을 메운다.
#   드리프트 최소 위해 상한을 느리게 둠(매핑 품질). drive_rotate.py(자동회전)의 수동 주행 짝.
# 사용(티원에서): python3 teleop_stamped.py [/tb3_1/cmd_vel]
#   키: w/x=전/후, a/d=좌/우회전, s 또는 space=정지, q 또는 Ctrl-C=종료(정지 발행).
import sys
import select
import termios
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped

LIN_STEP, ANG_STEP = 0.02, 0.1
LIN_MAX, ANG_MAX = 0.15, 0.6   # 느리게 = odom 드리프트 최소(매핑 품질 우선)
HELP = """
[teleop_stamped] 3D 매핑 수동 주행
  w / x : 전진 / 후진      a / d : 좌 / 우 회전
  s 또는 space : 정지       q 또는 Ctrl-C : 종료
  (천천히 — 벽까지 0.3~3m 유지, 급회전 금지. 한 바퀴 돌며 구석을 채운다.)
"""


def get_key(timeout=0.1):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        return sys.stdin.read(1) if r else ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else '/tb3_1/cmd_vel'
    rclpy.init()
    node = Node('teleop_stamped')
    pub = node.create_publisher(TwistStamped, topic, 10)
    lin = ang = 0.0
    print(HELP)
    print(f"publishing TwistStamped → {topic}")

    def send(lx, az):
        m = TwistStamped()
        m.header.stamp = node.get_clock().now().to_msg()
        m.header.frame_id = 'base_link'
        m.twist.linear.x = lx
        m.twist.angular.z = az
        pub.publish(m)

    try:
        while True:
            k = get_key(0.1)   # 키 없으면 0.1s 후 None → 10Hz 유지 발행
            if k == 'w':
                lin = clamp(lin + LIN_STEP, -LIN_MAX, LIN_MAX)
            elif k == 'x':
                lin = clamp(lin - LIN_STEP, -LIN_MAX, LIN_MAX)
            elif k == 'a':
                ang = clamp(ang + ANG_STEP, -ANG_MAX, ANG_MAX)
            elif k == 'd':
                ang = clamp(ang - ANG_STEP, -ANG_MAX, ANG_MAX)
            elif k in (' ', 's'):
                lin = ang = 0.0
            elif k in ('q', '\x03'):
                break
            send(lin, ang)
            print(f"\rlin={lin:+.2f} m/s  ang={ang:+.2f} rad/s   ", end='', flush=True)
    finally:
        for _ in range(5):   # 정지 명령 몇 틱 더 (안전 정지)
            send(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()
        print("\n[teleop_stamped] 정지·종료")


if __name__ == '__main__':
    main()
