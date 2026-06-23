#!/usr/bin/env python3
"""pose_logger.py — 로봇 측 /tb3_*/pose 구독 → Supabase pose_logs INSERT.

URHYNIX 박물관/미술관 디지털트윈경비로봇 좌표 기록기.
젠지/티원 각각 로봇 PC에서 systemd service 또는 백그라운드 프로세스로 실행한다.
Supabase anon key + RLS 정책으로 INSERT (service_role 미반입).

SCHEMA: docs/ref/SCHEMA.md `pose_logs` (Planned Extensions SCRUM-23)
환경변수:
  - SUPABASE_URL=https://ueupkrxwybuuqxflstvg.supabase.co
  - SUPABASE_ANON_KEY=...
  - URHYNIX_ROBOT_ID=tb3_1 또는 tb3_2
  - URHYNIX_SESSION_ID=<현재 세션 UUID>
  - URHYNIX_NAV_MODE=patrol (기본) / dispatch / lidar_boost / manual
"""
import math
import os
from datetime import datetime, timezone

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from supabase import Client, create_client  # pip install supabase


def _quaternion_to_yaw(q) -> float:
    # ROS quaternion → yaw(z축 회전, radian)
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class PoseLogger(Node):
    def __init__(self) -> None:
        super().__init__('pose_logger')
        self.robot_id = os.environ.get('URHYNIX_ROBOT_ID', 'tb3_unknown')
        self.session_id = os.environ.get('URHYNIX_SESSION_ID')
        self.nav_mode = os.environ.get('URHYNIX_NAV_MODE', 'patrol')

        if not self.session_id:
            self.get_logger().warn('URHYNIX_SESSION_ID 미설정 — INSERT 시 NULL FK 위반 위험')

        url = os.environ['SUPABASE_URL']
        key = os.environ['SUPABASE_ANON_KEY']
        self.supabase: Client = create_client(url, key)

        topic = f'/{self.robot_id}/pose'
        self.subscription = self.create_subscription(PoseStamped, topic, self.on_pose, 10)
        self.get_logger().info(
            f'PoseLogger 구독: {topic}, robot={self.robot_id}, session={self.session_id}, nav_mode={self.nav_mode}'
        )

    def on_pose(self, msg: PoseStamped) -> None:
        stamp_sec = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        ts_iso = datetime.fromtimestamp(stamp_sec, tz=timezone.utc).isoformat()
        entry = {
            'session_id': self.session_id,
            'robot_id': self.robot_id,
            'ts': ts_iso,
            'x': float(msg.pose.position.x),
            'y': float(msg.pose.position.y),
            'theta': _quaternion_to_yaw(msg.pose.orientation),
            'source_topic': self.subscription.topic_name,
            'nav_mode': self.nav_mode,
        }
        try:
            self.supabase.table('pose_logs').insert(entry).execute()
        except Exception as e:  # noqa: BLE001
            self.get_logger().error(f'pose_logs INSERT 실패: {e}')


def main() -> None:
    rclpy.init()
    node = PoseLogger()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
