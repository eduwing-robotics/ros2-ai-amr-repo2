import sys
import time
import math
import argparse
import threading
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid
from sensor_msgs.msg import LaserScan
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav2_simple_commander.robot_navigator import TaskResult

# 좌표계 — 기본값(폴백). --map <map.yaml>을 주면 load_map_frame()이 덮어씀.
MAP_ORIGIN_X = -0.737
MAP_ORIGIN_Y = -2.118
MAP_ORIGIN_YAW = 0.0   # rad — 맵 origin 회전각 (map.yaml origin[2])
MAP_SIZE_X = 2.8       # m — 맵 가로 물리크기 (= 폭px * resolution)
MAP_SIZE_Y = 2.8       # m — 맵 세로 물리크기 (= 높이px * resolution)
GRID_MAX = 200.0       # grid 좌표 범위 0~200 (맵과 무관한 고정 관례)
NAV_TIMEOUT = 90.0     # 초 — 한 구간 초과하면 이동 취소 (무한대기 방지)

# 스턱 감지
STUCK_TIME = 15.0      # 초 — 남은거리가 이 시간 동안 안 줄면 스턱
PROGRESS_EPS = 0.05    # m — 이만큼은 줄어야 '진전'으로 침
MAX_RECOVERIES = 6     # 복구 누적 이 횟수 넘으면 스턱 (보조 신호)

# 스턱 탈출 기동 (뒤로 → 옆으로 비껴 → 재시도, 막히면 반대쪽으로 번갈아)
MAX_ESCAPE = 4                          # 탈출 재시도 횟수 (오→왼→오→왼)
ESCAPE_ANGLE = math.radians(30.0)       # 옆으로 비끼는 회전각 ±30°
ESCAPE_BACK = 0.20                      # m 후진
ESCAPE_FWD = 0.20                       # m 전진(옆으로 벗어남)

MIN_BEARING_DIST = 0.05                 # m — 두 점이 이보다 가까우면 방향 계산 대신 현재 heading 유지


def grid_to_map(gx, gy):
    lx = (gx / GRID_MAX) * MAP_SIZE_X          # 맵원점 기준 로컬 오프셋
    ly = (gy / GRID_MAX) * MAP_SIZE_Y
    c, s = math.cos(MAP_ORIGIN_YAW), math.sin(MAP_ORIGIN_YAW)
    real_x = MAP_ORIGIN_X + lx * c - ly * s    # origin θ 회전 반영
    real_y = MAP_ORIGIN_Y + lx * s + ly * c
    return real_x, real_y


def _image_size(path):
    """맵 이미지(.pgm/.pgm-ascii/.png)에서 (width, height)픽셀 읽기."""
    with open(path, 'rb') as f:
        head = f.read(8)
        if head[:2] in (b'P5', b'P2'):          # PGM (binary/ascii)
            f.seek(2)

            def next_token():
                tok = b''
                while True:
                    c = f.read(1)
                    if not c:
                        return tok
                    if c == b'#':               # 주석: 줄 끝까지 skip
                        while c and c not in b'\r\n':
                            c = f.read(1)
                        continue
                    if c.isspace():
                        if tok:
                            return tok
                        continue
                    tok += c
            w = int(next_token())
            h = int(next_token())
            return w, h
        if head == b'\x89PNG\r\n\x1a\n':         # PNG: IHDR에 크기
            import struct
            f.seek(16)
            w, h = struct.unpack('>II', f.read(8))
            return w, h
    raise ValueError(f'지원 안 하는 이미지 포맷: {path} (PGM/PNG만)')


def load_map_frame(yaml_path):
    """map.yaml + 이미지에서 origin/resolution/크기를 읽어 좌표계 전역을 설정."""
    global MAP_ORIGIN_X, MAP_ORIGIN_Y, MAP_ORIGIN_YAW, MAP_SIZE_X, MAP_SIZE_Y
    import os
    image = resolution = origin = None
    with open(yaml_path) as f:
        for line in f:
            line = line.split('#', 1)[0].strip()
            if line.startswith('image:'):
                image = line.split(':', 1)[1].strip().strip('"\'')
            elif line.startswith('resolution:'):
                resolution = float(line.split(':', 1)[1])
            elif line.startswith('origin:'):
                vals = line.split(':', 1)[1].strip().strip('[]')
                origin = [float(v) for v in vals.split(',')]
    if image is None or resolution is None or origin is None:
        raise ValueError('map.yaml에 image/resolution/origin이 모두 필요합니다')

    img_path = image if os.path.isabs(image) else os.path.join(os.path.dirname(yaml_path), image)
    w, h = _image_size(img_path)
    MAP_ORIGIN_X, MAP_ORIGIN_Y = origin[0], origin[1]
    MAP_ORIGIN_YAW = origin[2] if len(origin) > 2 else 0.0
    MAP_SIZE_X = w * resolution
    MAP_SIZE_Y = h * resolution
    return {'origin': (MAP_ORIGIN_X, MAP_ORIGIN_Y), 'yaw': MAP_ORIGIN_YAW, 'res': resolution,
            'px': (w, h), 'size': (MAP_SIZE_X, MAP_SIZE_Y)}


