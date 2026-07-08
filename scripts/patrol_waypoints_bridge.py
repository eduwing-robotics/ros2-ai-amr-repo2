#!/usr/bin/env python3
# patrol_waypoints_bridge.py — Unity ControlRoom이 발행한 /<robot>/goal_pose(PoseStamped)와
# /<robot>/patrol_waypoints(PoseArray)를 받아 Nav2 goToPose/FollowWaypoints로 실행하는 로봇측 브리지.
# ROS-TCP는 액션 미지원이라 이 노드가 다리 역할.
# ★구독은 *전용* SingleThreadedExecutor로 백그라운드 spin, BasicNavigator는 메인에서 실행.
#   rclpy.spin()도 BasicNavigator도 기본값이 전역 executor라 같이 쓰면 "Executor is already spinning"으로
#   터짐 → 리스너에 전용 executor를 줘서 전역과 분리(2026-06-25 수정).
# 로봇/Nav2 PC(같은 저장맵+AMCL, 도메인 210)에서 실행:
#   python3 patrol_waypoints_bridge.py --robot tb3_1
import argparse
import queue
import threading
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


class CmdListener(Node):
    """Unity 명령을 구독해 큐에 적재만 한다(Nav2 호출은 메인 스레드가)."""

    def __init__(self, robot, q):
        super().__init__('patrol_waypoints_bridge')
        self.q = q
        self.create_subscription(PoseStamped, f'/{robot}/goal_pose', self.on_goal, 10)
        self.create_subscription(PoseArray, f'/{robot}/patrol_waypoints', self.on_route, 10)
        self.get_logger().info(f'구독: /{robot}/goal_pose, /{robot}/patrol_waypoints — Unity 명령 대기')

    def on_goal(self, msg: PoseStamped):
        self.q.put(('goal', msg))
        self.get_logger().info(
            f'goal_pose 수신 ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f}) → 큐')

    def on_route(self, msg: PoseArray):
        if not msg.poses:
            self.get_logger().warn('빈 PoseArray 수신 — 무시')
            return
        self.q.put(('route', msg))
        self.get_logger().info(f'순찰 {len(msg.poses)}점 수신 → 큐')


def to_stamped(nav, p, frame):
    ps = PoseStamped()
    ps.header.frame_id = frame or 'map'
    ps.header.stamp = nav.get_clock().now().to_msg()
    ps.pose = p
    return ps


def wait_result(nav, log, label):
    while not nav.isTaskComplete():
        fb = nav.getFeedback()
        if fb and hasattr(fb, 'current_waypoint'):
            log.info(f'{label}: 웨이포인트 #{fb.current_waypoint + 1}', throttle_duration_sec=2.0)
        time.sleep(0.2)
    r = nav.getResult()
    if r == TaskResult.SUCCEEDED:
        log.info(f'{label}: 성공')
    elif r == TaskResult.CANCELED:
        log.warn(f'{label}: 취소됨')
    else:
        log.error(f'{label}: 실패 result={r}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--robot', default='tb3_1')
    a = ap.parse_args()
    rclpy.init()

    q = queue.Queue()
    listener = CmdListener(a.robot, q)
    log = listener.get_logger()
    # 구독 노드는 *전용* executor로 백그라운드 spin. rclpy.spin()은 전역 executor를 잡는데
    # BasicNavigator도 전역 executor를 써서 충돌("Executor is already spinning") → 전용 executor로 분리.
    le = SingleThreadedExecutor()
    le.add_node(listener)
    threading.Thread(target=le.spin, daemon=True).start()

    # namespace= 필수: 미지정 시 /navigate_to_pose(비ns)를 찾아 이 프로젝트의 /<robot>/navigate_to_pose와
    # 어긋난다. waitUntilNav2Active()도 안 씀 — 기본 localizer='amcl'이 <robot>/amcl/get_state를 찾는데
    # 이 프로젝트의 AMCL은 노드명 <robot>_amcl(언더스코어, PushRosNamespace 미사용 — tf 리매핑 충돌 회피,
    # urhynix-t1-nav2-lifecycle-abi 참고)이라 매칭 불가 → 액션서버 자체 대기로 대체.
    nav = BasicNavigator(namespace=a.robot)
    log.info('Nav2 액션서버(navigate_to_pose) 대기...')
    nav.nav_to_pose_client.wait_for_server()
    log.info('Nav2 활성 확인 — 명령 처리 시작')

    try:
        while rclpy.ok():
            try:
                kind, msg = q.get(timeout=0.5)
            except queue.Empty:
                continue
            if kind == 'goal':
                msg.header.stamp = nav.get_clock().now().to_msg()
                if not msg.header.frame_id:
                    msg.header.frame_id = 'map'
                log.info(f'goToPose 시작 ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})')
                nav.goToPose(msg)
                wait_result(nav, log, 'goToPose')
            else:
                goals = [to_stamped(nav, p, msg.header.frame_id) for p in msg.poses]
                log.info(f'FollowWaypoints 시작 ({len(goals)}점)')
                nav.followWaypoints(goals)
                wait_result(nav, log, 'FollowWaypoints')
    except KeyboardInterrupt:
        pass
    finally:
        listener.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
