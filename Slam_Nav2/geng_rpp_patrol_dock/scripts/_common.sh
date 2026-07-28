#!/usr/bin/env bash
# Foreground child-process helpers — source only.
# Pattern: start children in background, main process blocks; Ctrl+C kills all children.

_FG_CHILD_PIDS=()

fg_register_trap() {
  trap 'fg_cleanup "INT"' INT
  trap 'fg_cleanup "TERM"' TERM
  trap 'fg_cleanup "EXIT"' EXIT
}

fg_add_child() {
  _FG_CHILD_PIDS+=("$1")
}

fg_start() {
  # fg_start <name> command...
  local name="$1"
  shift
  echo "==> [child] ${name} (pid will follow)"
  "$@" &
  local pid=$!
  fg_add_child "${pid}"
  echo "    pid=${pid}"
}


fg_publish_stop() {
  # TurtleBot driver has no reliable stale-command watchdog on this setup.
  # Publish zero after Nav2 exits so the last angular command cannot latch.
  timeout 3 ros2 topic pub -r 20 /cmd_vel geometry_msgs/msg/TwistStamped \
    '{header: {frame_id: base_footprint}, twist: {linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}' \
    >/dev/null 2>&1 || true
}

fg_cleanup() {
  local reason="${1:-EXIT}"
  if [[ "${_FG_CLEANUP_DONE:-}" == "1" ]]; then
    return 0
  fi
  _FG_CLEANUP_DONE=1
  if [[ "${#_FG_CHILD_PIDS[@]}" -eq 0 ]]; then
    return 0
  fi
  echo ""
  echo "==> 종료 (${reason}) — 자식 프로세스 정리"
  for pid in "${_FG_CHILD_PIDS[@]}"; do
    kill -INT "${pid}" 2>/dev/null || true
  done
  sleep 1
  for pid in "${_FG_CHILD_PIDS[@]}"; do
    kill -TERM "${pid}" 2>/dev/null || true
  done
  sleep 0.5
  for pid in "${_FG_CHILD_PIDS[@]}"; do
    kill -KILL "${pid}" 2>/dev/null || true
  done
  fg_publish_stop
  if [[ "${RESTORE_ODOM_TF_ON_EXIT:-0}" == "1" ]]; then
    ros2 param set /diff_drive_controller odometry.publish_tf true >/dev/null 2>&1 || true
  fi
}

fg_stop_local_ros() {
  local domain="${ROS_DOMAIN_ID:-?}"
  echo "==> 로컬 ROS 정리 (DOMAIN=${domain})"
  for pat in \
    scan_normalize.py \
    odom_tf_relay.py \
    ekf_node \
    ekf_filter_node \
    robot_localization \
    slam_toolbox \
    async_slam_toolbox \
    localization_slam_toolbox \
    cartographer \
    tf2_echo \
    component_container_isolated \
    component_container_mt \
    nav2_container \
    nav2_bringup \
    controller_server \
    smoother_server \
    planner_server \
    route_server \
    behavior_server \
    bt_navigator \
    waypoint_follower \
    velocity_smoother \
    collision_monitor \
    lifecycle_manager \
    map_server \
    amcl \
    rviz2; do
    pkill -f "${pat}" 2>/dev/null || true
  done
  ros2 daemon stop 2>/dev/null || true
  sleep 0.5
  ros2 daemon start 2>/dev/null || true
}
