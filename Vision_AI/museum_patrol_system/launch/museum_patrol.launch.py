"""Launch museum patrol vision stack (YOLO + task manager).

Nav2 / Unity / Arduino / SLAM are owned by the team URHYNIX scripts — see docs/team-integration.md.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

ROBOT_PROFILES = {
    't1': {
        'label': 'T1 순찰 로봇 (RealSense D435)',
        'image_topic': '/tb3_1/camera/color/image_raw',
        'camera_namespace': 'tb3_1',
        'launch_realsense': 'true',
    },
    'geng': {
        'label': 'Gen.G 방제 로봇 (Pi Camera)',
        'image_topic': '/tb3_2/camera/image_raw',
        'camera_namespace': 'tb3_2',
        'launch_realsense': 'false',
    },
}


def _resolve_auto(explicit: str, profile_default: str) -> str:
    if explicit in ('', 'auto'):
        return profile_default
    return explicit


def launch_setup(context, *args, **kwargs):
    robot_id = LaunchConfiguration('robot_id').perform(context)
    profile = ROBOT_PROFILES.get(robot_id, ROBOT_PROFILES['t1'])

    image_topic = _resolve_auto(
        LaunchConfiguration('image_topic').perform(context),
        profile['image_topic'],
    )
    launch_realsense = _resolve_auto(
        LaunchConfiguration('launch_realsense').perform(context),
        profile['launch_realsense'],
    )
    camera_namespace = profile.get('camera_namespace', '')

    nodes = []

    if launch_realsense == 'true':
        realsense_share = get_package_share_directory('realsense2_camera')
        nodes.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(realsense_share, 'launch', 'rs_launch.py'),
                ),
                launch_arguments={
                    'camera_namespace': camera_namespace,
                    'camera_name': 'camera',
                    'rgb_camera.color_profile': LaunchConfiguration(
                        'realsense_color_profile'
                    ),
                    'enable_depth': LaunchConfiguration('realsense_enable_depth'),
                    'pointcloud.enable': LaunchConfiguration('realsense_pointcloud'),
                    'colorizer.enable': LaunchConfiguration('realsense_colorizer'),
                    'serial_no': LaunchConfiguration('realsense_serial_no'),
                }.items(),
            )
        )

    launch_patrol_navigation = LaunchConfiguration('launch_patrol_navigation').perform(context)
    patrol_navigation_params = LaunchConfiguration('patrol_navigation_params').perform(context)

    nodes.extend([
        Node(
            package='museum_patrol_system',
            executable='yolo_detector',
            name='yolo_detector',
            output='screen',
            parameters=[{
                'model_path': LaunchConfiguration('model_path'),
                'confidence_threshold': ParameterValue(
                    LaunchConfiguration('confidence_threshold'),
                    value_type=float,
                ),
                'image_topic': image_topic,
                'detect_image_topic': '/detect/image_raw',
                'status_topic': '/detect/status',
                'detection_mode': LaunchConfiguration('detection_mode'),
                'inference_imgsz': ParameterValue(
                    LaunchConfiguration('inference_imgsz'),
                    value_type=int,
                ),
                'inference_fps': ParameterValue(
                    LaunchConfiguration('inference_fps'),
                    value_type=float,
                ),
                'publish_fps': ParameterValue(
                    LaunchConfiguration('publish_fps'),
                    value_type=float,
                ),
            }],
        ),
        Node(
            package='museum_patrol_system',
            executable='task_manager',
            name='task_manager',
            output='screen',
            parameters=[{
                'night_mode': ParameterValue(
                    LaunchConfiguration('night_mode'),
                    value_type=bool,
                ),
                'fire_temp_threshold_c': 40.0,
                'battery_low_threshold_pct': 20.0,
                'task_eval_period_sec': 0.5,
                'state_topic': '/museum/task/state',
                'command_topic': '/museum/task/command',
            }],
        ),
    ])

    if launch_patrol_navigation == 'true':
        nodes.append(
            Node(
                package='museum_patrol_system',
                executable='patrol_navigation',
                name='patrol_navigation',
                output='screen',
                parameters=[patrol_navigation_params],
            )
        )

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'robot_id',
            default_value='t1',
            description='Hardware profile: t1 | geng',
            choices=['t1', 'geng'],
        ),
        DeclareLaunchArgument(
            'image_topic',
            default_value='auto',
            description='auto → t1:/tb3_1/camera/color/image_raw, geng:/tb3_2/camera/image_raw',
        ),
        DeclareLaunchArgument(
            'launch_realsense',
            default_value='auto',
            description='auto → on for t1, off for geng.',
        ),
        DeclareLaunchArgument(
            'realsense_color_profile',
            default_value='640,480,30',
            description='RealSense RGB stream: width,height,fps',
        ),
        DeclareLaunchArgument(
            'realsense_enable_depth',
            default_value='false',
        ),
        DeclareLaunchArgument(
            'realsense_pointcloud',
            default_value='false',
        ),
        DeclareLaunchArgument(
            'realsense_colorizer',
            default_value='false',
        ),
        DeclareLaunchArgument(
            'realsense_serial_no',
            default_value='',
        ),
        DeclareLaunchArgument(
            'model_path',
            default_value='yolov8n.pt',
        ),
        DeclareLaunchArgument(
            'confidence_threshold',
            default_value='0.5',
        ),
        DeclareLaunchArgument(
            'detection_mode',
            default_value='museum',
            choices=['museum', 'all'],
        ),
        DeclareLaunchArgument(
            'inference_imgsz',
            default_value='416',
        ),
        DeclareLaunchArgument(
            'inference_fps',
            default_value='10.0',
        ),
        DeclareLaunchArgument(
            'publish_fps',
            default_value='30.0',
        ),
        DeclareLaunchArgument(
            'night_mode',
            default_value='false',
        ),
        DeclareLaunchArgument(
            'launch_patrol_navigation',
            default_value='false',
            description='Launch Nav2 patrol/dispatch/charge-wait mission executor.',
        ),
        DeclareLaunchArgument(
            'patrol_navigation_params',
            default_value=os.path.join(
                get_package_share_directory('museum_patrol_system'),
                'config',
                'patrol_navigation.yaml',
            ),
        ),
        OpaqueFunction(function=launch_setup),
    ])
