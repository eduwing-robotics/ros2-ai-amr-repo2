#!/usr/bin/env python3
# patrol_waypoints_bridge.py — Unity ControlRoom이 발행한 /<robot>/goal_pose(PoseStamped)와
# /<robot>/patrol_waypoints(PoseArray)를 받아 Nav2 goToPose/FollowWaypoints로 실행하는 로봇측 브리지.
# ROS-TCP는 액션 미지원이라 이 노드가 다리 역할.
# ★구독은 *전용* SingleThreadedExecutor로 백그라운드 spin, BasicNavigator는 메인에서 실행.
#   rclpy.spin()도 BasicNavigator도 기본값이 전역 executor라 같이 쓰면 "Executor is already spinning"으로
#   터짐 → 리스너에 전용 executor를 줘서 전역과 분리(2026-06-25 수정).
# 로봇/Nav2 PC(같은 저장맵+AMCL, 도메인은 로봇별 팀 표준 — 젠지 1, 티원 2)에서 실행:
#   python3 patrol_waypoints_bridge.py --robot tb3_1
import argparse
import json
import math
import os
import queue
import threading
import time
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters

GOAL_TIMEOUT_S = 240.0     # 레그 1개 상한 — 초과 시 cancel(무한대기로 큐 블록 방지, 2026-07-08)
                           # 2026-07-09: 90→240 — 협소 회랑(36cm) 레그가 PolygonSlow/Limit 크롤로
                           # 실측 ~217s. 이건 행 방지 워치독이지 페이스 강제가 아님 — 넉넉히.
DEPART_DIST_M = 0.3        # 출발점에서 이만큼 벗어나면 PolygonStop 복원
DEPART_FALLBACK_S = 30.0   # 이동 실패해도 무조건 복원(안전 성역)
# 복귀주차 목표(= AMCL 독 시딩값, urhynix-t1-amcl-saved-map 참조) — 맵 재캡처 시 갱신 필수(2026-07-09).
DOCK_X, DOCK_Y, DOCK_YAW = 0.038, 1.405, 0.293
# 주차 전용 위치 허용오차(m) — 순찰 레그(0.15)보다 조여 독 정밀주차. park 끝나면 원복(2026-07-09 P0).
PARK_XY_TOL, PATROL_XY_TOL = 0.10, 0.15
# 주행기록(레그 단위 JSONL, 2026-07-09) — /tmp 금지(재부팅 증발), 홈에 영속. 분석: tail/jq/python 1줄.
RUN_LOG = os.path.expanduser('~/patrol_runs.jsonl')


def record(event):
    """주행기록 1건 append(JSONL). 기록 실패는 주행에 무영향(로그는 부업, 주행이 본업)."""
    try:
        with open(RUN_LOG, 'a') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
    except OSError:
        pass
YAW_ALIGN_TOL = 0.15       # 주차 방향 허용오차(rad) — goal_checker yaw 체크가 해제돼 있어 Spin으로 정렬


