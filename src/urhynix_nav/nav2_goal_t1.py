"""nav2_goal_t1.py — 맵 좌표로 티원(tb3_1)을 Nav2 주행시키는 스크립트 (nav2_goal_v3 티원 이식판).

■ 원본(nav2_goal_v3.py) 대비 바뀐 것 — 티원 3대 즉사 포인트 수정
  1) BasicNavigator(namespace=--robot) + waitUntilNav2Active 제거(티원 AMCL 노드명이 tb3_1_amcl이라
     영원히 대기하는 함정#12 — docs: urhynix-t1-nav2-patrol-drive) → nav_to_pose 액션서버 대기로 대체.
  2) 맵 상수 하드코딩 제거 — 기본 입력이 map 좌표(미터, Unity 2.5D 우클릭 [MapClick] 로그와 동일 단위).
     grid(0~200) 입력이 필요하면 --grid --map-yaml <맵.yaml>로 로봇측 맵 메타에서 변환.
  3) 네임스페이스 프레임/토픽: {robot}/base_footprint, /{robot}/scan (비-ns 로봇은 --robot "" 로 폴백).

■ 유지한 알짜(원본): 무진전 스턱 감지, /scan 트인쪽 번갈이 탈출 기동, 도달불가 사전 스킵,
  도착방향 정책(다음 점/왔던 곳), 취소 레이스 대기, --loop/--laps 순찰.

■ 사용법 (티원, 로봇에서 실행 — nav2 8노드 수동 activate + AMCL 시딩 완료 후)
  python3 nav2_goal_t1.py 1.30 1.25                    # map(1.30, 1.25)m 로 이동
  python3 nav2_goal_t1.py 0.4 0.4 1.3 1.25 --loop      # 두 점 순찰 반복
  python3 nav2_goal_t1.py 100 100 --grid --map-yaml ~/maps/arena_shared.yaml
"""
import sys
import time
import math
import argparse
import re
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav2_simple_commander.robot_navigator import TaskResult

GRID_MAX = 200.0
NAV_TIMEOUT = 90.0     # 초 — 한 구간 초과하면 이동 취소 (무한대기 방지)

# 스턱 감지
STUCK_TIME = 15.0      # 초 — 남은거리가 이 시간 동안 안 줄면 스턱
PROGRESS_EPS = 0.05    # m — 이만큼은 줄어야 '진전'으로 침
MAX_RECOVERIES = 6     # 복구 누적 이 횟수 넘으면 스턱 (보조 신호)

# 스턱 탈출 기동 (뒤로 → 옆으로 비껴 → 재시도, 막히면 반대쪽으로 번갈아)
MAX_ESCAPE = 4
ESCAPE_ANGLE = math.radians(60.0)  # 2026-07-08: 30°는 좁은 아레나서 탈출 부족 — 사용자 지시로 확대
ESCAPE_BACK = 0.15                      # m 후진 — 1.9m 아레나라 원본 0.20에서 축소
ESCAPE_FWD = 0.15                       # m 전진

MIN_BEARING_DIST = 0.05                 # m — 두 점이 이보다 가까우면 현재 heading 유지


def load_map_meta(yaml_path):
    """map_server yaml에서 (origin_x, origin_y, size_m) 추출 — grid 변환용. pgm 크기는 resolution*px 근사 불가라
    grid는 origin+size 정사각 가정(원본 스크립트와 동일 의미론). size_m은 yaml 옆 pgm 헤더에서 읽는다."""
    txt = open(yaml_path).read()
    res = float(re.search(r"resolution:\s*([\d.eE+-]+)", txt).group(1))
    ox, oy = [float(v) for v in re.search(r"origin:\s*\[([^\]]+)\]", txt).group(1).split(",")[:2]]
    pgm = re.search(r"image:\s*(\S+)", txt).group(1)
    import os
    pgm_path = pgm if os.path.isabs(pgm) else os.path.join(os.path.dirname(yaml_path), pgm)
    with open(pgm_path, "rb") as f:
        f.readline()                          # P5
        line = f.readline()
        while line.startswith(b"#"):
            line = f.readline()
        w, h = [int(v) for v in line.split()]
    return ox, oy, max(w, h) * res


def yaw_to_quat(yaw):
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def bearing(fx, fy, tx, ty):
    return math.atan2(ty - fy, tx - fx)


