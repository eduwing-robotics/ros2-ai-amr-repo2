"""Nav2 mission executor for patrol, dispatch, and charge-wait handoff."""

from __future__ import annotations

import math
import time
from enum import Enum
from typing import Optional

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.task import Future
from std_msgs.msg import Float32, String

from museum_patrol_system.msg import MuseumState


class MissionState(str, Enum):
    """High-level navigation states for one robot."""

    IDLE = 'idle'
    PATROLLING = 'patrolling'
    DISPATCHING = 'dispatching'
    GOING_TO_CHARGE_WAIT = 'going_to_charge_wait'
    CHARGING_WAIT = 'charging_wait'
    ERROR = 'error'


class PatrolNavigationNode(Node):
    """Send Nav2 goals according to patrol, event, and battery handoff state."""

    def __init__(self) -> None:
        super().__init__('patrol_navigation')

        self.declare_parameter('robot_id', 't1')
        self.declare_parameter('display_name', 'T1')
        self.declare_parameter('navigate_action', 'navigate_to_pose')
        self.declare_parameter('task_state_topic', '/museum/task/state')
        self.declare_parameter('battery_topic', '/museum/battery/level')
        self.declare_parameter('status_topic', '/museum/navigation/status')
        self.declare_parameter('battery_low_threshold_pct', 20.0)
        self.declare_parameter('battery_resume_threshold_pct', 35.0)
        self.declare_parameter('goal_frame', 'map')
        self.declare_parameter('goal_timeout_sec', 60.0)
        self.declare_parameter('waypoint_pause_sec', 1.0)
        self.declare_parameter('patrol_waypoints', [])
        self.declare_parameter('charge_wait_pose', [0.0, 0.0, 0.0])
        self.declare_parameter('event_pose', [0.0, 0.0, 0.0])
        self.declare_parameter('start_patrolling', True)
        self.declare_parameter('patrol_on_battery_handoff', False)
        self.declare_parameter('dispatch_on_events', True)

        self.robot_id = self.get_parameter('robot_id').value
        self.display_name = self.get_parameter('display_name').value
        self.goal_frame = self.get_parameter('goal_frame').value
        self.goal_timeout_sec = float(self.get_parameter('goal_timeout_sec').value)
        self.waypoint_pause_sec = float(self.get_parameter('waypoint_pause_sec').value)
        self.battery_low_threshold = float(
            self.get_parameter('battery_low_threshold_pct').value
        )
        self.battery_resume_threshold = float(
            self.get_parameter('battery_resume_threshold_pct').value
        )
        self.patrol_on_battery_handoff = bool(
            self.get_parameter('patrol_on_battery_handoff').value
        )
        self.dispatch_on_events = bool(self.get_parameter('dispatch_on_events').value)
        self.patrol_waypoints = self._load_pose_list(
            self.get_parameter('patrol_waypoints').value
        )
        self.charge_wait_pose = self._load_pose(
            self.get_parameter('charge_wait_pose').value,
            'charge_wait_pose',
        )
        self.event_pose = self._load_pose(
            self.get_parameter('event_pose').value,
            'event_pose',
        )

        navigate_action = self.get_parameter('navigate_action').value
        task_state_topic = self.get_parameter('task_state_topic').value
        battery_topic = self.get_parameter('battery_topic').value
        status_topic = self.get_parameter('status_topic').value

        self.nav_client = ActionClient(self, NavigateToPose, navigate_action)
        self.create_subscription(MuseumState, task_state_topic, self._task_state_cb, 10)
        self.create_subscription(Float32, battery_topic, self._battery_cb, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)

        self.state = MissionState.IDLE
        self.active_scenario = 'idle'
        self.battery_pct = 100.0
        self.current_waypoint_index = 0
        self._active_goal_kind: Optional[str] = None
        self._active_goal_handle = None
        self._goal_pending = False
        self._goal_sent_at = 0.0
        self._waiting_until = 0.0

        if self.get_parameter('start_patrolling').value and self.patrol_waypoints:
            self.state = MissionState.PATROLLING

        self.create_timer(0.5, self._tick)
        self.get_logger().info(
            f'{self.display_name} patrol navigation ready: '
            f'{len(self.patrol_waypoints)} patrol waypoints, action={navigate_action}'
        )

    def _load_pose_list(self, raw_value) -> list[tuple[float, float, float]]:
        poses = []
        for index, item in enumerate(raw_value):
            poses.append(self._load_pose(item, f'patrol_waypoints[{index}]'))
        return poses

    def _load_pose(self, raw_value, name: str) -> tuple[float, float, float]:
        if isinstance(raw_value, str):
            raw_value = [part.strip() for part in raw_value.split(',')]
        if len(raw_value) != 3:
            raise ValueError(f'{name} must be [x, y, yaw]')
        return (float(raw_value[0]), float(raw_value[1]), float(raw_value[2]))

    def _task_state_cb(self, msg: MuseumState) -> None:
        self.active_scenario = msg.scenario_id

    def _battery_cb(self, msg: Float32) -> None:
        self.battery_pct = float(msg.data)

    def _tick(self) -> None:
        self._publish_status()

        now = time.monotonic()
        if now < self._waiting_until:
            return

        if self._goal_pending:
            if now - self._goal_sent_at > 5.0:
                self.get_logger().warn('Goal response timeout; clearing pending goal')
                self._goal_pending = False
                self._active_goal_kind = None
            return

        if self.battery_pct <= self.battery_low_threshold:
            if self._active_goal_kind != 'charge_wait':
                self._preempt_active_goal('battery low')
            if self.state not in (
                MissionState.GOING_TO_CHARGE_WAIT,
                MissionState.CHARGING_WAIT,
            ):
                self.get_logger().warn(
                    f'Battery low ({self.battery_pct:.1f}%). '
                    'Cancel patrol/dispatch and move to charge wait pose.'
                )
                self.state = MissionState.GOING_TO_CHARGE_WAIT
            if not self._has_active_goal():
                self._send_goal(self.charge_wait_pose, 'charge_wait')
            return

        if (
            self.state == MissionState.CHARGING_WAIT
            and self.battery_pct < self.battery_resume_threshold
        ):
            return

        if self._has_active_goal():
            if now - self._goal_sent_at > self.goal_timeout_sec:
                self.get_logger().warn('Goal timeout; canceling current navigation goal')
                self._cancel_active_goal()
            return

        event_scenarios = (
            'exhibit_contact',
            'night_intruder',
            'exhibit_loss',
            'fire_response',
        )
        if self.dispatch_on_events and self.active_scenario in event_scenarios:
            self.state = MissionState.DISPATCHING
            self._send_goal(self.event_pose, f'event:{self.active_scenario}')
            return

        should_patrol = self.patrol_waypoints and (
            self.get_parameter('start_patrolling').value
            or (self.patrol_on_battery_handoff and self.active_scenario == 'battery_handoff')
        )
        if should_patrol:
            self.state = MissionState.PATROLLING
            goal = self.patrol_waypoints[self.current_waypoint_index]
            self._send_goal(goal, f'patrol:{self.current_waypoint_index}')
            return

        self.state = MissionState.IDLE

    def _send_goal(self, pose_xyyaw: tuple[float, float, float], goal_kind: str) -> None:
        if not self.nav_client.wait_for_server(timeout_sec=0.1):
            self.get_logger().warn('Waiting for NavigateToPose action server...')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = self._make_pose_stamped(pose_xyyaw)

        self._active_goal_kind = goal_kind
        self._goal_sent_at = time.monotonic()
        self._goal_pending = True
        send_future = self.nav_client.send_goal_async(goal_msg)
        send_future.add_done_callback(self._goal_response_cb)
        self.get_logger().info(
            f'Sent {goal_kind} goal: '
            f'x={pose_xyyaw[0]:.2f}, y={pose_xyyaw[1]:.2f}, yaw={pose_xyyaw[2]:.2f}'
        )

    def _goal_response_cb(self, future: Future) -> None:
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            self.get_logger().error(f'Goal rejected: {self._active_goal_kind}')
            self._active_goal_kind = None
            self._active_goal_handle = None
            self._goal_pending = False
            self.state = MissionState.ERROR
            return

        self._goal_pending = False
        self._active_goal_handle = goal_handle
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._goal_result_cb)

    def _goal_result_cb(self, future: Future) -> None:
        result = future.result()
        goal_kind = self._active_goal_kind or 'unknown'
        self._active_goal_kind = None
        self._active_goal_handle = None
        self._goal_pending = False

        if result is None:
            self.get_logger().error(f'No result for goal: {goal_kind}')
            self.state = MissionState.ERROR
            return

        if result.status != 4:
            self.get_logger().warn(f'Goal did not succeed: {goal_kind}, status={result.status}')
            return

        self.get_logger().info(f'Goal succeeded: {goal_kind}')

        if goal_kind.startswith('patrol:') and self.patrol_waypoints:
            self.current_waypoint_index = (
                self.current_waypoint_index + 1
            ) % len(self.patrol_waypoints)
            self._waiting_until = time.monotonic() + self.waypoint_pause_sec
        elif goal_kind == 'charge_wait':
            self.state = MissionState.CHARGING_WAIT
        elif goal_kind.startswith('event:'):
            self.state = MissionState.PATROLLING
            self._waiting_until = time.monotonic() + self.waypoint_pause_sec

    def _has_active_goal(self) -> bool:
        return self._goal_pending or self._active_goal_handle is not None

    def _preempt_active_goal(self, reason: str) -> None:
        if not self._has_active_goal():
            return
        self.get_logger().warn(f'Preempting {self._active_goal_kind} goal: {reason}')
        self._cancel_active_goal()

    def _cancel_active_goal(self) -> None:
        self._goal_pending = False
        if self._active_goal_handle is None:
            self._active_goal_kind = None
            return
        cancel_future = self._active_goal_handle.cancel_goal_async()
        cancel_future.add_done_callback(self._cancel_done_cb)

    def _cancel_done_cb(self, _future: Future) -> None:
        self._active_goal_kind = None
        self._active_goal_handle = None
        self._goal_pending = False

    def _make_pose_stamped(self, pose_xyyaw: tuple[float, float, float]) -> PoseStamped:
        x, y, yaw = pose_xyyaw
        pose = PoseStamped()
        pose.header.frame_id = self.goal_frame
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = 0.0
        pose.pose.orientation.z = math.sin(yaw * 0.5)
        pose.pose.orientation.w = math.cos(yaw * 0.5)
        return pose

    def _publish_status(self) -> None:
        msg = String()
        msg.data = (
            f'robot={self.robot_id},state={self.state.value},'
            f'scenario={self.active_scenario},battery={self.battery_pct:.1f},'
            f'waypoint={self.current_waypoint_index},goal={self._active_goal_kind or ""}'
        )
        self.status_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PatrolNavigationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
