import sys
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav2_simple_commander.robot_navigator import TaskResult

MAP_ORIGIN_X = -0.737
MAP_ORIGIN_Y = -2.118
MAP_SIZE = 2.8  # 56px * 0.05m/px
GRID_MAX = 200.0


def grid_to_map(gx, gy):
    real_x = MAP_ORIGIN_X + (gx / GRID_MAX) * MAP_SIZE
    real_y = MAP_ORIGIN_Y + (gy / GRID_MAX) * MAP_SIZE
    return real_x, real_y


class GoToGoal(Node):
    def __init__(self, grid_x, grid_y):
        super().__init__('go_to_goal')
        self.navigator = BasicNavigator()
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.go_to_goal()

    def go_to_goal(self):
        self.navigator.waitUntilNav2Active()

        real_x, real_y = grid_to_map(self.grid_x, self.grid_y)
        self.get_logger().info(
            f'그리드 ({self.grid_x}, {self.grid_y}) -> 맵 ({real_x:.3f}, {real_y:.3f})'
        )

        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = real_x
        goal_pose.pose.position.y = real_y
        goal_pose.pose.orientation.w = 1.0

        self.get_logger().info('목표 위치로 이동 시작')
        self.navigator.goToPose(goal_pose)

        while not self.navigator.isTaskComplete():
            feedback = self.navigator.getFeedback()
            time.sleep(0.5)

        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('목표 도착 성공!')
        else:
            self.get_logger().info('이동 실패')


def main():
    if len(sys.argv) < 3:
        print('사용법: python3 nav2_goal.py <x> <y>  (0~200)')
        sys.exit(1)

    gx = float(sys.argv[1])
    gy = float(sys.argv[2])

    if not (0 <= gx <= 200 and 0 <= gy <= 200):
        print('좌표는 0~200 범위여야 합니다')
        sys.exit(1)

    rclpy.init()
    node = GoToGoal(gx, gy)
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
