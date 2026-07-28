from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, LogInfo, RegisterEventHandler
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.substitutions import AndSubstitution, LaunchConfiguration, NotSubstitution
from launch_ros.actions import LifecycleNode
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition


import os

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_lifecycle_manager = LaunchConfiguration('use_lifecycle_manager')
    slam_params_file = LaunchConfiguration('slam_params_file')
    autostart = LaunchConfiguration('autostart')

    slam_node = LifecycleNode(
        parameters=[
            slam_params_file,
            {'use_lifecycle_manager': use_lifecycle_manager, 'use_sim_time': use_sim_time},
        ],
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        namespace='',
    )

    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_node),
            transition_id=Transition.TRANSITION_CONFIGURE,
        ),
        condition=IfCondition(AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))),
    )

    activate_event = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_node,
            start_state='configuring',
            goal_state='inactive',
            entities=[
                LogInfo(msg='[Gen.G] slam_toolbox SLAM activating'),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_action(slam_node),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        ),
        condition=IfCondition(AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))),
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument('slam_params_file', description='slam_toolbox mapping yaml'),
            DeclareLaunchArgument('use_sim_time', default_value='false'),
            DeclareLaunchArgument('autostart', default_value='true'),
            DeclareLaunchArgument('use_lifecycle_manager', default_value='false'),
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
            slam_node,
            configure_event,
            activate_event,
        ]
    )
