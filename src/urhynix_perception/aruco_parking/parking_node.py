#!/usr/bin/env python3
# URHYNIX ControlRoom — TurtleBot3 ArUco 자동주차 노드 (TwistStamped 버전)
# 마커 ID 1번을 RealSense RGB+Depth로 검출 → APPROACH/ALIGN/PARK_DONE 상태머신으로 자동 주차.
# 발행: /cmd_vel (geometry_msgs/TwistStamped), /aruco/debug_image (sensor_msgs/Image)
# 구독: /camera/camera/color/image_raw + /camera/camera/aligned_depth_to_color/image_raw (BEST_EFFORT)
# 작성: 2026-06-09 / 안전 한도 lin=0.15m/s, ang=0.5rad/s 클램프.

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import Image
from geometry_msgs.msg import TwistStamped
from cv_bridge import CvBridge
import cv2
import numpy as np
import threading
from enum import Enum


class State(Enum):
    SEARCH = 0
    APPROACH = 1
    ALIGN = 2
    PARK_DONE = 3


class ArucoParkingNode(Node):
    def __init__(self):
        super().__init__('aruco_parking_node')

        # ── 파라미터 (Jazzy context-race 회피: batch declare) ──
        self.declare_parameters('', [
            ('target_id', 1),
            ('target_distance', 0.25),
            ('cmd_vel_topic', '/cmd_vel'),
            ('rgb_topic',   '/camera/camera/color/image_raw'),
            ('depth_topic', '/camera/camera/aligned_depth_to_color/image_raw'),
            ('dry_run', False),
        ])

        self.target_id       = self.get_parameter('target_id').value
        self.target_distance = self.get_parameter('target_distance').value
        self.dry_run         = self.get_parameter('dry_run').value
        cmd_vel_topic        = self.get_parameter('cmd_vel_topic').value
        rgb_topic            = self.get_parameter('rgb_topic').value
        depth_topic          = self.get_parameter('depth_topic').value

        # ── QoS (RealSense는 BEST_EFFORT) ──
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, depth=5)

        # ── 구독 (RGB 콜백 + Depth latest cache — 함정 #8 우회) ──
        # ApproximateTimeSynchronizer 매칭 불안정 → RGB는 콜백, Depth는 별도 캐시.
        # MultiThreadedExecutor + ReentrantCallbackGroup → callback 병렬 처리 (함정 #9)
        self.bridge = CvBridge()
        self._depth_image = None
        self._depth_lock = threading.Lock()
        self.cb_group = ReentrantCallbackGroup()
        self.create_subscription(Image, depth_topic, self.depth_callback, qos,
                                 callback_group=self.cb_group)
        self.create_subscription(Image, rgb_topic,   self.image_callback, qos,
                                 callback_group=self.cb_group)
        # 0.1초 heartbeat — callback이 멈춰도 cmd_vel 정지 발행 보장
        self._latest_cmd = (0.0, 0.0)
        self.create_timer(0.1, self.publish_loop, callback_group=self.cb_group)

        # ── 발행 ──
        self.cmd_pub   = self.create_publisher(TwistStamped, cmd_vel_topic, 10)
        self.debug_pub = self.create_publisher(Image, '/aruco/debug_image', 10)

        # ── ArUco detector (OpenCV 4.6 호환 API) ──
        self.aruco_dict   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters_create() \
            if hasattr(cv2.aruco, 'DetectorParameters_create') \
            else cv2.aruco.DetectorParameters()

        # ── 상태 + 제어 ──
        self.state = State.SEARCH
        self.no_marker_count = 0
        self._first_callback_logged = False
        self.Kp_linear  = 0.4
        self.Kp_angular = 1.5
        self.max_linear  = 0.15
        self.max_angular = 0.5

        self.get_logger().info(
            f'ArUco Parking 시작 — target_id={self.target_id}, '
            f'target_dist={self.target_distance}m, dry_run={self.dry_run}, '
            f'cmd_vel_topic={cmd_vel_topic}')

    def make_cmd(self, lin_x=0.0, ang_z=0.0):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        if self.dry_run:
            lin_x, ang_z = 0.0, 0.0
        msg.twist.linear.x  = float(lin_x)
        msg.twist.angular.z = float(ang_z)
        return msg

    def publish_loop(self):
        # heartbeat — image_callback이 멈춰도 최근 명령(또는 정지) 0.1초마다 발행
        lin_x, ang_z = self._latest_cmd
        self.cmd_pub.publish(self.make_cmd(lin_x, ang_z))

    def depth_callback(self, depth_msg):
        try:
            depth = self.bridge.imgmsg_to_cv2(depth_msg, '16UC1')
            with self._depth_lock:
                self._depth_image = depth
        except Exception as e:
            self.get_logger().error(f'depth_callback exception: {e}')

    def image_callback(self, rgb_msg):
        try:
            self._image_callback_impl(rgb_msg)
        except Exception as e:
            self.get_logger().error(f'image_callback exception: {e}')
            self._latest_cmd = (0.0, 0.0)   # 안전 정지

    def _image_callback_impl(self, rgb_msg):
        if not self._first_callback_logged:
            self.get_logger().info('🎥 첫 RGB 메시지 도착 — image_callback 가동')
            self._first_callback_logged = True
        rgb = self.bridge.imgmsg_to_cv2(rgb_msg, 'bgr8')
        with self._depth_lock:
            depth = self._depth_image
        if depth is None:
            # Depth 아직 없음 — 정지 유지, debug 영상만 발행
            self._latest_cmd = (0.0, 0.0)
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(rgb, 'bgr8'))
            return

        h, w = rgb.shape[:2]
        image_cx = w // 2

        corners, ids, _ = cv2.aruco.detectMarkers(rgb, self.aruco_dict, parameters=self.aruco_params)
        lin_x, ang_z = 0.0, 0.0

        if ids is None or self.target_id not in ids.flatten().tolist():
            # 마커 없음 → 정지
            self.no_marker_count += 1
            if self.no_marker_count > 10:
                self.state = State.SEARCH
            cv2.putText(rgb, f'STATE: {self.state.name} (no marker)',
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            self.no_marker_count = 0

            # 타겟 마커 중심 픽셀
            idx = ids.flatten().tolist().index(self.target_id)
            corner = corners[idx][0]
            cx = int(corner[:, 0].mean())
            cy = int(corner[:, 1].mean())

            # Depth 3×3 median 으로 실제 거리(m) 측정
            y1, y2 = max(0, cy-1), min(depth.shape[0], cy+2)
            x1, x2 = max(0, cx-1), min(depth.shape[1], cx+2)
            patch = depth[y1:y2, x1:x2]
            valid = patch[patch > 0]
            distance = float(np.median(valid)) / 1000.0 if len(valid) else -1.0

            # 좌우 오차 (-0.5 ~ +0.5 정규화)
            x_error = (image_cx - cx) / float(w)

            # 상태 전이
            if distance < 0:
                self.state = State.SEARCH
            elif distance > self.target_distance + 0.15:
                self.state = State.APPROACH
            elif distance > self.target_distance:
                self.state = State.ALIGN
            else:
                self.state = State.PARK_DONE

            # 제어
            if self.state == State.APPROACH:
                lin_x = self.Kp_linear  * (distance - self.target_distance)
                ang_z = self.Kp_angular * x_error
            elif self.state == State.ALIGN:
                lin_x = 0.05
                ang_z = self.Kp_angular * x_error * 0.5
            # PARK_DONE / SEARCH → 모두 0

            # 안전 클램프
            lin_x = float(np.clip(lin_x, -self.max_linear,  self.max_linear))
            ang_z = float(np.clip(ang_z, -self.max_angular, self.max_angular))

            # 디버그 오버레이
            cv2.aruco.drawDetectedMarkers(rgb, corners, ids)
            cv2.circle(rgb, (cx, cy), 5, (0, 255, 255), -1)
            cv2.putText(rgb, f'STATE: {self.state.name}',
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(rgb, f'dist: {distance:.2f}m  x_err: {x_error:+.2f}',
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(rgb, f'cmd: lin={lin_x:+.2f} ang={ang_z:+.2f}',
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        self._latest_cmd = (lin_x, ang_z)   # heartbeat가 publish
        self.debug_pub.publish(self.bridge.cv2_to_imgmsg(rgb, 'bgr8'))


def main():
    rclpy.init()
    node = ArucoParkingNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        # 종료 시 정지 메시지 — context 살아있을 때만
        try:
            if rclpy.ok():
                node.cmd_pub.publish(node.make_cmd(0.0, 0.0))
        except Exception:
            pass
        node.get_logger().info('종료 — 로봇 정지')
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
