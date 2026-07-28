#!/usr/bin/env python3
"""Rotate T1 until docking ArUco marker 11 is centered."""

import argparse
import math
import time

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, CompressedImage

VIDEO_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)
VIDEO_QOS_RELIABLE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)


class ArucoAligner(Node):
    def __init__(
        self,
        marker_id: int,
        marker_size: float,
        cmd_topic: str,
        target_bearing: float,
        image_topic: str,
        camera_info_topic: str,
        *,
        invert_yaw: bool = False,
        max_speed: float = 0.08,
        min_speed: float = 0.055,
        tol_deg: float = 1.5,
        use_image_error: bool = False,
        image_qos_reliable: bool = False,
    ) -> None:
        super().__init__("aruco_align_t1")
        self.marker_id = marker_id
        self.marker_size = marker_size
        self.target_bearing = target_bearing
        self.invert_yaw = invert_yaw
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.tol_rad = math.radians(tol_deg)
        self.use_image_error = use_image_error
        self.camera_matrix = None
        self.distortion = None
        self.last_image_at = None
        self.last_bearing = None
        self.last_image_error = None
        self.aligned_frames = 0
        self.publisher = self.create_publisher(TwistStamped, cmd_topic, 10)

        if hasattr(cv2.aruco, "getPredefinedDictionary"):
            self.dictionary = cv2.aruco.getPredefinedDictionary(
                cv2.aruco.DICT_4X4_50
            )
        else:
            self.dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
        if hasattr(cv2.aruco, "DetectorParameters_create"):
            self.detector_parameters = cv2.aruco.DetectorParameters_create()
        else:
            self.detector_parameters = cv2.aruco.DetectorParameters()
        self.detector = (
            cv2.aruco.ArucoDetector(self.dictionary, self.detector_parameters)
            if hasattr(cv2.aruco, "ArucoDetector")
            else None
        )
        self.create_subscription(
            CameraInfo,
            camera_info_topic,
            self.on_camera_info,
            1,
        )
        image_qos = VIDEO_QOS_RELIABLE if image_qos_reliable else VIDEO_QOS
        self.create_subscription(
            CompressedImage,
            image_topic,
            self.on_image,
            image_qos,
        )

    def on_camera_info(self, message: CameraInfo) -> None:
        matrix = np.asarray(message.k, dtype=np.float64).reshape(3, 3)
        if float(matrix[0, 0]) <= 1.0 or float(matrix[1, 1]) <= 1.0:
            self.camera_matrix = None
            self.distortion = None
            return
        self.camera_matrix = matrix
        self.distortion = np.asarray(message.d, dtype=np.float64)

    def on_image(self, message: CompressedImage) -> None:
        self.last_image_at = time.monotonic()
        image = cv2.imdecode(np.frombuffer(message.data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            self.last_bearing = None
            return
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(image)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(
                image, self.dictionary, parameters=self.detector_parameters
            )
        self.last_bearing = None
        self.last_image_error = None
        if ids is None:
            return

        half = self.marker_size * 0.5
        object_points = np.asarray(
            [
                [-half, half, 0.0],
                [half, half, 0.0],
                [half, -half, 0.0],
                [-half, -half, 0.0],
            ],
            dtype=np.float32,
        )
        height, width = image.shape[:2]
        for index, detected_id in enumerate(ids.flatten()):
            if int(detected_id) != self.marker_id:
                continue
            image_points = corners[index][0].astype(np.float32)
            # If marker is leaving the frame, nudge back toward center (don't keep spinning).
            xs = image_points[:, 0]
            marker_cx = float(np.mean(xs))
            self.last_image_error = (marker_cx - width * 0.5) / width
            if float(xs.min()) < width * 0.10 or float(xs.max()) > width * 0.90:
                fx = width / (2.0 * math.tan(math.radians(31.1)))
                # Soft bearing so controller turns back toward center gently.
                self.last_bearing = math.atan2(marker_cx - (width * 0.5), fx)
                return

            if self.use_image_error or self.camera_matrix is None:
                # Fall back to image-center error when camera_info is empty.
                fx = width / (2.0 * math.tan(math.radians(31.1)))
                self.last_bearing = math.atan2(marker_cx - (width * 0.5), fx)
                return

            solved, _, tvec = cv2.solvePnP(
                object_points,
                image_points,
                self.camera_matrix,
                self.distortion,
                flags=cv2.SOLVEPNP_IPPE_SQUARE,
            )
            if solved:
                x, _, z = tvec.reshape(3)
                bearing = math.atan2(float(x), float(z))
                if math.isfinite(bearing):
                    self.last_bearing = bearing
                    return
            fx = width / (2.0 * math.tan(math.radians(31.1)))
            self.last_bearing = math.atan2(marker_cx - (width * 0.5), fx)
            return

    def publish(self, angular: float = 0.0) -> None:
        message = TwistStamped()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_footprint"
        message.twist.angular.z = angular
        self.publisher.publish(message)

    def stop(self) -> None:
        for _ in range(15):
            self.publish()
            rclpy.spin_once(self, timeout_sec=0.01)
            time.sleep(0.03)

    def run(self, timeout: float = 45.0) -> bool:
        deadline = time.monotonic() + timeout
        last_log = 0.0
        ever_seen = False
        last_cmd_sign = 0.0  # +1 = CCW (left), -1 = CW (right)
        recover_sign = 0.0
        recover_until = 0.0
        lost_since = None
        try:
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(self, timeout_sec=0.03)
                now = time.monotonic()
                image_stale = (
                    self.last_image_at is None or now - self.last_image_at > 0.5
                )
                seen = (not image_stale) and self.last_bearing is not None

                # --- Lost after having seen: reverse and re-acquire ---
                if not seen:
                    self.aligned_frames = 0
                    if ever_seen:
                        if lost_since is None:
                            lost_since = now
                            # Reverse the last turn direction to come back to the marker.
                            recover_sign = -last_cmd_sign if last_cmd_sign != 0.0 else 1.0
                            recover_until = now + 2.5
                            self.get_logger().warn(
                                "마커 놓침 → 반대 방향으로 재탐색 "
                                f"(wz_sign={recover_sign:+.0f})"
                            )
                        # Keep sweeping back for a bit, then slowly continue same way.
                        if now < recover_until:
                            self.publish(recover_sign * max(self.min_speed, 0.045))
                        else:
                            # Alternate sweep every 2s if still lost.
                            phase = int((now - recover_until) / 2.0) % 2
                            sweep = recover_sign if phase == 0 else -recover_sign
                            self.publish(sweep * max(self.min_speed, 0.04))
                        if now - last_log > 0.5:
                            self.get_logger().info("재탐색 중 (마커 미검출)")
                            last_log = now
                    else:
                        # Never seen yet: slow left/right sweep to find marker.
                        phase = int(now / 2.5) % 2
                        self.publish((1.0 if phase == 0 else -1.0) * 0.05)
                        if now - last_log > 1.0:
                            self.get_logger().info("초기 탐색 중 (마커 미검출)")
                            last_log = now
                    continue

                # Marker visible again.
                if lost_since is not None:
                    self.get_logger().info(
                        f"마커 재검출 (놓친 시간 {now - lost_since:.1f}s) → 미세 정렬"
                    )
                    lost_since = None
                    recover_until = 0.0
                ever_seen = True

                error = self.last_bearing - self.target_bearing
                if self.invert_yaw:
                    error = -error
                if now - last_log > 0.25:
                    img_err = (
                        f" image_err={self.last_image_error:+.3f}"
                        if self.last_image_error is not None
                        else ""
                    )
                    self.get_logger().info(
                        f"marker bearing={math.degrees(self.last_bearing):+.2f}deg "
                        f"error={math.degrees(error):+.2f}deg{img_err}"
                    )
                    last_log = now
                if abs(error) <= self.tol_rad:
                    self.aligned_frames += 1
                    self.publish()
                    last_cmd_sign = 0.0
                    if self.aligned_frames >= 8:
                        self.get_logger().info("ArUco 정면 각도 정렬 완료")
                        return True
                    continue

                self.aligned_frames = 0
                if abs(error) < math.radians(8.0):
                    speed = self.min_speed
                else:
                    speed = min(self.max_speed, max(self.min_speed, abs(error) * 0.35))
                cmd = math.copysign(speed, -error)
                last_cmd_sign = 1.0 if cmd > 0 else -1.0
                self.publish(cmd)

            self.get_logger().error("ArUco 각도 정렬 시간 초과")
            return False
        finally:
            self.stop()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--marker-id", type=int, default=11)
    parser.add_argument("--marker-size", type=float, default=0.05)
    parser.add_argument("--cmd-topic", default="/cmd_vel")
    parser.add_argument("--image-topic", default="/camera/color/image_detect/compressed")
    parser.add_argument("--camera-info-topic", default="/tb3_1/camera/color/camera_info")
    parser.add_argument("--target-bearing-deg", type=float, default=0.0,
                        help="Bearing seen when the robot body is correctly aligned.")
    args = parser.parse_args()

    rclpy.init()
    node = ArucoAligner(args.marker_id, args.marker_size, args.cmd_topic,
                        math.radians(args.target_bearing_deg), args.image_topic, args.camera_info_topic)
    try:
        return 0 if node.run() else 1
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