def yaw_from_quat(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class GoToGoal(Node):
    def __init__(self, robot, route_in, route_map, loop, laps=0):
        super().__init__('nav2_goal_t1')
        # 함정#12: 인자 없는 BasicNavigator는 비-ns 액션/amcl을 찾음 → 티원은 namespace 필수.
        self.navigator = BasicNavigator(namespace=robot) if robot else BasicNavigator()
        self.robot = robot
        self.base_frame = f'{robot}/base_footprint' if robot else 'base_footprint'
        self.scan_topic = f'/{robot}/scan' if robot else '/scan'
        self.route_in = route_in            # 입력 그대로 (로그용)
        self.route = route_map              # [(x,y), ...] map 미터
        self.loop = loop
        self.laps = laps
        self.skipped = []
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

    def start_pose(self):
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                t = self.tf_buffer.lookup_transform('map', self.base_frame, rclpy.time.Time())
                return t.transform.translation.x, t.transform.translation.y
            except (LookupException, ConnectivityException, ExtrapolationException):
                rclpy.spin_once(self, timeout_sec=0.1)
        return None

    def current_yaw(self):
        deadline = time.time() + 1.0
        while time.time() < deadline:
            try:
                t = self.tf_buffer.lookup_transform('map', self.base_frame, rclpy.time.Time())
                return yaw_from_quat(t.transform.rotation)
            except (LookupException, ConnectivityException, ExtrapolationException):
                rclpy.spin_once(self, timeout_sec=0.1)
        return None

    def bearing_or(self, fx, fy, tx, ty, fallback):
        if math.hypot(tx - fx, ty - fy) < MIN_BEARING_DIST:
            return fallback if fallback is not None else 0.0
        return bearing(fx, fy, tx, ty)

    def goal_yaw(self, i, came_from, fallback_yaw):
        x, y = self.route[i]
        n = len(self.route)
        if i < n - 1:
            nx, ny = self.route[i + 1]
            return self.bearing_or(x, y, nx, ny, fallback_yaw)
        if self.loop:
            nx, ny = self.route[0]
            return self.bearing_or(x, y, nx, ny, fallback_yaw)
        cx, cy = came_from
        return self.bearing_or(x, y, cx, cy, fallback_yaw)

    def cancel_and_wait(self, cap=1.0):
        self.navigator.cancelTask()
        t0 = time.time()
        while not self.navigator.isTaskComplete() and time.time() - t0 < cap:
            time.sleep(0.05)

    def drive_to(self, goal):
        self.navigator.goToPose(goal)
        last_log = -1.0
        best_dist = float('inf')
        last_progress = 0.0
        while not self.navigator.isTaskComplete():
            feedback = self.navigator.getFeedback()
            if feedback is None:
                time.sleep(0.2)
                continue

            nav_time = Duration.from_msg(feedback.navigation_time).nanoseconds / 1e9
            eta = Duration.from_msg(feedback.estimated_time_remaining).nanoseconds / 1e9
            if nav_time - last_log >= 0.5:
                last_log = nav_time
                self.get_logger().info(
                    f'  이동 중: 남은거리 {feedback.distance_remaining:.2f}m, '
                    f'ETA {eta:.1f}s, 경과 {nav_time:.1f}s, '
                    f'복구 {feedback.number_of_recoveries}회')

            if feedback.distance_remaining < best_dist - PROGRESS_EPS:
                best_dist = feedback.distance_remaining
                last_progress = nav_time
            elif nav_time - last_progress > STUCK_TIME:
                self.cancel_and_wait()
                self.get_logger().warn(f'  {STUCK_TIME:.0f}s 무진전 → 스턱 판단, 취소')
                break
            if feedback.number_of_recoveries >= MAX_RECOVERIES:
                self.cancel_and_wait()
                self.get_logger().warn(f'  복구 {feedback.number_of_recoveries}회 → 스턱 판단, 취소')
                break

            if nav_time > NAV_TIMEOUT:
                self.cancel_and_wait()
                self.get_logger().warn(f'  {NAV_TIMEOUT:.0f}s 초과 → 이동 취소')
                break
            time.sleep(0.2)

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('  도착 성공')
            return True
        if result == TaskResult.CANCELED:
            self.get_logger().warn('  이동 취소됨')
            return False
        self.get_logger().error('  이동 실패')
        return False

    def do_behavior(self, name, start):
        start()
        while not self.navigator.isTaskComplete():
            time.sleep(0.1)
        if self.navigator.getResult() != TaskResult.SUCCEEDED:
            self.get_logger().warn(f'    {name} 동작 실패/취소')

    def escape_maneuver(self, angle):
        side = '오른쪽' if angle < 0 else '왼쪽'
        self.get_logger().info(
            f'  탈출기동: 뒤로 {ESCAPE_BACK:.2f}m → {side} {abs(math.degrees(angle)):.0f}° → 앞 {ESCAPE_FWD:.2f}m')
        self.do_behavior('backup', lambda: self.navigator.backup(backup_dist=ESCAPE_BACK, backup_speed=0.05))
        self.do_behavior('spin', lambda: self.navigator.spin(spin_dist=angle))
        self.do_behavior('drive', lambda: self.navigator.driveOnHeading(dist=ESCAPE_FWD, speed=0.05))

    def is_reachable(self, goal):
        start = PoseStamped()
        start.header.frame_id = 'map'
        start.header.stamp = self.navigator.get_clock().now().to_msg()
        try:
            path = self.navigator.getPath(start, goal, use_start=False)
        except Exception as e:
            self.get_logger().warn(f'  경로 확인 실패({e}) → 확인 생략하고 시도')
            return True
        return path is not None and len(path.poses) > 0

    def _get_scan(self, timeout=2.0):
        qos = QoSProfile(depth=1)
        qos.reliability = QoSReliabilityPolicy.BEST_EFFORT
        qos.durability = QoSDurabilityPolicy.VOLATILE
        holder = {}
        sub = self.create_subscription(LaserScan, self.scan_topic,
                                       lambda m: holder.setdefault('m', m), qos)
        deadline = time.time() + timeout
        while 'm' not in holder and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.destroy_subscription(sub)
        return holder.get('m')

    def _sector_min(self, scan, deg_lo, deg_hi):
        lo, hi = math.radians(deg_lo), math.radians(deg_hi)
        best = float('inf')
        for k, r in enumerate(scan.ranges):
            ang = scan.angle_min + k * scan.angle_increment
            if lo <= ang <= hi and scan.range_min <= r <= scan.range_max and math.isfinite(r):
                best = min(best, r)
        return best

    def pick_open_side(self):
        scan = self._get_scan()
        if scan is None:
            self.get_logger().warn(f'  {self.scan_topic} 못 받음 → 탈출 방향 기본(오른쪽)')
            return -1
        left = self._sector_min(scan, 30, 90)
        right = self._sector_min(scan, -90, -30)
        side = 1 if left > right else -1
        self.get_logger().info(
            f'  트인쪽 판정: 좌 {left:.2f}m vs 우 {right:.2f}m → '
            f'{"왼쪽" if side > 0 else "오른쪽"}부터 탈출')
        return side

    def navigate_with_recovery(self, goal):
        if self.drive_to(goal):
            return True
        side = self.pick_open_side()
        for attempt in range(MAX_ESCAPE):
            self.get_logger().warn(
                f'  탈출 {attempt + 1}/{MAX_ESCAPE}: {"오른쪽" if side < 0 else "왼쪽"}으로 비껴 재시도')
            self.escape_maneuver(side * ESCAPE_ANGLE)
            if self.drive_to(goal):
                return True
            side *= -1
        return False

    def wait_nav2_ready(self, period=10.0):
        """함정#12 대응: waitUntilNav2Active 대신 navigate_to_pose 액션서버만 기다린다.
        (8노드 lifecycle activate는 스킬 절차에서 이미 수동 확인 — amcl 상태조회는 티원 노드명과 안 맞음.)"""
        waited = 0
        while not self.navigator.nav_to_pose_client.wait_for_server(timeout_sec=period):
            waited += int(period)
            self.get_logger().info(f'navigate_to_pose 액션서버 대기 중... ({waited}s 경과) — nav2 8노드 activate 확인 필요')
        self.get_logger().info('navigate_to_pose 액션서버 확인 — 주행 시작')

    def run(self):
        self.wait_nav2_ready()
        start = self.start_pose()
        if start is None:
            self.get_logger().error(
                f'localize 안 됨 (map→{self.base_frame} TF 없음) → 주행 중단. '
                'AMCL 초기포즈 시딩(urhynix-t1-amcl-saved-map) 후 다시 실행하세요.')
            return

        n = len(self.route)
        lap = 0
        while True:
            for i in range(n):
                x, y = self.route[i]
                if i > 0:
                    came_from = self.route[i - 1]
                elif lap > 0:
                    came_from = self.route[-1]
                else:
                    came_from = start if start is not None else (x, y)

                fallback_yaw = self.current_yaw()
                yaw = self.goal_yaw(i, came_from, fallback_yaw)
                qz, qw = yaw_to_quat(yaw)

                goal = PoseStamped()
                goal.header.frame_id = 'map'
                goal.header.stamp = self.navigator.get_clock().now().to_msg()
                goal.pose.position.x = x
                goal.pose.position.y = y
                goal.pose.orientation.z = qz
                goal.pose.orientation.w = qw

                ix, iy = self.route_in[i]
                self.get_logger().info(
                    f'[{i + 1}/{n}] 입력({ix},{iy}) -> 맵({x:.3f},{y:.3f}) '
                    f'도착방향 {math.degrees(yaw):.0f}°')

                if not self.is_reachable(goal):
                    self.get_logger().warn(f'[{i + 1}/{n}] 도달 불가(경로 없음) → 사전 스킵')
                    self.skipped.append((ix, iy))
                    continue

                if not self.navigate_with_recovery(goal):
                    self.get_logger().warn(
                        f'[{i + 1}/{n}] 탈출 {MAX_ESCAPE}회 모두 실패 → 스킵')
                    self.skipped.append((ix, iy))

            lap += 1
            if not self.loop:
                break
            if self.laps > 0 and lap >= self.laps:
                self.get_logger().info(f'루프 {lap}바퀴 완료 (--laps {self.laps}) → 종료')
                break
            self.get_logger().info(f'루프 {lap}바퀴 완료 → 재시작')

        if self.skipped:
            self.get_logger().warn(f'스킵된 지점 {len(self.skipped)}개: {self.skipped}')
        self.get_logger().info('전체 경로 완료')


def main():
    global NAV_TIMEOUT, STUCK_TIME, MAX_ESCAPE, ESCAPE_ANGLE, ESCAPE_BACK, ESCAPE_FWD

    p = argparse.ArgumentParser(
        description='티원 Nav2 목표 주행 — 기본 입력은 map 좌표(m, Unity [MapClick]과 동일). '
                    '--grid --map-yaml로 grid(0~200) 변환 모드.')
    p.add_argument('coords', nargs='+', type=float, help='x1 y1 [x2 y2 ...]')
    p.add_argument('--robot', default='tb3_1', help='네임스페이스 (기본 tb3_1, 비-ns 로봇은 "")')
    p.add_argument('--grid', action='store_true', help='좌표를 grid(0~200)로 해석 (--map-yaml 필수)')
    p.add_argument('--map-yaml', help='grid 변환용 map_server yaml 경로')
    p.add_argument('--loop', action='store_true', help='경로 반복 (Ctrl+C까지)')
    p.add_argument('--laps', type=int, default=0, metavar='N', help='루프 바퀴 수 (0=무한)')
    p.add_argument('--timeout', type=float, default=NAV_TIMEOUT, metavar='초')
    p.add_argument('--stuck-time', type=float, default=STUCK_TIME, metavar='초')
    p.add_argument('--max-escape', type=int, default=MAX_ESCAPE, metavar='N')
    p.add_argument('--escape-angle', type=float, default=math.degrees(ESCAPE_ANGLE), metavar='도')
    p.add_argument('--escape-back', type=float, default=ESCAPE_BACK, metavar='m')
    p.add_argument('--escape-fwd', type=float, default=ESCAPE_FWD, metavar='m')
    args = p.parse_args()

    if len(args.coords) % 2 != 0:
        p.error('좌표는 x y 쌍이어야 합니다 (개수가 짝수)')
    route_in = list(zip(args.coords[0::2], args.coords[1::2]))

    if args.grid:
        if not args.map_yaml:
            p.error('--grid 모드는 --map-yaml 필수')
        ox, oy, size_m = load_map_meta(args.map_yaml)
        for gx, gy in route_in:
            if not (0 <= gx <= GRID_MAX and 0 <= gy <= GRID_MAX):
                p.error('grid 좌표는 0~%d 범위' % int(GRID_MAX))
        route_map = [(ox + (gx / GRID_MAX) * size_m, oy + (gy / GRID_MAX) * size_m)
                     for gx, gy in route_in]
        print(f'grid 변환: origin=({ox:.3f},{oy:.3f}) size={size_m:.2f}m ({args.map_yaml})')
    else:
        route_map = route_in                 # map 미터 그대로

    NAV_TIMEOUT = args.timeout
    STUCK_TIME = args.stuck_time
    MAX_ESCAPE = args.max_escape
    ESCAPE_ANGLE = math.radians(args.escape_angle)
    ESCAPE_BACK = args.escape_back
    ESCAPE_FWD = args.escape_fwd
    loop = args.loop or args.laps > 0

    rclpy.init()
    node = GoToGoal(args.robot, route_in, route_map, loop, laps=args.laps)
    try:
        node.run()
    except KeyboardInterrupt:
        node.get_logger().warn('사용자 중단(Ctrl+C)')
    finally:
        if not node.navigator.isTaskComplete():
            node.navigator.cancelTask()
            node.get_logger().warn('남은 goal 취소 → 로봇 정지')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
