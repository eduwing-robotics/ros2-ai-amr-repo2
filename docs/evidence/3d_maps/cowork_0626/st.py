import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, CompressedImage, CameraInfo

rclpy.init()
n = Node("st")
last = {}


def mk(name):
    def cb(m):
        last[name] = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        if len(last) == 3:
            c = last.get("c", 0.0)
            d = last.get("d", 0.0)
            i = last.get("i", 0.0)
            vals = sorted([c, d, i])
            spread = vals[-1] - vals[0]
            print("upd=%s | color=%.3f depth=%.3f info=%.3f | spread=%.3fs" % (name, c, d, i, spread), flush=True)
    return cb


n.create_subscription(CompressedImage, "/tb3_1/camera/color/image_raw/compressed", mk("c"), qos_profile_sensor_data)
n.create_subscription(Image, "/tb3_1/camera/aligned_depth_to_color/image_raw", mk("d"), qos_profile_sensor_data)
n.create_subscription(CameraInfo, "/tb3_1/camera/aligned_depth_to_color/camera_info", mk("i"), qos_profile_sensor_data)

t0 = time.time()
while time.time() - t0 < 10:
    rclpy.spin_once(n, timeout_sec=0.2)
