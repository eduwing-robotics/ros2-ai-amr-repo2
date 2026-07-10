# nav_ns_launch.py — tb3_1 네임스페이스로 nav2 controller/planner/bt/waypoint 등만 기동(로봇에서 실행).
# 표준 nav2_bringup navigation_launch.py 대신 Node()를 직접 나열하는 이유:
#   navigation_launch.py는 remappings=[('/tf','tf'),('/tf_static','tf_static')]가 내장돼 있어
#   PushRosNamespace와 결합되면 /tb3_1/tf 로 격리된다. 그런데 이 프로젝트의 bringup/amcl은 공유
#   (비-ns) /tf 를 쓰므로(map 프레임이 여러 로봇 사이 공유돼야 함) 리매핑이 있으면 costmap이 tf를
#   영영 못 찾는다("frame does not exist", 2026-07-01 실측 재현). remappings=[] 로 /tf 전역 공유 유지.
# map_server/amcl은 별도(scripts/_robot_amcl_ns.sh)로 이미 떠 있어야 함 — 여기서 재기동 안 함.
# 사용: patch_nav_params_ns.py로 /home/t1/nav2_tb3_1_params.yaml 생성 후,
#   ros2 launch nav_ns_launch.py  →  lifecycle_manager는 ABI 깨짐 전제이므로 자동활성화 없음,
#   각 노드를 수동 configure→activate 할 것([[urhynix-t1-nav2-lifecycle-abi]]).
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import PushRosNamespace, Node, SetParameter
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    ns = "tb3_1"
    params_file = "/home/t1/nav2_tb3_1_params.yaml"

    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key=ns,
            param_rewrites={"autostart": "false"},
            convert_types=True,
        ),
        allow_substs=True,
    )

    nodes = [
        ("nav2_controller", "controller_server", "controller_server", [("cmd_vel", "cmd_vel_nav")]),
        ("nav2_smoother", "smoother_server", "smoother_server", []),
        ("nav2_planner", "planner_server", "planner_server", []),
        ("nav2_behaviors", "behavior_server", "behavior_server", [("cmd_vel", "cmd_vel_nav")]),
        ("nav2_bt_navigator", "bt_navigator", "bt_navigator", []),
        ("nav2_waypoint_follower", "waypoint_follower", "waypoint_follower", []),
        ("nav2_velocity_smoother", "velocity_smoother", "velocity_smoother", [("cmd_vel", "cmd_vel_nav")]),
        ("nav2_collision_monitor", "collision_monitor", "collision_monitor", []),
    ]

    actions = [PushRosNamespace(ns), SetParameter("use_sim_time", False)]
    for pkg, exe, name, extra_remaps in nodes:
        actions.append(Node(
            package=pkg,
            executable=exe,
            name=name,
            output="screen",
            parameters=[configured_params],
            remappings=extra_remaps,   # /tf, /tf_static 리매핑 없음 — 전역 공유 유지
        ))

    return LaunchDescription([GroupAction(actions)])
