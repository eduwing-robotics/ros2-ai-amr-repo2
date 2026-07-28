from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    carto_config_dir = LaunchConfiguration('carto_config_dir')
    carto_lua = LaunchConfiguration('carto_lua')
    use_sim_time = LaunchConfiguration('use_sim_time')
    resolution = LaunchConfiguration('resolution')
    publish_period_sec = LaunchConfiguration('publish_period_sec')

    return LaunchDescription(
        [
            DeclareLaunchArgument('carto_config_dir', description='Cartographer lua directory'),
            DeclareLaunchArgument(
                'carto_lua',
                default_value='cartographer_arena_mapping.lua',
            ),
            DeclareLaunchArgument('use_sim_time', default_value='false'),
            DeclareLaunchArgument('resolution', default_value='0.02'),
            DeclareLaunchArgument('publish_period_sec', default_value='1.0'),
            Node(
                package='cartographer_ros',
                executable='cartographer_node',
                name='cartographer_node',
                output='screen',
                parameters=[{'use_sim_time': use_sim_time}],
                arguments=[
                    '-configuration_directory', carto_config_dir,
                    '-configuration_basename', carto_lua,
                ],
                remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            ),
            Node(
                package='cartographer_ros',
                executable='cartographer_occupancy_grid_node',
                name='cartographer_occupancy_grid_node',
                output='screen',
                parameters=[
                    {'use_sim_time': use_sim_time},
                    {'resolution': resolution},
                    {'publish_period_sec': publish_period_sec},
                ],
                remappings=[('/tf', 'tf'), ('/tf_static', 'tf_static')],
            ),
        ]
    )
