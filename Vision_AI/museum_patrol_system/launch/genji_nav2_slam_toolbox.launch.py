from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.substitutions import AndSubstitution, LaunchConfiguration, NotSubstitution
from launch_ros.actions import LifecycleNode, Node
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition
import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_launch_description():
    params_file = LaunchConfiguration('params_file')
    slam_params_file = LaunchConfiguration('slam_params_file')
    map_file_name = LaunchConfiguration('map_file_name')
    map_yaml = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    log_level = LaunchConfiguration('log_level')
    use_lifecycle_manager = LaunchConfiguration('use_lifecycle_manager')

    slam_node = LifecycleNode(
        parameters=[
            slam_params_file,
            {'map_file_name': map_file_name},
            {'use_lifecycle_manager': use_lifecycle_manager, 'use_sim_time': use_sim_time},
        ],
        package='slam_toolbox',
        executable='localization_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        namespace='',
        remappings=[('/map', '/slam_toolbox_map')],
    )

    configure_slam = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        ),
        condition=IfCondition(AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))),
    )

    nav2_nodes = [
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
        ),
        ExecuteProcess(
            cmd=[
                'python3',
                os.path.join(_PKG_ROOT, 'scripts', 'genji_slamtoolbox_pose_bridge.py'),
                map_file_name,
            ],
            cwd=_PKG_ROOT,
            output='screen',
        ),
        TimerAction(
            period=6.0,
            actions=[
                ExecuteProcess(
                    cmd=[
                        'bash',
                        os.path.join(_PKG_ROOT, 'scripts', 'genji_slamtoolbox_activate.sh'),
                        '120',
                    ],
                    cwd=_PKG_ROOT,
                    output='screen',
                ),
            ],
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
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_localization',
            output='screen',
            arguments=['--ros-args', '--log-level', log_level],
            parameters=[
                {'autostart': autostart},
                {'node_names': ['map_server']},
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
            DeclareLaunchArgument('slam_params_file', description='slam_toolbox localization yaml'),
            DeclareLaunchArgument('map_file_name', description='Posegraph base path without extension'),
            DeclareLaunchArgument('map', description='Static map yaml for map_server /map'),
            DeclareLaunchArgument('use_sim_time', default_value='false'),
            DeclareLaunchArgument('autostart', default_value='true'),
            DeclareLaunchArgument('use_lifecycle_manager', default_value='false'),
            DeclareLaunchArgument('log_level', default_value='info'),
            slam_node,
            configure_slam,
            *nav2_nodes,
        ]
    )
