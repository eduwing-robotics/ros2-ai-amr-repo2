#!/usr/bin/env python3
# scan_normalize.py — LDS-03처럼 매 스캔 빔 개수가 변동(399~402)하는 LaserScan을
#   고정 빔 수 N으로 리샘플해 재발행. slam_toolbox(Karto)는 첫 스캔 빔 수로 센서를
#   고정 등록하고 다른 길이 스캔을 전부 거부 → 맵 0. 이 릴레이로 길이를 일관화.
#   각 출력 빔 각도에 대응하는 입력 인덱스를 nearest로 매핑(±1~2빔 변동만 흡수, 정보손실 무시 가능).
# 사용: python3 scan_normalize.py [in_topic=/scan] [out_topic=/scan_fixed] [N=400]
import sys, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

IN = sys.argv[1] if len(sys.argv) > 1 else '/scan'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/scan_fixed'
N = int(sys.argv[3]) if len(sys.argv) > 3 else 400


class Norm(Node):
    def __init__(self):
        super().__init__('scan_normalize')
        self.pub = self.create_publisher(LaserScan, OUT, qos_profile_sensor_data)
        self.create_subscription(LaserScan, IN, self.cb, qos_profile_sensor_data)
        self.get_logger().info(f'scan_normalize: {IN} -> {OUT}, N={N}')

    def cb(self, m):
        n_in = len(m.ranges)
        if n_in == 0:
            return
        new_inc = (m.angle_max - m.angle_min) / (N - 1)
        out = LaserScan()
        out.header = m.header
        out.angle_min = m.angle_min
        out.angle_max = m.angle_max
        out.angle_increment = new_inc
        out.time_increment = m.time_increment
        out.scan_time = m.scan_time
        out.range_min = m.range_min
        out.range_max = m.range_max
        ranges = [0.0] * N
        inten = [0.0] * N
        has_int = len(m.intensities) == n_in
        for i in range(N):
            ang = out.angle_min + i * new_inc
            j = int(round((ang - m.angle_min) / m.angle_increment)) if m.angle_increment else i
            if j < 0:
                j = 0
            elif j >= n_in:
                j = n_in - 1
            ranges[i] = m.ranges[j]
            if has_int:
                inten[i] = m.intensities[j]
        out.ranges = ranges
        out.intensities = inten if has_int else []
        self.pub.publish(out)


def main():
    rclpy.init()
    node = Norm()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
