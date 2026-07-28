#!/usr/bin/env python3
import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_ros import TransformBroadcaster


class OdomTfRelay(Node):
    def __init__(self):
        super().__init__("odom_tf_relay")
        self._broadcaster = TransformBroadcaster(self)
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=50,
        )
        self.create_subscription(Odometry, "/odom", self._on_odom, qos)

    def _on_odom(self, msg: Odometry) -> None:
        if not msg.header.frame_id or not msg.child_frame_id:
            return
        transform = TransformStamped()
        transform.header = msg.header
        transform.child_frame_id = msg.child_frame_id
        transform.transform.translation.x = msg.pose.pose.position.x
        transform.transform.translation.y = msg.pose.pose.position.y
        transform.transform.translation.z = msg.pose.pose.position.z
        transform.transform.rotation = msg.pose.pose.orientation
        self._broadcaster.sendTransform(transform)


def main() -> None:
    rclpy.init()
    node = OdomTfRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
