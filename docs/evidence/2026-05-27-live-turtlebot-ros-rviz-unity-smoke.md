# Live TurtleBot / ROS2 / RViz / Unity Smoke

Date: 2026-05-27
Robot: TurtleBot3 Burger

## Physical / Network

- Mac host IP: `192.168.0.107`
- Robot IP found by ARP: `192.168.0.138`
- Robot MAC verified: `2c:cf:67:47:38:03`
- SSH port: open on `192.168.0.138:22`
- Robot identity: `kim-desktop`
- OpenCR device: `/dev/ttyACM0`

## TurtleBot Bringup

Started in robot tmux session `bringup`:

```bash
source /opt/ros/jazzy/setup.bash
source ~/turtlebot3_ws/install/setup.bash
export ROS_DOMAIN_ID=56
export TURTLEBOT3_MODEL=burger
export LDS_MODEL=LDS-03
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export ROS_STATIC_PEERS=192.168.0.107
ros2 launch turtlebot3_bringup robot.launch.py
```

Bringup log evidence:

- `Succeeded to open the port(/dev/ttyACM0)!`
- `Start Calibration of Gyro`
- `Activated lidar publish thread for port /dev/tb3_lidar`
- `TOF version lidar start for /dev/tb3_lidar`

## ROS2 Topic Evidence

After `ros2 daemon stop/start`, topics included:

- `/battery_state`
- `/cmd_vel`
- `/imu`
- `/joint_states`
- `/magnetic_field`
- `/odom`
- `/robot_description`
- `/scan`
- `/sensor_state`
- `/tf`
- `/tf_static`

Observed messages:

- `/battery_state`: `12.20V`, `94.44%`
- `/odom`: received one message, frame `odom`, child `base_footprint`
- `/scan`: `average rate: 10.017 Hz`

## RViz

- TigerVNC active: `192.168.0.138:5902`
- RViz binary: `/opt/ros/jazzy/bin/rviz2`
- RViz started in robot tmux session `rviz` with `DISPLAY=:2`
- RViz process observed: `rviz2`

Visual check route:

```text
Mac Screen Sharing -> vnc://192.168.0.138:5902 -> password 123456
```

## Unity ROS-TCP Endpoint

Installed ROS2 branch of Unity ROS-TCP-Endpoint under:

```text
/home/kim/unity_ros_ws/src/ROS-TCP-Endpoint
```

Important detail:

- default `main` branch is ROS1/catkin and failed on ROS2
- switched to `main-ros2`
- built with `colcon build --packages-select ros_tcp_endpoint`

Endpoint started in tmux session `ros_tcp`:

```bash
ros2 run ros_tcp_endpoint default_server_endpoint \
  --ros-args -p ROS_IP:=192.168.0.138 -p ROS_TCP_PORT:=10000
```

Endpoint evidence:

- listening: `192.168.0.138:10000`
- Mac TCP check: `nc` succeeded from `192.168.0.107`

Unity endpoint log:

- `Connection from 192.168.0.107`
- `RegisterSubscriber(/scan, sensor_msgs/LaserScan) OK`
- `RegisterSubscriber(/odom, nav_msgs/Odometry) OK`
- `RegisterSubscriber(/battery_state, sensor_msgs/BatteryState) OK`
- `RegisterSubscriber(/tf, tf2_msgs/TFMessage) OK`

## Unity Mini Project

Created outside the main repo:

```text
/Users/family/jason/UnityRosSmoke
```

Contains:

- `Packages/manifest.json` with `com.unity.robotics.ros-tcp-connector#v0.7.0`
- `Assets/RosSmoke.unity`
- `Assets/Scripts/RosSmokeDashboard.cs`
- `Assets/Editor/RosSmokeConfigure.cs`

Unity GUI launched with:

```bash
open -na /Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app \
  --args -projectPath /Users/family/jason/UnityRosSmoke \
  -executeMethod RosSmokeConfigure.Play \
  -logFile /tmp/unity-ros-smoke-gui-2.log
```

## Notes

- Initial Unity `/scan` subscription hit QoS mismatch because TurtleBot LaserScan uses Best Effort and ROS-TCP-Endpoint default subscriber used Reliable.
- Endpoint subscriber QoS was patched in `/home/kim/unity_ros_ws/src/ROS-TCP-Endpoint/ros_tcp_endpoint/subscriber.py` to use `QoSReliabilityPolicy.BEST_EFFORT`, then rebuilt and restarted.
- Existing Unity project instance prevented a final batchmode recompile after adding extra `Debug.Log` lines, but the endpoint-side connection and subscriber registration were already verified.

## Session Teardown / Current State

- User requested a clean disconnect after the successful smoke path.
- Robot tmux sessions `bringup`, `rviz`, and `ros_tcp` were stopped.
- `192.168.0.138:10000` was verified closed after stopping ROS-TCP-Endpoint.
- TigerVNC `5902` may remain listening as a standing remote-display service; this is separate from ROS/RViz bringup.
- LiDAR may keep physically spinning briefly after node shutdown depending on driver/device state; power cycle if a hard physical stop is required.

## Convenience Helpers / Skillization

Mac helper aliases/functions were added to:

```text
/Users/family/.zshrc
```

Available after `source ~/.zshrc` or a new Mac terminal:

- `tb3-help`: show helper summary
- `tb3-ip`: rediscover the TurtleBot IP by MAC `2c:cf:67:47:38:03`
- `tb3-ssh`: SSH to the discovered robot as `kim`
- `tb3-vnc`: open Mac Screen Sharing to `vnc://<robot-ip>:5902`
- `tb3-port`: check ROS-TCP port `10000`
- `tb3-unity`: launch `/Users/family/jason/UnityRosSmoke`

Robot helper installer was copied to:

```text
/tmp/install_tb3_helpers.py
```

Final robot-side installation is pending because SSH to `192.168.0.138:22` timed out after teardown, even though ARP still showed the known MAC. When the robot is reachable again, run on the robot:

```bash
python3 /tmp/install_tb3_helpers.py
source ~/.bashrc
tb3-help
```

Expected robot helpers after install:

- `tb3-status`
- `tb3-bringup`
- `tb3-restart-bringup`
- `tb3-log`
- `tb3-topics`
- `tb3-rviz`
- `tb3-restart-rviz`
- `tb3-tcp`
- `tb3-restart-tcp`
- `tb3-tcp-log`
- `tb3-stop`

The reusable Codex skill was created and validated at:

```text
/Users/family/.codex/skills/urhynix-turtlebot-unity-ros2-success-pattern/SKILL.md
```
