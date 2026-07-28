"""Gen.G Nav2 bringup — standalone (no museum_nav_bringup install required)."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_THIS_DIR)


def generate_launch_description():
    nav2_dir = get_package_share_directory("nav2_bringup")
    nav2_launch = os.path.join(nav2_dir, "launch")

    map_yaml = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "map",
                default_value=os.path.join(_PKG_ROOT, "maps", "museum_map.yaml"),
                description="Path to map yaml",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=os.path.join(
                    _PKG_ROOT, "config", "nav2_params_geng_rpp.yaml"
                ),
                description="Nav2 parameters file",
            ),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            DeclareLaunchArgument("autostart", default_value="true"),
            Node(
                package="rclcpp_components",
                executable="component_container_isolated",
                name="nav2_container",
                output="screen",
                parameters=[params_file, {"autostart": autostart}],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(nav2_launch, "localization_launch.py")
                ),
                launch_arguments={
                    "map": map_yaml,
                    "params_file": params_file,
                    "use_sim_time": use_sim_time,
                    "autostart": autostart,
                    "use_composition": "True",
                    "use_respawn": "False",
                    "container_name": "nav2_container",
                }.items(),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(_THIS_DIR, "navigation_arena_launch.py")
                ),
                launch_arguments={
                    "params_file": params_file,
                    "use_sim_time": use_sim_time,
                    "autostart": autostart,
                    "use_composition": "True",
                    "use_respawn": "False",
                    "container_name": "nav2_container",
                }.items(),
            ),
        ]
    )
