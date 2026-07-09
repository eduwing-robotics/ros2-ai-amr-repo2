#!/usr/bin/env python3
# readyd.py — 티원(tb3_1) "주행준비 원버튼" 온디맨드 트리거 데몬(로봇 상주, systemd user).
#   Unity ControlRoom '주행준비' 버튼이 /tb3_1/prepare_drive(std_msgs/Bool, data=true)를 발행하면
#   ~/t1_drive_ready.sh(bringup→배터리게이트→AMCL+재시딩→nav2 8노드 lifecycle→검증)를 1회 실행하고,
#   스크립트 stdout 각 줄을 /tb3_1/drive_ready_status(std_msgs/String, transient_local)로 실시간 회신한다.
#   → Unity는 SSH 없이 ROS 토픽만으로 주행준비 풀시퀀스를 트리거하고 진행상황을 화면에 띄울 수 있다.
# 설계 원칙 보존: 이 데몬은 "항상 켜진 릴레이"가 아니라 "버튼 시 1회 실행 트리거"다.
#   bringup/nav2를 상주로 만들지 않으므로 robot_services/CLAUDE.md의 "하드웨어 초기화 순서·수동
#   lifecycle 보존" 원칙과 충돌하지 않음(수동 절차는 t1_drive_ready.sh 안에 그대로 있음).
# 동시 실행 방지(진행 중 재발행은 무시), 종료코드까지 상태로 회신.
import os
import subprocess
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import Bool, String


class ReadyD(Node):
    def __init__(self):
        super().__init__('urhynix_readyd')
        self.ns = os.environ.get('READYD_NS', 'tb3_1')
        self.script = os.path.expanduser('~/t1_drive_ready.sh')
        # 마지막 상태를 latch(transient_local) → Unity가 늦게 붙어도 최근 진행상황을 받음
        qos = QoSProfile(depth=20, history=HistoryPolicy.KEEP_LAST,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(String, f'/{self.ns}/drive_ready_status', qos)
        self.create_subscription(Bool, f'/{self.ns}/prepare_drive', self.on_trigger, 10)
        self._busy = threading.Lock()
        self.get_logger().info(f'readyd 대기: /{self.ns}/prepare_drive → {self.script}')
        self._status('READY — 주행준비 버튼 대기 중')

    def _status(self, text):
        m = String()
        m.data = text
        self.pub.publish(m)

    def on_trigger(self, msg: Bool):
        if not msg.data:
            return
        if not self._busy.acquire(blocking=False):
            self._status('이미 진행 중 — 재요청 무시')
            return
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            if not os.path.isfile(self.script):
                self._status(f'FAIL: 스크립트 없음 {self.script}')
                return
            self._status('시작: 주행준비 6단계')
            p = subprocess.Popen(['bash', self.script],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, bufsize=1)
            for line in p.stdout:
                line = line.rstrip()
                if line:
                    self._status(line)
                    self.get_logger().info(line)
            rc = p.wait()
            self._status('DRIVE-READY: PASS' if rc == 0 else f'FAIL (rc={rc})')
        except Exception as e:  # noqa: BLE001 — 데몬은 어떤 예외에도 죽지 않고 상태만 회신
            self._status(f'FAIL: readyd 예외 {e}')
        finally:
            self._busy.release()


def main():
    rclpy.init()
    node = ReadyD()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
