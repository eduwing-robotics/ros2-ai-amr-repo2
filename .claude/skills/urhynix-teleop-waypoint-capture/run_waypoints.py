#!/usr/bin/env python3
# run_waypoints.py — waypoints_*.yaml(START+WP들)을 Nav2 FollowWaypoints로 순찰 실행.
# 로봇 측(Nav2+AMCL+같은 저장맵 구동 중)에서 실행. START로 초기위치 세팅 후 WP1..N 순회.
# 사용: python3 run_waypoints.py waypoints_tb3_1_final.yaml [--loop] [--no-initialpose]
import sys, time, argparse, yaml
import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


def make_pose(nav, p):
    ps = PoseStamped()
    ps.header.frame_id = p.get('header', {}).get('frame_id', 'map')
    ps.header.stamp = nav.get_clock().now().to_msg()
    pos = p['pose']['position']; ori = p['pose']['orientation']
    ps.pose.position.x = float(pos['x']); ps.pose.position.y = float(pos['y']); ps.pose.position.z = float(pos.get('z', 0.0))
    ps.pose.orientation.x = float(ori.get('x', 0.0)); ps.pose.orientation.y = float(ori.get('y', 0.0))
    ps.pose.orientation.z = float(ori['z']); ps.pose.orientation.w = float(ori['w'])
    return ps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('yaml')
    ap.add_argument('--loop', action='store_true', help='무한 순찰 반복')
    ap.add_argument('--no-initialpose', action='store_true', help='START로 AMCL 초기화 생략(이미 위치추정됨)')
    ap.add_argument('--dynamic-start', action='store_true',
                    help='START 좌표 무시 — 로봇 현재(localize된) 위치에서 출발. 충전소 위치가 매번 바뀔 때.')
    a = ap.parse_args()

    data = yaml.safe_load(open(a.yaml))
    poses = data['poses']
    start = next((p for p in poses if p['name'] == 'START'), None)
    wps = [p for p in poses if p['name'] != 'START']
    skip_init = a.no_initialpose or a.dynamic_start

    rclpy.init()
    nav = BasicNavigator()

    # localize는 tf(map->base_footprint)로 외부 확인되므로, simple_commander의 amcl_pose 무한대기를 항상 우회.
    nav.initial_pose_received = True
    if start and not skip_init:
        nav.setInitialPose(make_pose(nav, start))
        print(f"[init] 고정 START로 초기위치 세팅: {start['pose']['position']}")
    else:
        print("[init] 동적 START — 현재 localize된 위치에서 출발(START 좌표 무시). 로봇이 먼저 localize돼 있어야 함.")

    nav.waitUntilNav2Active()   # Nav2 + AMCL 활성 대기(위 우회로 amcl 대기 즉시 통과)
    print(f"[ready] Nav2 활성. 웨이포인트 {len(wps)}개 순찰 시작.")

    round_n = 0
    while True:
        round_n += 1
        goal = [make_pose(nav, p) for p in wps]
        nav.followWaypoints(goal)
        while not nav.isTaskComplete():
            fb = nav.getFeedback()
            if fb:
                print(f"  [r{round_n}] 현재 웨이포인트 #{fb.current_waypoint + 1}/{len(wps)}", end='\r')
            time.sleep(0.5)
        result = nav.getResult()
        print(f"\n[done r{round_n}] result={result}")
        if result != TaskResult.SUCCEEDED:
            print("⚠️ 실패/취소 — 중단."); break
        if not a.loop:
            break

    nav.lifecycleShutdown()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