class CmdListener(Node):
    """Unity 명령을 구독해 큐에 적재만 한다(Nav2 호출은 메인 스레드가)."""

    def __init__(self, robot, q, nav_prefix):
        super().__init__('patrol_waypoints_bridge')
        self.q = q
        self.odom_pos = None
        self.amcl_pos = None
        self.stop_flag = False   # 무한 순찰 정지 요청(/patrol_stop) — 백그라운드 executor가 세우고 메인 루프가 읽음
        # Unity 계약 토픽은 항상 /<robot>/* — nav 스택 쪽 토픽/서비스만 nav_prefix를 따른다
        # (티원=ns 스택이라 /<robot>/*, 젠지=비-ns 표준 스택이라 빈 prefix. --nav-ns 참조)
        self.create_subscription(PoseStamped, f'/{robot}/goal_pose', self.on_goal, 10)
        self.create_subscription(PoseArray, f'/{robot}/patrol_waypoints', self.on_route, 10)
        # 무한 순찰 정지(Bool). 큐 미경유 — 메인이 레그루프에 묶여 있어도 플래그로 즉시 전달.
        self.create_subscription(Bool, f'/{robot}/patrol_stop', self.on_stop, 10)
        # 독/구석 출발 시 PolygonStop 일시 해제용 — 상대변위 판정이라 odom으로 충분
        self.create_subscription(Odometry, f'{nav_prefix}/odom', self.on_odom, 10)
        # 복귀주차 방향 정렬용 현재 yaw — amcl 발행 QoS(TRANSIENT_LOCAL)에 맞춤
        self.amcl_yaw = None
        aq = QoSProfile(depth=1)
        aq.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self.create_subscription(PoseWithCovarianceStamped, f'{nav_prefix}/amcl_pose', self.on_amcl, aq)
        self.param_cli = self.create_client(SetParameters, f'{nav_prefix}/collision_monitor/set_parameters')
        # 주차 전용 goal_checker xy tolerance 동적 조정용(SimpleGoalChecker dynamic reconfigure)
        self.ctrl_param_cli = self.create_client(SetParameters, f'{nav_prefix}/controller_server/set_parameters')
        self.get_logger().info(f'구독: /{robot}/goal_pose, /{robot}/patrol_waypoints — Unity 명령 대기')

    def on_odom(self, msg: Odometry):
        self.odom_pos = msg.pose.pose.position

    def on_amcl(self, msg: PoseWithCovarianceStamped):
        o = msg.pose.pose.orientation
        self.amcl_yaw = 2.0 * math.atan2(o.z, o.w)
        self.amcl_pos = msg.pose.pose.position

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

    def on_stop(self, msg: Bool):
        if msg.data:
            self.stop_flag = True
            self.get_logger().info('순찰 정지 요청 수신 — 현재 랩 마무리 후 복귀주차')


def to_stamped(nav, p, frame):
    ps = PoseStamped()
    ps.header.frame_id = frame or 'map'
    ps.header.stamp = nav.get_clock().now().to_msg()
    ps.pose = p
    return ps


def set_polygon_stop(listener, log, enabled):
    """collision_monitor PolygonStop 동적 토글. 독 존 안에서 출발할 때 잠깐 끄는 용도(nav2 공식 패턴).
    실패해도 주행은 계속(토글은 편의, 안전장치 복원은 wait_result가 보장)."""
    if not listener.param_cli.service_is_ready():
        log.warn('collision_monitor set_parameters 서비스 없음 — 존 토글 스킵')
        return False
    p = Parameter(name='PolygonStop.enabled',
                  value=ParameterValue(type=ParameterType.PARAMETER_BOOL, bool_value=enabled))
    fut = listener.param_cli.call_async(SetParameters.Request(parameters=[p]))
    t0 = time.time()
    while not fut.done() and time.time() - t0 < 5.0:
        time.sleep(0.1)  # future 완료는 백그라운드 executor가 처리
    ok = bool(fut.done() and fut.result().results and fut.result().results[0].successful)
    (log.info if ok else log.warn)(f'PolygonStop.enabled={enabled} → {"OK" if ok else "실패"}')
    return ok


def set_xy_goal_tol(listener, log, tol):
    """controller_server goal_checker의 xy_goal_tolerance 동적 변경(SimpleGoalChecker는 dynamic reconfigure 지원).
    주차만 조이고 순찰 레그엔 원복하는 용도. 실패해도 주차는 계속(정밀도만 손해)."""
    cli = listener.ctrl_param_cli
    if not cli.service_is_ready():
        log.warn('controller_server set_parameters 서비스 없음 — 주차 tolerance 조정 스킵')
        return False
    p = Parameter(name='goal_checker.xy_goal_tolerance',
                  value=ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=float(tol)))
    fut = cli.call_async(SetParameters.Request(parameters=[p]))
    t0 = time.time()
    while not fut.done() and time.time() - t0 < 5.0:
        time.sleep(0.1)
    ok = bool(fut.done() and fut.result().results and fut.result().results[0].successful)
    (log.info if ok else log.warn)(f'goal_checker.xy_goal_tolerance={tol} → {"OK" if ok else "실패"}')
    return ok


def begin_departure(listener, log):
    """출발 직전 PolygonStop 해제. 복원 조건(변위/시간)은 wait_result가 감시."""
    if not set_polygon_stop(listener, log, False):
        return None
    return {'start': listener.odom_pos, 't0': time.time(), 'restored': False}