def yaw_to_quat(yaw):
    """yaw(rad) -> (z, w) 쿼터니언 (평면 회전)."""
    return math.sin(yaw / 2.0), math.cos(yaw / 2.0)


def bearing(fx, fy, tx, ty):
    """(fx,fy)에서 (tx,ty)를 바라보는 방향 yaw."""
    return math.atan2(ty - fy, tx - fx)


def yaw_from_quat(q):
    """쿼터니언 -> yaw(rad) (평면)."""
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class GoToGoal(Node):
    def __init__(self, route_grid, loop, map_info=None, laps=0):
        super().__init__('go_to_goal')
        self.navigator = BasicNavigator()
        self.route_grid = route_grid                                # [(gx,gy), ...]
        self.route = [grid_to_map(gx, gy) for gx, gy in route_grid]  # [(x,y), ...] map
        self.loop = loop
        self.laps = laps                                            # 루프 바퀴 수 (0=무한)
        self.map_info = map_info                                     # --map으로 읽은 좌표계 (없으면 None)
        self.skipped = []                                           # 탈출 실패로 스킵된 지점
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

    # --- --map 파일과 Nav2 실제 맵(/map)이 같은지 확인 ---
    def check_map_match(self):
        if self.map_info is None:
            return                                  # --map 미지정이면 비교 불가
        qos = QoSProfile(depth=1)
        qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL   # /map은 latched
        qos.reliability = QoSReliabilityPolicy.RELIABLE
        holder = {}
        sub = self.create_subscription(
            OccupancyGrid, '/map', lambda m: holder.setdefault('m', m), qos)
        deadline = time.time() + 5.0
        while 'm' not in holder and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.destroy_subscription(sub)
        if 'm' not in holder:
            self.get_logger().warn('/map을 못 받아 맵 일치 확인 생략 (Nav2 map_server 확인)')
            return

        info = holder['m'].info
        exp_ox, exp_oy = self.map_info['origin']
        exp_res = self.map_info['res']
        exp_w, exp_h = self.map_info['px']
        dif = []
        if abs(info.resolution - exp_res) > 1e-3:
            dif.append(f'resolution {info.resolution:.3f} vs {exp_res:.3f}')
        if info.width != exp_w or info.height != exp_h:
            dif.append(f'크기 {info.width}x{info.height}px vs {exp_w}x{exp_h}px')
        if (abs(info.origin.position.x - exp_ox) > 1e-2 or
                abs(info.origin.position.y - exp_oy) > 1e-2):
            dif.append(f'origin ({info.origin.position.x:.3f},{info.origin.position.y:.3f}) '
                       f'vs ({exp_ox:.3f},{exp_oy:.3f})')
        exp_yaw = self.map_info.get('yaw', 0.0)
        map_yaw = yaw_from_quat(info.origin.orientation)
        if abs(math.atan2(math.sin(map_yaw - exp_yaw), math.cos(map_yaw - exp_yaw))) > 1e-2:
            dif.append(f'origin θ {map_yaw:.3f} vs {exp_yaw:.3f} rad')
        if dif:
            self.get_logger().warn(
                '⚠️ Nav2 실제 맵과 --map 파일이 다릅니다! 좌표가 틀어질 수 있음:\n    '
                + '\n    '.join(dif))
        else:
            self.get_logger().info('Nav2 맵과 --map 파일 일치 확인 ✅')

    # --- 현재 위치(왔던 곳 계산용) ---
    def start_pose(self):
        """map->base_footprint TF에서 현재 위치. 5초 내 못 읽으면 None."""
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
                return t.transform.translation.x, t.transform.translation.y
            except (LookupException, ConnectivityException, ExtrapolationException):
                rclpy.spin_once(self, timeout_sec=0.1)
        return None

    # --- 현재 heading (퇴화 bearing fallback용) ---
    def current_yaw(self):
        """map->base_footprint TF에서 현재 yaw. 1초 내 못 읽으면 None."""
        deadline = time.time() + 1.0
        while time.time() < deadline:
            try:
                t = self.tf_buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time())
                return yaw_from_quat(t.transform.rotation)
            except (LookupException, ConnectivityException, ExtrapolationException):
                rclpy.spin_once(self, timeout_sec=0.1)
        return None

    # --- 두 점이 너무 가까우면(퇴화) 방향 대신 fallback 유지 ---
    def bearing_or(self, fx, fy, tx, ty, fallback):
        if math.hypot(tx - fx, ty - fy) < MIN_BEARING_DIST:
            return fallback if fallback is not None else 0.0
        return bearing(fx, fy, tx, ty)

    # --- 도착 방향 정책 ---
    def goal_yaw(self, i, came_from, fallback_yaw):
        """i번째 목표에 도착했을 때 바라볼 yaw.
        다음 목적지 있음/루프 -> 갈 방향, 최종 도착 -> 왔던 곳.
        두 점이 너무 가까우면(퇴화) 현재 heading(fallback_yaw) 유지."""
        x, y = self.route[i]
        n = len(self.route)
        if i < n - 1:                       # 갈 곳이 더 있음
            nx, ny = self.route[i + 1]
            return self.bearing_or(x, y, nx, ny, fallback_yaw)    # 다음 점(갈 방향)
        if self.loop:                       # 루프: 마지막도 처음을 향함
            nx, ny = self.route[0]
            return self.bearing_or(x, y, nx, ny, fallback_yaw)
        cx, cy = came_from                  # 최종 도착: 왔던 곳
        return self.bearing_or(x, y, cx, cy, fallback_yaw)

    # --- 취소 요청 후 실제 완료까지 짧게 대기 (getResult 레이스 방지) ---
    def cancel_and_wait(self, cap=1.0):
        self.navigator.cancelTask()
        t0 = time.time()
        while not self.navigator.isTaskComplete() and time.time() - t0 < cap:
            time.sleep(0.05)

    # --- 한 구간 주행 (피드백 루프 + 스턱 감지) ---
    def drive_to(self, goal):
        """True=성공, False=실패/취소/스턱."""
        self.navigator.goToPose(goal)
        last_log = -1.0        # 시작하자마자 첫 로그
        best_dist = float('inf')
        last_progress = 0.0    # 마지막으로 남은거리가 줄어든 시점(nav_time)
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

            # 스턱 감지 (a) 무진전: 남은거리가 STUCK_TIME 동안 안 줄어듦
            if feedback.distance_remaining < best_dist - PROGRESS_EPS:
                best_dist = feedback.distance_remaining
                last_progress = nav_time
            elif nav_time - last_progress > STUCK_TIME:
                self.cancel_and_wait()
                self.get_logger().warn(f'  {STUCK_TIME:.0f}s 무진전 → 스턱 판단, 취소')
                break
            # 스턱 감지 (b) 복구 누적 임계
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

    # --- 복구 동작(backup/spin/driveOnHeading) 1개 실행 후 완료 대기 ---
    def do_behavior(self, name, start):
        start()
        while not self.navigator.isTaskComplete():
            time.sleep(0.1)
        if self.navigator.getResult() != TaskResult.SUCCEEDED:
            self.get_logger().warn(f'    {name} 동작 실패/취소')

    # --- 스턱 탈출 기동: 뒤로 → angle 회전 → 전진 (옆으로 비껴남) ---
    def escape_maneuver(self, angle):
        side = '오른쪽' if angle < 0 else '왼쪽'
        self.get_logger().info(
            f'  탈출기동: 뒤로 {ESCAPE_BACK:.2f}m → {side} {abs(math.degrees(angle)):.0f}° → 앞 {ESCAPE_FWD:.2f}m')
        self.do_behavior('backup', lambda: self.navigator.backup(backup_dist=ESCAPE_BACK, backup_speed=0.05))
        self.do_behavior('spin', lambda: self.navigator.spin(spin_dist=angle))
        self.do_behavior('drive', lambda: self.navigator.driveOnHeading(dist=ESCAPE_FWD, speed=0.05))

    # --- 목표 도달가능 사전확인 (플래너로 경로 존재 여부) ---
    def is_reachable(self, goal):
        start = PoseStamped()
        start.header.frame_id = 'map'
        start.header.stamp = self.navigator.get_clock().now().to_msg()
        try:
            path = self.navigator.getPath(start, goal, use_start=False)   # 현재 pose에서 경로계획
        except Exception as e:
            self.get_logger().warn(f'  경로 확인 실패({e}) → 확인 생략하고 시도')
            return True             # 확인 자체가 안 되면 막지 말고 시도
        return path is not None and len(path.poses) > 0

    # --- /scan으로 좌/우 중 더 트인(가까운 벽이 먼) 쪽 고르기 ---
    def _get_scan(self, timeout=2.0):
        qos = QoSProfile(depth=1)
        qos.reliability = QoSReliabilityPolicy.BEST_EFFORT   # 센서 QoS
        qos.durability = QoSDurabilityPolicy.VOLATILE
        holder = {}
        sub = self.create_subscription(LaserScan, '/scan',
                                       lambda m: holder.setdefault('m', m), qos)
        deadline = time.time() + timeout
        while 'm' not in holder and time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.destroy_subscription(sub)
        return holder.get('m')

    def _sector_min(self, scan, deg_lo, deg_hi):
        """[deg_lo,deg_hi]° 섹터의 최소 유효거리 (없으면 inf)."""
        lo, hi = math.radians(deg_lo), math.radians(deg_hi)
        best = float('inf')
        for k, r in enumerate(scan.ranges):
            ang = scan.angle_min + k * scan.angle_increment
            if lo <= ang <= hi and scan.range_min <= r <= scan.range_max and math.isfinite(r):
                best = min(best, r)
        return best

    def pick_open_side(self):
        """탈출 첫 방향: +1(왼쪽)/-1(오른쪽) 중 가까운 벽이 더 먼 쪽. /scan 없으면 -1."""
        scan = self._get_scan()
        if scan is None:
            self.get_logger().warn('  /scan 못 받음 → 탈출 방향 기본(오른쪽)')
            return -1
        left = self._sector_min(scan, 30, 90)      # 왼쪽 섹터 최소거리
        right = self._sector_min(scan, -90, -30)   # 오른쪽 섹터 최소거리
        side = 1 if left > right else -1
        self.get_logger().info(
            f'  트인쪽 판정: 좌 {left:.2f}m vs 우 {right:.2f}m → '
            f'{"왼쪽" if side > 0 else "오른쪽"}부터 탈출')
        return side

    # --- 목표 주행 + 스턱 시 번갈이 탈출 재시도 (트인 쪽부터, 이후 번갈아) ---
    def navigate_with_recovery(self, goal):
        if self.drive_to(goal):
            return True
        side = self.pick_open_side()   # /scan으로 트인 쪽부터, 막히면 반대쪽으로 번갈아
        for attempt in range(MAX_ESCAPE):
            self.get_logger().warn(
                f'  탈출 {attempt + 1}/{MAX_ESCAPE}: {"오른쪽" if side < 0 else "왼쪽"}으로 비껴 재시도')
            self.escape_maneuver(side * ESCAPE_ANGLE)
            if self.drive_to(goal):
                return True
            side *= -1
        return False

    # --- Nav2 활성화 대기 (무한 대기하되 60초마다 로그) ---
    def wait_nav2_active(self, period=60.0):
        done = threading.Event()

        def _wait():
            self.navigator.waitUntilNav2Active()
            done.set()

        threading.Thread(target=_wait, daemon=True).start()
        waited = 0
        while not done.wait(timeout=period):
            waited += int(period)
            self.get_logger().info(f'Nav2 활성화 대기 중... ({waited}s 경과)')
        self.get_logger().info('Nav2 활성화됨')

    # --- 전체 경로 실행 ---
    def run(self):
        self.wait_nav2_active()
        self.check_map_match()      # --map과 Nav2 실제 맵 일치 확인
        start = self.start_pose()
        if start is None:
            self.get_logger().error(
                'localize 안 됨 (map→base_footprint TF 없음) → 주행 중단. '
                'RViz "2D Pose Estimate"로 초기 위치를 지정한 뒤 다시 실행하세요.')
            return

        n = len(self.route)
        lap = 0
        while True:
            for i in range(n):
                x, y = self.route[i]
                # 왔던 곳: 직전 웨이포인트, 첫 점이면 로봇 출발 위치
                if i > 0:
                    came_from = self.route[i - 1]
                elif lap > 0:
                    came_from = self.route[-1]
                else:
                    came_from = start if start is not None else (x, y)

                fallback_yaw = self.current_yaw()   # 퇴화 시 유지할 현재 heading
                yaw = self.goal_yaw(i, came_from, fallback_yaw)
                qz, qw = yaw_to_quat(yaw)

                goal = PoseStamped()
                goal.header.frame_id = 'map'
                goal.header.stamp = self.navigator.get_clock().now().to_msg()
                goal.pose.position.x = x
                goal.pose.position.y = y
                goal.pose.orientation.z = qz
                goal.pose.orientation.w = qw

                gx, gy = self.route_grid[i]
                self.get_logger().info(
                    f'[{i + 1}/{n}] 그리드({gx},{gy}) -> 맵({x:.3f},{y:.3f}) '
                    f'도착방향 {math.degrees(yaw):.0f}°')

                if not self.is_reachable(goal):
                    self.get_logger().warn(f'[{i + 1}/{n}] 도달 불가(경로 없음) → 사전 스킵')
                    self.skipped.append((gx, gy))
                    continue

                if not self.navigate_with_recovery(goal):
                    self.get_logger().warn(
                        f'[{i + 1}/{n}] 탈출 {MAX_ESCAPE}회 모두 실패 → 스킵')
                    self.skipped.append((gx, gy))

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
        description='Nav2 grid 목표 주행 (피드백 로그 + 스턱 감지 + 번갈이 탈출).')
    p.add_argument('coords', nargs='+', type=float,
                   help='목표 좌표 x1 y1 [x2 y2 ...] (grid 0~%d)' % int(GRID_MAX))
    p.add_argument('--map', dest='map_path', metavar='map.yaml',
                   help='map.yaml에서 좌표계(origin/resolution/크기) 로드')
    p.add_argument('--loop', action='store_true', help='경로 반복 (Ctrl+C까지)')
    p.add_argument('--laps', type=int, default=0, metavar='N',
                   help='루프 바퀴 수 (0=무한, 지정 시 --loop 자동)')
    p.add_argument('--timeout', type=float, default=NAV_TIMEOUT, metavar='초',
                   help='구간 타임아웃 (기본 %g)' % NAV_TIMEOUT)
    p.add_argument('--stuck-time', type=float, default=STUCK_TIME, metavar='초',
                   help='무진전 스턱 판정 시간 (기본 %g)' % STUCK_TIME)
    p.add_argument('--max-escape', type=int, default=MAX_ESCAPE, metavar='N',
                   help='탈출 재시도 횟수 (기본 %d)' % MAX_ESCAPE)
    p.add_argument('--escape-angle', type=float, default=math.degrees(ESCAPE_ANGLE), metavar='도',
                   help='탈출 회전각(도) (기본 %g)' % math.degrees(ESCAPE_ANGLE))
    p.add_argument('--escape-back', type=float, default=ESCAPE_BACK, metavar='m',
                   help='탈출 후진거리 (기본 %g)' % ESCAPE_BACK)
    p.add_argument('--escape-fwd', type=float, default=ESCAPE_FWD, metavar='m',
                   help='탈출 전진거리 (기본 %g)' % ESCAPE_FWD)
    args = p.parse_args()

    # 좌표 검증 (짝수 개수 + 범위)
    if len(args.coords) % 2 != 0:
        p.error('좌표는 x y 쌍이어야 합니다 (개수가 짝수)')
    route = list(zip(args.coords[0::2], args.coords[1::2]))
    for gx, gy in route:
        if not (0 <= gx <= GRID_MAX and 0 <= gy <= GRID_MAX):
            p.error('좌표는 0~%d 범위여야 합니다' % int(GRID_MAX))

    # 튜닝값을 전역에 반영 (메서드들이 참조)
    NAV_TIMEOUT = args.timeout
    STUCK_TIME = args.stuck_time
    MAX_ESCAPE = args.max_escape
    ESCAPE_ANGLE = math.radians(args.escape_angle)
    ESCAPE_BACK = args.escape_back
    ESCAPE_FWD = args.escape_fwd
    loop = args.loop or args.laps > 0

    # 좌표계: map 파일에서 읽기 (없으면 기본값 폴백)
    map_info = None
    if args.map_path:
        try:
            map_info = load_map_frame(args.map_path)
            print(f'[map] {args.map_path} → origin={map_info["origin"]}, res={map_info["res"]}, '
                  f'px={map_info["px"]}, size={map_info["size"]}')
        except Exception as e:
            p.error('map 파일 로드 실패: %s' % e)
    else:
        print(f'[map] --map 미지정 → 기본 좌표계 사용 '
              f'(origin=({MAP_ORIGIN_X},{MAP_ORIGIN_Y}), size=({MAP_SIZE_X},{MAP_SIZE_Y}))')

    rclpy.init()
    node = GoToGoal(route, loop, map_info=map_info, laps=args.laps)
    try:
        node.run()
    except KeyboardInterrupt:
        node.get_logger().warn('사용자 중단(Ctrl+C)')
    finally:
        # 진행 중인 goal이 남아 있으면 안전하게 취소 (로봇 계속 이동 방지)
        if not node.navigator.isTaskComplete():
            node.navigator.cancelTask()
            node.get_logger().warn('남은 goal 취소 → 로봇 정지')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
