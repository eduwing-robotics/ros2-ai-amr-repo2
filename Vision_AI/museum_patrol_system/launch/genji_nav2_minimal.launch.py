from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_BT_NAV_TO_POSE = os.path.join(_PKG_ROOT, 'museum_patrol_system', 'config', 'genji_nav_to_pose_no_spin.xml')
_BT_NAV_THROUGH = os.path.join(_PKG_ROOT, 'museum_patrol_system', 'config', 'genji_nav_through_poses_no_spin.xml')


def generate_launch_description():
    map_yaml = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    loc_autostart = LaunchConfiguration('loc_autostart')
    nav_autostart = LaunchConfiguration('nav_autostart')
    log_level = LaunchConfiguration('log_level')

    startup_nodes = [
        ExecuteProcess(
            cmd=[
                'python3',
                os.path.join(_PKG_ROOT, 'scripts', 'scan_normalize.py'),
                '/scan',
                '/scan_fixed',
                '400',
            ],
            cwd=_PKG_ROOT,
            output='screen',
            additional_env={'SCAN_RESTAMP': '0'},
        ),
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            output='screen',
            parameters=[params_file, {'yaml_filename': map_yaml}, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            output='screen',
            arguments=['--ros-args', '--log-level', log_level],
            parameters=[
                {'autostart': loc_autostart},
                {'node_names': ['map_server', 'amcl']},
                {'use_sim_time': use_sim_time},
            ],
        ),
        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static'), ('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_smoother',
            executable='smoother_server',
            name='smoother_server',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static'), ('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            output='screen',
            parameters=[
                params_file,
                {
                    'use_sim_time': use_sim_time,
                    'default_nav_to_pose_bt_xml': _BT_NAV_TO_POSE,
                    'default_nav_through_poses_bt_xml': _BT_NAV_THROUGH,
                },
            ],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_waypoint_follower',
            executable='waypoint_follower',
            name='waypoint_follower',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_velocity_smoother',
            executable='velocity_smoother',
            name='velocity_smoother',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static'), ('cmd_vel', 'cmd_vel_nav')],
        ),
        Node(
            package='nav2_collision_monitor',
            executable='collision_monitor',
            name='collision_monitor',
            output='screen',
            parameters=[params_file, {'use_sim_time': use_sim_time}],
            arguments=['--ros-args', '--log-level', log_level],
            remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
        ),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            arguments=['--ros-args', '--log-level', log_level],
            parameters=[
                {'autostart': nav_autostart},
                {
                    'node_names': [
                        'controller_server',
                        'smoother_server',
                        'planner_server',
                        'behavior_server',
                        'bt_navigator',
                        'waypoint_follower',
                        'velocity_smoother',
                        'collision_monitor',
                    ]
                },
                {'use_sim_time': use_sim_time},
            ],
        ),
    ]

    return LaunchDescription(
        [
            DeclareLaunchArgument('map', description='Map yaml'),
            DeclareLaunchArgument('params_file', description='Nav2 params yaml'),
            DeclareLaunchArgument('use_sim_time', default_value='false'),
            DeclareLaunchArgument('loc_autostart', default_value='true'),
            DeclareLaunchArgument('nav_autostart', default_value='false'),
            DeclareLaunchArgument('autostart', default_value='true'),
            DeclareLaunchArgument('log_level', default_value='info'),
            *startup_nodes,
        ]
    )