def _dist(a, b):
    if a is None or b is None:
        return 0.0
    return math.hypot(b.x - a.x, b.y - a.y)


def wait_result(nav, log, label, timeout_s=GOAL_TIMEOUT_S, listener=None, depart=None, cancel_on_stop=False):
    t0 = time.time()
    timed_out = False
    try:
        while not nav.isTaskComplete():
            if cancel_on_stop and listener is not None and listener.stop_flag:
                log.warn(f'{label}: 순찰 정지 요청 — goal 취소')
                nav.cancelTask()
                break
            if depart and not depart['restored'] and (
                    _dist(depart['start'], listener.odom_pos) > DEPART_DIST_M
                    or time.time() - depart['t0'] > DEPART_FALLBACK_S):
                set_polygon_stop(listener, log, True)
                depart['restored'] = True
            if time.time() - t0 > timeout_s:
                log.error(f'{label}: {timeout_s:.0f}s 타임아웃 — goal 취소')
                nav.cancelTask()
                timed_out = True
                break
            fb = nav.getFeedback()
            if fb and hasattr(fb, 'current_waypoint'):
                log.info(f'{label}: 웨이포인트 #{fb.current_waypoint + 1}', throttle_duration_sec=2.0)
            time.sleep(0.2)
        r = nav.getResult()
        # 타임아웃 취소 후 getResult가 SUCCEEDED를 주는 가짜 성공 차단(2026-07-10 젠지 복귀주차 실측:
        # 240s 타임아웃·독에서 1.3m 이탈인데 JSONL에 SUCCEEDED로 기록됨) — 목표 미달이므로 CANCELED로 강등.
        if timed_out and r == TaskResult.SUCCEEDED:
            r = TaskResult.CANCELED
        if r == TaskResult.SUCCEEDED:
            log.info(f'{label}: 성공')
        elif r == TaskResult.CANCELED:
            log.warn(f'{label}: 취소됨')
        else:
            log.error(f'{label}: 실패 result={r}')
        return r
    finally:
        # 어떤 경로로 끝나도(성공/취소/예외) PolygonStop은 반드시 복원 — 안전 성역
        if depart and not depart['restored']:
            set_polygon_stop(listener, log, True)
            depart['restored'] = True


def recover(nav, log, tag):
    """레그 실패 탈출(2026-07-10): costmap 청소 + 소폭 후진 → 'Start occupied'(출발셀이 장애물셀) 자동 해제.
    오늘 실측: 3랩 뒤 로봇이 좁은 회랑서 장애물 가장자리에 얹혀 전 레그 0초 실패 → 무한순찰 붕괴.
    후진으로 자유공간에 복귀시키면 다음 레그가 다시 계획 가능 → 순찰 지속. 실패해도 다음 레그로 진행."""
    log.warn(f'{tag}: 탈출 리커버리 — costmap 청소 + 후진 0.12m')
    try:
        nav.clearLocalCostmap()
        nav.clearGlobalCostmap()
    except Exception:  # noqa: BLE001 — 리커버리는 best-effort, 실패해도 순찰 계속
        pass
    try:
        nav.backup(backup_dist=0.12, backup_speed=0.05, time_allowance=15)
        wait_result(nav, log, f'{tag} 후진', 20.0)
    except Exception:  # noqa: BLE001
        pass


