"""RealSense camera + JPEG compressor for Wi-Fi YOLO on laptop (namespace tb3_1)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

ROBOT_NS_T1 = 'tb3_1'


def generate_launch_description():
    pkg_share = get_package_share_directory('museum_patrol_system')
    realsense_share = get_package_share_directory('realsense2_camera')
    config_file = os.path.join(pkg_share, 'config', 'realsense_wifi.yaml')

    robot_ns = LaunchConfiguration('robot_namespace')
    color_profile = LaunchConfiguration('realsense_color_profile')
    serial_no = LaunchConfiguration('realsense_serial_no')

    return LaunchDescription([
        DeclareLaunchArgument('robot_namespace', default_value=ROBOT_NS_T1),
        DeclareLaunchArgument('realsense_color_profile', default_value='640x480x6'),
        DeclareLaunchArgument('realsense_serial_no', default_value=''),
        DeclareLaunchArgument('jpeg_quality', default_value='75'),
        DeclareLaunchArgument('jpeg_max_fps', default_value='10.0'),
        DeclareLaunchArgument(
            'raw_image_topic',
            default_value=f'/{ROBOT_NS_T1}/camera/color/image_raw',
        ),
        DeclareLaunchArgument(
            'compressed_image_topic',
            default_value=f'/{ROBOT_NS_T1}/camera/color/image_raw/compressed',
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(realsense_share, 'launch', 'rs_launch.py'),
            ),
            launch_arguments={
                'config_file': config_file,
                'camera_namespace': robot_ns,
                'camera_name': 'camera',
                'rgb_camera.color_profile': color_profile,
                'enable_depth': 'false',
                'enable_sync': 'false',
                'enable_infra': 'false',
                'enable_infra1': 'false',
                'enable_infra2': 'false',
                'enable_gyro': 'false',
                'enable_accel': 'false',
                'initial_reset': 'false',
                'usb_port_id': '2-2',
                'reconnect_timeout': '10.0',
                'publish_tf': 'false',
                'pointcloud.enable': 'false',
                'colorizer.enable': 'false',
                'align_depth.enable': 'false',
                'serial_no': serial_no,
            }.items(),
        ),
        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='museum_patrol_system',
                    executable='jpeg_compressor',
                    name='jpeg_camera_compressor',
                    output='screen',
                    parameters=[{
                        'input_topic': LaunchConfiguration('raw_image_topic'),
                        'output_topic': LaunchConfiguration('compressed_image_topic'),
                        'jpeg_quality': ParameterValue(
                            LaunchConfiguration('jpeg_quality'),
                            value_type=int,
                        ),
                        'max_publish_fps': ParameterValue(
                            LaunchConfiguration('jpeg_max_fps'),
                            value_type=float,
                        ),
                    }],
                ),
            ],
        ),
    ])
