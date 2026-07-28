"""RealSense D435 only — run on T1 robot (Raspberry Pi). No YOLO."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration

ROBOT_NS_T1 = 'tb3_1'


def generate_launch_description():
    pkg_share = get_package_share_directory('museum_patrol_system')
    realsense_share = get_package_share_directory('realsense2_camera')
    config_file = os.path.join(pkg_share, 'config', 'realsense_wifi.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('robot_namespace', default_value=ROBOT_NS_T1),
        DeclareLaunchArgument(
            'realsense_color_profile',
            default_value='640x480x6',
            description='RealSense RGB profile WIDTHxHEIGHTxFPS',
        ),
        DeclareLaunchArgument('realsense_serial_no', default_value=''),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(realsense_share, 'launch', 'rs_launch.py'),
            ),
            launch_arguments={
                'config_file': config_file,
                'camera_namespace': LaunchConfiguration('robot_namespace'),
                'camera_name': 'camera',
                'rgb_camera.color_profile': LaunchConfiguration('realsense_color_profile'),
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
                'serial_no': LaunchConfiguration('realsense_serial_no'),
            }.items(),
        ),
    ])
