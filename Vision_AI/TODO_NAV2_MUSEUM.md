# Nav2 / Dispatch TODO

## Doing Next

- Re-validate Gen.G with the simple arena profile first.
  - New default params: `museum_patrol_system/config/genji_nav2_arena_simple.yaml`
  - Design intent: `DWB + Navfn`, manual RViz `2D Pose Estimate`, short-goal-first validation.
  - Do not tune patrol/dispatch speed again until the short-goal contract passes.

- Run the new validation contract in order.
  - Stage 1: straight short goal (`30~50cm`) x3.
  - Stage 2: short goal with ~90deg heading change x3.
  - Stage 3: one dispatch-length point-to-point goal.
  - Stage 4: only then re-enter waypoint patrol / dispatch expansion.

- Add keepout zones around exhibits and the two statues.
  - Goal: prevent approach paths from hugging protected assets.
  - Start with static keepout masks for the current `arena_shared` map.

- Add a safe-goal conversion node.
  - Event position should not be sent directly to Nav2.
  - Convert `person_intrusion` / `fire` to a standoff response pose.
  - Candidate node name: `safe_goal_generator.py`.

- Add response pose data file.
  - Create `museum_response_poses.yaml`.
  - Define temporary slots first, replace with teleop-captured coordinates later.

- Route dispatch through one or two safe hubs when needed.
  - Use `NavigateThroughPoses` only for dispatch.
  - Keep normal patrol on `FollowWaypoints`.

- Extend the existing task manager instead of creating a second one.
  - Add flow: `EVENT_DETECTED -> MAKE_SAFE_GOAL -> DISPATCH -> ARRIVED`.
  - Keep the current actuator logic and connect it to Nav2 dispatch only where needed.

- Add fake-event test path.
  - Test `fire` and intrusion flows without YOLO/sensor hardware.
  - Validate: event -> safe goal -> dispatch -> arrival.

## Ambiguous / Decide Later

- Separate patrol speed from dispatch speed.
  - The new simple profile is deliberately shared for short-goal validation.
  - If dispatch should stay faster later, split profile after Stage 3 passes:
    - separate controller plugin/profile, or
    - separate Nav2 params/BT path for dispatch.

- Full topological waypoint graph.
  - Do this only if simple hub-based dispatch still fails.
  - Start with fixed hubs instead of a full graph.

- Fine-tune goal tolerance / inflation after keepout is added.
  - Tightening too early may block narrow passages.

- Add obstacle layer to the global costmap.
  - Current design intentionally keeps global costmap simple.
  - Revisit only if static-map planning proves insufficient.

- Create a single all-in-one museum navigation launch.
  - Low priority while bringup and laptop Nav2 remain intentionally split.

- Automatic response-robot selection.
  - Base rule remains:
    - T1 = patrol
    - Gen.G = dispatch
  - Exception scenario to support later:
    - if T1 battery is low, Gen.G temporarily takes patrol,
      and T1 goes to standby/charge.

- Person intrusion during open hours.
  - Current project intent is actuator-based response, not Nav2 chase.
  - Keep this separated from dispatch navigation logic.
