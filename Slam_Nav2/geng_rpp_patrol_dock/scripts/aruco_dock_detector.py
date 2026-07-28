#!/usr/bin/env python3
"""Detect a docking ArUco marker from a compressed ROS camera stream.

Gen.G ArUco dock detector UI: drawDetectedMarkers + axes + status text.
Uses the Gen.G entry from aruco_markers/markers.yaml.
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, CompressedImage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from aruco_marker_config import marker_for_robot  # noqa: E402

VIDEO_QOS_BE = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)
VIDEO_QOS_RELIABLE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
)


class ArucoDockDetector(Node):
    def __init__(
        self,
        marker_id: int,
        marker_size: float,
        image_topic: str,
        camera_info_topic: str,
        window_title: str,
        scale: float,
        reliable_image: bool = False,
    ) -> None:
        super().__init__("aruco_dock_detector")
        self.marker_id = marker_id
        self.marker_size = marker_size
        self.scale = scale
        self.window_title = window_title
        self.camera_matrix = None
        self.distortion = None
        self.last_log = 0.0
        self.frame_count = 0
        self.fps_started_at = time.monotonic()

        if hasattr(cv2.aruco, "getPredefinedDictionary"):
            self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        else:
            self.dictionary = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
        if hasattr(cv2.aruco, "DetectorParameters_create"):
            self.parameters = cv2.aruco.DetectorParameters_create()
        else:
            self.parameters = cv2.aruco.DetectorParameters()
        self.detector = (
            cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
            if hasattr(cv2.aruco, "ArucoDetector")
            else None
        )

        cv2.namedWindow(self.window_title, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_title, 1280, 960)

        self.create_subscription(CameraInfo, camera_info_topic, self.on_camera_info, 1)
        # One subscription only (dual QoS caused mixed-frame feel).
        image_qos = VIDEO_QOS_RELIABLE if reliable_image else VIDEO_QOS_BE
        self.create_subscription(CompressedImage, image_topic, self.on_image, image_qos)
        self.get_logger().info(
            f"ArUco detector id={marker_id} image={image_topic} info={camera_info_topic} "
            f"qos={'RELIABLE' if reliable_image else 'BEST_EFFORT'}"
        )
        self._last_show = 0.0
        self._min_show_interval = 1.0 / 12.0


    def on_camera_info(self, message: CameraInfo) -> None:
        matrix = np.asarray(message.k, dtype=np.float64).reshape(3, 3)
        # Gen.G camera_ros often publishes empty calibration.
        if float(matrix[0, 0]) <= 1.0 or float(matrix[1, 1]) <= 1.0:
            self.camera_matrix = None
            self.distortion = None
            return
        self.camera_matrix = matrix
        self.distortion = np.asarray(message.d, dtype=np.float64)

    def on_image(self, message: CompressedImage) -> None:
        now = time.monotonic()
        # Drop excess frames so display doesn't look like mixed/ghosted frames.
        if now - self._last_show < self._min_show_interval:
            return
        self._last_show = now

        self.frame_count += 1
        elapsed = now - self.fps_started_at
        if elapsed >= 2.0:
            self.get_logger().info(f"camera receive ~{self.frame_count / elapsed:.1f} fps")
            self.frame_count = 0
            self.fps_started_at = now

        image = cv2.imdecode(np.frombuffer(message.data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return

        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(image)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(
                image, self.dictionary, parameters=self.parameters
            )

        # Only draw/use the configured docking ID (11 or 12).
        # Other IDs (e.g. 17 on a picture frame) are false positives in DICT_4X4_50.
        found = False
        other_ids = []
        if ids is not None:
            keep_corners = []
            keep_ids = []
            for index, detected_id in enumerate(ids.flatten()):
                did = int(detected_id)
                if did == self.marker_id:
                    keep_corners.append(corners[index])
                    keep_ids.append([did])
                else:
                    other_ids.append(did)
            if keep_ids:
                keep_corners_arr = tuple(keep_corners)
                keep_ids_arr = np.asarray(keep_ids, dtype=np.int32)
                cv2.aruco.drawDetectedMarkers(image, keep_corners_arr, keep_ids_arr)
                corners, ids = keep_corners_arr, keep_ids_arr
            else:
                corners, ids = None, None

        if other_ids and now - self.last_log >= 2.0:
            self.get_logger().info(
                f"ignored false-positive IDs={sorted(set(other_ids))} "
                f"(only ID {self.marker_id} counts)"
            )
            self.last_log = now

        if ids is not None:
            for index, detected_id in enumerate(ids.flatten()):
                if int(detected_id) != self.marker_id:
                    continue
                found = True
                pts = corners[index][0].astype(np.float32)
                center_x = float(np.mean(pts[:, 0]))
                image_error = (center_x - image.shape[1] * 0.5) / image.shape[1]

                if self.camera_matrix is not None:
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
                    solved, rvec, tvec = cv2.solvePnP(
                        object_points,
                        pts,
                        self.camera_matrix,
                        self.distortion,
                        flags=cv2.SOLVEPNP_IPPE_SQUARE,
                    )
                    if solved:
                        rvec = rvec.reshape(3)
                        tvec = tvec.reshape(3)
                        cv2.drawFrameAxes(
                            image,
                            self.camera_matrix,
                            self.distortion,
                            rvec,
                            tvec,
                            self.marker_size * 0.5,
                        )
                        bearing = math.atan2(float(tvec[0]), float(tvec[2]))
                        if now - self.last_log >= 0.5:
                            self.get_logger().info(
                                f"id={self.marker_id} distance={tvec[2]:.3f}m "
                                f"lateral={tvec[0]:+.3f}m "
                                f"bearing={math.degrees(bearing):+.1f}deg "
                                f"image_error={image_error:+.3f}"
                            )
                            self.last_log = now
                        cv2.putText(
                            image,
                            f"ID {self.marker_id}  z={tvec[2]:.2f}m  "
                            f"bearing={math.degrees(bearing):+.1f}deg",
                            (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 255, 0),
                            2,
                        )
                    else:
                        cv2.putText(
                            image,
                            f"ID {self.marker_id}  image_error={image_error:+.3f}",
                            (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.9,
                            (0, 255, 0),
                            2,
                        )
                else:
                    # No calibration: still show detection with the Gen.G overlay.
                    bearing_approx = math.atan2(
                        center_x - image.shape[1] * 0.5, image.shape[1] * 0.5
                    )
                    if now - self.last_log >= 0.5:
                        self.get_logger().info(
                            f"id={self.marker_id} image_error={image_error:+.3f} "
                            f"bearing_approx={math.degrees(bearing_approx):+.1f}deg "
                            "(no camera calibration)"
                        )
                        self.last_log = now
                    cv2.putText(
                        image,
                        f"ID {self.marker_id}  image_error={image_error:+.3f}  "
                        f"bearing~{math.degrees(bearing_approx):+.1f}deg",
                        (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.9,
                        (0, 255, 0),
                        2,
                    )

        if not found:
            cv2.putText(
                image,
                f"Searching for ArUco ID {self.marker_id}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 0, 255),
                2,
            )

        h, w = image.shape[:2]
        cv2.drawMarker(image, (w // 2, h // 2), (255, 255, 0), cv2.MARKER_CROSS, 28, 2)
        if self.scale != 1.0:
            image = cv2.resize(
                image, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_LINEAR
            )
        cv2.imshow(self.window_title, image)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            raise SystemExit(0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--robot", choices=("geng",), default="geng")
    parser.add_argument("--marker-id", type=int, default=None)
    parser.add_argument("--marker-size", type=float, default=None)
    parser.add_argument("--image-topic", default=None)
    parser.add_argument("--camera-info-topic", default=None)
    parser.add_argument(
        "--scale",
        type=float,
        default=2.0,
        help="Display scale (default 2.0 for larger window)",
    )
    args = parser.parse_args()

    cfg = marker_for_robot(args.robot)
    marker_id = int(args.marker_id if args.marker_id is not None else cfg["marker_id"])
    marker_size = float(
        args.marker_size if args.marker_size is not None else cfg["marker_size_m"]
    )
    image_topic = args.image_topic or cfg["image_topic"]
    camera_info_topic = args.camera_info_topic or cfg["camera_info_topic"]
    robot_key = cfg["robot"]
    window_title = "Gen.G ArUco Dock Detector"

    rclpy.init()
    node = ArucoDockDetector(
        marker_id,
        marker_size,
        image_topic,
        camera_info_topic,
        window_title,
        args.scale,
        reliable_image=(robot_key == "geng"),
    )
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
