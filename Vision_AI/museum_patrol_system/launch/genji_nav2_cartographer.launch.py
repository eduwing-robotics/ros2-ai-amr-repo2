from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    pbstream = LaunchConfiguration('pbstream')
    carto_config_dir = LaunchConfiguration('carto_config_dir')
    carto_lua = LaunchConfiguration('carto_lua')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    log_level = LaunchConfiguration('log_level')
    resolution = LaunchConfiguration('resolution')

    cartographer_node = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-configuration_directory', carto_config_dir,
            '-configuration_basename', carto_lua,
            '-load_state_filename', pbstream,
            '-load_frozen_state', 'true',
            '-start_trajectory_with_default_topics', 'true',
        ],
        remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
    )

    cartographer_occupancy_grid_node = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid_node',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'resolution': resolution},
            {'publish_period_sec': 1.0},
        ],
        remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
    )

    startup_nodes = [
        cartographer_node,
        cartographer_occupancy_grid_node,
        ExecuteProcess(
            cmd=[
                'python3',
                os.path.join(_PKG_ROOT, 'scripts', 'genji_cartographer_pose_bridge.py'),
            ],
            cwd=_PKG_ROOT,
            output='screen',
            additional_env={
                'GENJI_CARTO_CONFIG_DIR': os.path.join(
                    _PKG_ROOT, 'museum_patrol_system', 'config', 'cartographer'
                ),
                'GENJI_CARTO_LUA': 'cartographer_arena_localization.lua',
            },
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
            parameters=[params_file, {'use_sim_time': use_sim_time}],
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
                {'autostart': autostart},
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
            DeclareLaunchArgument('params_file', description='Nav2 params yaml'),
            DeclareLaunchArgument('pbstream', description='Cartographer pbstream for localization'),
            DeclareLaunchArgument(
                'carto_config_dir',
                description='Directory with cartographer lua configs',
            ),
            DeclareLaunchArgument(
                'carto_lua',
                default_value='cartographer_arena_localization.lua',
            ),
            DeclareLaunchArgument('resolution', default_value='0.02'),
            DeclareLaunchArgument('use_sim_time', default_value='false'),
            DeclareLaunchArgument('autostart', default_value='true'),
            DeclareLaunchArgument('log_level', default_value='info'),
            *startup_nodes,
        ]
    )
