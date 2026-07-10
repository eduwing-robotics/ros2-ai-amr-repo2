# dual_bringup.launch.py — 네임스페이스+tf_prefix 멀티로봇 bringup (동시 주행 전제).
# 표준 turtlebot3_bringup/robot.launch.py의 최소 변형: state_publisher·turtlebot3_node는 그대로 두고
# (둘 다 namespace로 토픽·TF 프레임을 이미 올바르게 prefix함), coin_d4 라이다만 교체한다.
# 누수 이유: coin_d4 single_lidar_node.launch.py는 robot.launch.py가 넘기는 frame_id/namespace 인자를
#   무시하고 yaml의 고정 frame_id("base_scan")를 쓴다 → scan header.frame_id가 prefix 안 돼 URDF의
#   "<ns>/base_scan" TF 프레임과 불일치 → SLAM/costmap TF 룩업 실패. 여기서 frame_id=<ns>/base_scan로 박는다.
# 결과(ns=tb3_2 예): 토픽 /tb3_2/{scan,odom,cmd_vel,imu,joint_states}, TF /tb3_2/tf 트리 전체가 tb3_2/* 프레임.
#   → 두 로봇을 동시에 켜도 토픽·프레임이 완전 격리되어 /scan·/tf 충돌 0.
# 사용: ros2 launch dual_bringup.launch.py namespace:=tb3_2 usb_port:=/dev/ttyACM0
#   (env: TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03 필요. _robot_bringup_ns.sh가 env 세팅 후 호출.)
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace


def generate_launch_description():
    TURTLEBOT3_MODEL = os.environ['TURTLEBOT3_MODEL']

    namespace = LaunchConfiguration('namespace', default='tb3_1')
    usb_port = LaunchConfiguration('usb_port', default='/dev/ttyACM0')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    bringup_dir = get_package_share_directory('turtlebot3_bringup')
    tb3_param_dir = os.path.join(bringup_dir, 'param', TURTLEBOT3_MODEL + '.yaml')
    state_pub_launch = os.path.join(bringup_dir, 'launch', 'turtlebot3_state_publisher.launch.py')

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=namespace,
                              description='로봇 네임스페이스 (tb3_1=티원, tb3_2=젠지)'),
        DeclareLaunchArgument('usb_port', default_value=usb_port,
                              description='OpenCR USB 포트'),
        DeclareLaunchArgument('use_sim_time', default_value=use_sim_time),

        # 이 아래 모든 노드를 /<namespace> 로 밀어넣음 → 토픽·/tf 가 /<ns>/* 로 격리.
        PushRosNamespace(namespace),

        # 1) robot_state_publisher — xacro namespace:=<ns>/ 로 URDF 링크가 <ns>/base_link 등으로 prefix.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(state_pub_launch),
            launch_arguments={'use_sim_time': use_sim_time,
                              'namespace': namespace}.items(),
        ),

        # 2) turtlebot3_ros — odometry.cpp/imu.cpp/joint_state.cpp가 namespace 파라미터로
        #    odom/base_footprint/imu/joint 프레임을 <ns>/ prefix. burger.yaml(/** 와일드카드)도 매칭됨.
        Node(
            package='turtlebot3_node',
            executable='turtlebot3_ros',
            parameters=[tb3_param_dir, {'namespace': namespace}],
            arguments=['-i', usb_port],
            output='screen',
        ),

        # 3) coin_d4 라이다 — frame_id를 <ns>/base_scan 로 직접 박는다(누수 #1 봉합). 토픽은 PushRosNamespace로 /<ns>/scan.
        Node(
            package='coin_d4_driver',
            executable='single_coin_d4_node',
            parameters=[{
                'port': '/dev/tb3_lidar',
                'frame_id': [namespace, '/base_scan'],
                'baudrate': 230400,
                'version': 4,
                'topic_name': 'scan',
                'reverse': False,
                'warmup_time': 5,
            }],
            output='screen',
        ),
    ])
