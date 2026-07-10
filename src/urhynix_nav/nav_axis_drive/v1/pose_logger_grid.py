import sys
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped

MAP_ORIGIN_X = -0.737
MAP_ORIGIN_Y = -2.118
MAP_SIZE = 2.8
GRID_MAX = 200.0

LOG_FILE = '/home/kimsunil/robotmap/pose_log.txt'


def map_to_grid(real_x, real_y):
    gx = (real_x - MAP_ORIGIN_X) / MAP_SIZE * GRID_MAX
    gy = (real_y - MAP_ORIGIN_Y) / MAP_SIZE * GRID_MAX
    return round(gx, 1), round(gy, 1)


class PoseLogger(Node):
    def __init__(self):
        super().__init__('pose_logger')
        self.current_pose = None
        self.last_gx = None
        self.last_gy = None
        self.sub = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.pose_callback,
            10
        )
        self.get_logger().info('이동 시 자동 출력 | "ps"=저장 | "xc"=마지막삭제 | "c"=전체삭제 | "q"=종료')

    def pose_callback(self, msg):
        self.current_pose = msg.pose.pose
        x = self.current_pose.position.x
        y = self.current_pose.position.y
        gx, gy = map_to_grid(x, y)

        if self.last_gx is None or abs(gx - self.last_gx) >= 1.0 or abs(gy - self.last_gy) >= 1.0:
            self.last_gx = gx
            self.last_gy = gy
            print(f'[위치] 그리드({gx}, {gy})  맵({x:.3f}, {y:.3f})')

    def log_pose(self):
        if self.current_pose is None:
            print('[!] 아직 위치 데이터 없음 (amcl_pose 수신 대기 중)')
            return

        x = self.current_pose.position.x
        y = self.current_pose.position.y
        oz = self.current_pose.orientation.z
        ow = self.current_pose.orientation.w

        gx, gy = map_to_grid(x, y)

        line = f'맵({x:.3f}, {y:.3f})  그리드({gx}, {gy})  방향(z={oz:.4f}, w={ow:.4f})'
        print(f'[저장] {line}')

        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')


def input_loop(node):
    while rclpy.ok():
        try:
            cmd = input()
        except EOFError:
            break
        if cmd.strip().lower() == 'ps':
            node.log_pose()
        elif cmd.strip().lower() == 'xc':
            try:
                with open(LOG_FILE, 'r') as f:
                    lines = f.readlines()
                if lines:
                    removed = lines.pop()
                    with open(LOG_FILE, 'w') as f:
                        f.writelines(lines)
                    print(f'[삭제] {removed.strip()}')
                else:
                    print('[!] 저장된 좌표 없음')
            except FileNotFoundError:
                print('[!] 저장된 좌표 없음')
        elif cmd.strip().lower() == 'c':
            open(LOG_FILE, 'w').close()
            print('[삭제] pose_log.txt 초기화 완료')
        elif cmd.strip().lower() == 'q':
            print('종료합니다.')
            rclpy.shutdown()
            break


def main():
    rclpy.init()
    node = PoseLogger()

    t = threading.Thread(target=input_loop, args=(node,), daemon=True)
    t.start()

    rclpy.spin(node)


if __name__ == '__main__':
    main()
