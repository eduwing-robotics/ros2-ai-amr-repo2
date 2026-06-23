# ROS2 Robot Tech Ref

ROS2, TurtleBot3, SLAM/Nav2, robot bringup 작업의 빠른 진입점이다.

## Read First

1. `docs/ref/TECH-INDEX.md`
2. `docs/ref/ARCHITECTURE.md`
3. `docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md`
4. `.claude/skills/slam-nav2-arena-survey/SKILL.md` for SLAM/Nav2 survey work
5. `scripts/tb3.sh` for helper aliases and robot connection flow

## Current Truth

- ROS domain: `ROS_DOMAIN_ID=210`. (2026-06-15 210으로 통일, cross-discovery PASS)
- `tb3_1` / T1: vision-centered robot, host `t1@192.168.0.250`, hostname `rb`.
- `tb3_2` / Genji: sensor and confirmation robot, host `urhynix-robot`.
- Robot-side SLAM/Nav2 runs on Raspberry Pi or Linux robot host, not macOS Docker.
- RPi build rule: use `colcon build --symlink-install --parallel-workers 1 --executor sequential`.
- Do not delete `~/turtlebot3_ws/build`; install hooks can depend on build artifacts.

## Safe Shutdown

Use this when leaving the lab, ending a hardware session, or stopping LiDAR/camera motors for transport.

1. Stop long-running ROS/process bridges first.
   - Preferred helper path when available: `tb3-down`.
   - T1 manual fallback:
     ```bash
     ssh t1@192.168.10.250 'pkill -f robot.launch.py; pkill -f default_server_endpoint; pkill -f turtlebot3_ros; pkill -f single_coin_d4; pkill -f realsense2_camera; pkill -f web_video_server; pkill -f foxglove_bridge; true'
     ```
2. Shut down the robot OS over SSH.
   ```bash
   ssh t1@192.168.10.250 'sudo poweroff'
   # or for Genji:
   ssh urhynix-robot 'sudo poweroff'
   ```
3. Verify OS halt.
   ```bash
   ping -c 2 -W 1500 192.168.10.250
   # PASS when 100% packet loss after the shutdown grace period.
   ```
4. Only after ping loss, turn the TurtleBot main slide switch OFF.
5. Disconnect or isolate LiPo for transport/charging.

Rules:
- Do not use the main slide switch as the normal first shutdown step while SSH still works; halt the OS first.
- If SSH is frozen or the robot is unsafe, physical power OFF is allowed as emergency recovery, then document it.
- OpenCR USB power can make devices appear alive even when the main switch is OFF; verify Dynamixel power separately during bringup.

## Verify

- Robot connection: `ssh urhynix-robot hostname`.
- Topic smoke: `/scan`, `/odom`, `/battery_state`, `/tf` for TurtleBot basics.
- SLAM output: map saved under robot `~/maps/<name>.{pgm,yaml}` and local evidence/docs location when copied.
- Unity bridge: ROS-TCP endpoint listens and Unity subscribes to expected topics.