def park_at_dock(nav, listener, log, run_id=None):
    """순찰 종료 후 충전독 복귀주차(2026-07-09): 위치는 goToPose, 방향은 Spin으로 원방향(DOCK_YAW)
    정렬 — goal_checker의 yaw 체크가 해제돼 있어(벽 인접 회전 스톨 방지) 위치·방향을 분리 처리.
    2026-07-09 P0: 주차만 xy tolerance 조이고(PARK_XY_TOL) 실제 도착 포즈·오차를 기록(측정 없으면 최적화 불가)."""
    dock = PoseStamped()
    dock.header.frame_id = 'map'
    dock.header.stamp = nav.get_clock().now().to_msg()
    dock.pose.position.x = DOCK_X
    dock.pose.position.y = DOCK_Y
    dock.pose.orientation.z = math.sin(DOCK_YAW / 2)
    dock.pose.orientation.w = math.cos(DOCK_YAW / 2)
    log.info(f'복귀주차: 독({DOCK_X}, {DOCK_Y})으로 이동 (tol {PARK_XY_TOL}m)')
    set_xy_goal_tol(listener, log, PARK_XY_TOL)          # 주차만 조임
    t0 = time.time()
    nav.goToPose(dock)
    r = wait_result(nav, log, '복귀주차')
    set_xy_goal_tol(listener, log, PATROL_XY_TOL)        # 순찰용으로 원복(어떤 결과든)
    # 실제 도착 포즈 + 오차 기록. amcl_pos/yaw는 백그라운드 executor가 최신화 — 정지 직후 값이 최종 근사.
    ax = ay = ayaw = err_xy = err_yaw = None
    if listener.amcl_pos is not None:
        ax, ay = round(listener.amcl_pos.x, 3), round(listener.amcl_pos.y, 3)
        err_xy = round(math.hypot(ax - DOCK_X, ay - DOCK_Y), 3)
    if listener.amcl_yaw is not None:
        ayaw = round(math.degrees(listener.amcl_yaw), 1)
        err_yaw = round(math.degrees((DOCK_YAW - listener.amcl_yaw + math.pi) % (2.0 * math.pi) - math.pi), 1)
    record({'kind': 'park', 'run': run_id, 'x': DOCK_X, 'y': DOCK_Y,
            'ax': ax, 'ay': ay, 'ayaw_deg': ayaw, 'err_xy_m': err_xy, 'err_yaw_deg': err_yaw,
            'tol': PARK_XY_TOL, 'dur_s': round(time.time() - t0, 1),
            'result': getattr(r, 'name', str(r)), 't': round(time.time(), 1)})
    yaw = listener.amcl_yaw
    if yaw is None:
        log.warn('amcl_pose 미수신 — 주차 방향 정렬 스킵')
        return
    d = (DOCK_YAW - yaw + math.pi) % (2.0 * math.pi) - math.pi
    if abs(d) > YAW_ALIGN_TOL:
        log.info(f'주차 방향 정렬: {math.degrees(d):.0f}° 회전')
        nav.spin(spin_dist=d, time_allowance=30)
        r = wait_result(nav, log, '방향정렬', 60.0)
        # 정렬 후 최종 헤딩 오차 기록(Spin이 실제로 맞췄는지 실측)
        fyaw = listener.amcl_yaw
        ferr = (round(math.degrees((DOCK_YAW - fyaw + math.pi) % (2.0 * math.pi) - math.pi), 1)
                if fyaw is not None else None)
        record({'kind': 'align', 'run': run_id, 'deg': round(math.degrees(d)),
                'final_yaw_deg': round(math.degrees(fyaw), 1) if fyaw is not None else None,
                'final_err_yaw_deg': ferr,
                'result': getattr(r, 'name', str(r)), 't': round(time.time(), 1)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--robot', default='tb3_1')
    # nav2 스택 네임스페이스. 기본 = --robot과 동일(티원 ns 스택). 젠지(비-ns 표준 스택)는 --nav-ns '' 전달.
    ap.add_argument('--nav-ns', default=None)
    # 복귀주차 좌표 x y yaw(rad). 미지정 = 모듈 기본(티원 독). 젠지가 기본값으로 돌면 티원 주차 자리로
    # 파고들므로(2026-07-10 발견) 로봇별로 자기 독을 넘길 것 — _robot_nav_up.sh가 초기포즈로 전달.
    ap.add_argument('--dock', nargs=3, type=float, default=None, metavar=('X', 'Y', 'YAW'))
    a = ap.parse_args()
    if a.dock:
        global DOCK_X, DOCK_Y, DOCK_YAW
        DOCK_X, DOCK_Y, DOCK_YAW = a.dock
    nav_ns = a.robot if a.nav_ns is None else a.nav_ns
    nav_prefix = f'/{nav_ns}' if nav_ns else ''
    rclpy.init()

    q = queue.Queue()
    listener = CmdListener(a.robot, q, nav_prefix)
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
    nav = BasicNavigator(namespace=nav_ns)
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
                depart = begin_departure(listener, log)
                t0 = time.time()
                nav.goToPose(msg)
                r = wait_result(nav, log, 'goToPose', GOAL_TIMEOUT_S, listener, depart)
                record({'kind': 'goal', 'x': round(msg.pose.position.x, 3),
                        'y': round(msg.pose.position.y, 3), 'dur_s': round(time.time() - t0, 1),
                        'result': getattr(r, 'name', str(r)), 't': round(time.time(), 1)})
            else:
                goals = [to_stamped(nav, p, msg.header.frame_id) for p in msg.poses]
                # 왕복 순찰(2026-07-09): 마지막 점 도착 후 역순(N-1→…→1)으로 출발점 복귀.
                # ponytail: 무한 루프 순회는 아직 아님 — 필요해지면 FollowWaypoints의
                # number_of_loops(goal 필드 직접 구성)로 업그레이드.
                if len(goals) >= 2:
                    goals = goals + goals[-2::-1]
                run_id = int(time.time())
                listener.stop_flag = False   # 새 순찰 시작 시 정지플래그 리셋(정지 후 재시작 대비)
                # 무한 연속 순찰(2026-07-09): /patrol_stop(Bool) 올 때까지 왕복을 계속 반복.
                # 랩 사이 주차 없음 — 주차 정확도는 순찰 중 무관, 정지 시 1회만 복귀주차.
                log.info(f'무한 순찰 시작 ({len(goals)}점 왕복 반복 — 정지: /{a.robot}/patrol_stop)')
                lap = 0
                # 레그별 실행: 각 레그 시작 전 다음 목표 방위각으로 사전 회전("방향 보고→이동").
                # 레그 시작 헤딩 불일치가 최대 시간싱크였음 — 실측: 같은 B-회랑이 정방향(등지고 출발)
                # 136s vs 역방향(보고 출발) 29s. Spin 0.4rad/s면 180°가 ~8s. 실패 레그는 스킵하고 계속.
                while not listener.stop_flag:
                    lap += 1
                    log.info(f'--- 랩 {lap} 시작 ---')
                    depart = begin_departure(listener, log)   # 각 랩 출발점(복귀지점)에서 독존 토글
                    for i, g in enumerate(goals):
                        if listener.stop_flag:
                            break
                        if listener.amcl_pos is not None and listener.amcl_yaw is not None:
                            b = math.atan2(g.pose.position.y - listener.amcl_pos.y,
                                           g.pose.position.x - listener.amcl_pos.x)
                            dyaw = (b - listener.amcl_yaw + math.pi) % (2.0 * math.pi) - math.pi
                            if abs(dyaw) > 0.5:
                                nav.spin(spin_dist=dyaw, time_allowance=30)
                                wait_result(nav, log, f'랩{lap}레그{i + 1} 사전회전', 60.0)
                        g.header.stamp = nav.get_clock().now().to_msg()
                        log.info(f'랩{lap} 레그 {i + 1}/{len(goals)} → ({g.pose.position.x:.2f}, {g.pose.position.y:.2f})')
                        t0 = time.time()
                        nav.goToPose(g)
                        r = wait_result(nav, log, f'랩{lap}레그{i + 1}', GOAL_TIMEOUT_S, listener,
                                        depart if i == 0 else None, cancel_on_stop=True)
                        record({'kind': 'leg', 'run': run_id, 'lap': lap, 'leg': i + 1, 'total': len(goals),
                                'x': round(g.pose.position.x, 3), 'y': round(g.pose.position.y, 3),
                                'dur_s': round(time.time() - t0, 1),
                                'result': getattr(r, 'name', str(r)), 't': round(time.time(), 1)})
                        # 레그 실패(주로 'Start occupied' 낌) → 탈출 리커버리로 자유공간 복귀 후 다음 레그 진행
                        if r != TaskResult.SUCCEEDED and not listener.stop_flag:
                            recover(nav, log, f'랩{lap}레그{i + 1}')
                    record({'kind': 'lap', 'run': run_id, 'lap': lap, 't': round(time.time(), 1)})
                log.info(f'순찰 정지 — {lap}랩 완료, 복귀주차')
                park_at_dock(nav, listener, log, run_id)  # 정지 시 1회 충전독 복귀주차(실패해도 귀소 시도)
    except KeyboardInterrupt:
        pass
    finally:
        listener.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
