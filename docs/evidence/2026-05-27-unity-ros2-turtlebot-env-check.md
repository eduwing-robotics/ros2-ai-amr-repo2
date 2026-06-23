# Unity / ROS2 / TurtleBot Environment Check

Date: 2026-05-27
Request: Unity, ROS2, TurtleBot 상호작용 테스트 가능 여부 확인. Reference: `Jason-hub-star/turtlebo.git`.

## Intake Verdict

- verdict: `review`
- chosen skill: `task-intake-router`
- next skill: `evidence-review`
- sub-agent needed: no
- reasoning: 코드 구현 전 현재 로컬/봇/Unity/ROS2 상태를 확인하고, 상호작용 스모크 테스트의 가능 여부와 blockers를 판정하는 요청.

## Reference Repository

- URL: `https://github.com/Jason-hub-star/turtlebo.git`
- checked commit: `ab4842cf298c3c806476cb3f35237de97d1305b8`
- notable assets:
  - `scripts/bot-on.sh`, `scripts/nav-up.sh`, `scripts/nav-kill.sh`
  - `code/nav2_goal.py`, `code/waypoint_nav.py`
  - `nav2_params/burger_tune.yaml`, `nav2_params/navigation2_v3.launch.py`
  - `skills/find-turtlebot`, `skills/turtlebot-drive`, `skills/turtlebot-slam`
- important drift: reference repo is ROS 2 Jazzy / Ubuntu 24.04 oriented, while URHYNIX docs currently name ROS 2 Humble / Ubuntu 22.04 in `ros-ws/README.md`.

## Local Environment

- host: macOS 26.3.1, arm64
- network: `en0` active at `192.168.0.107/24`
- Unity editors installed:
  - `/Applications/Unity/Hub/Editor/6000.0.64f1`
  - `/Applications/Unity/Hub/Editor/6000.3.11f1`
- Unity project version: `6000.0.64f1`
- Python: `Python 3.14.3`
- available Python package observed: `psycopg2-binary 2.9.11`
- missing from PATH:
  - `ros2`
  - `colcon`
  - `docker`
  - `unityhub`

## Repository State

- `ros-ws/` currently contains only `README.md`; no ROS2 `src/` packages were present.
- `scripts/check-project.sh` failed because these scaffold files are missing:
  - `src/AGENTS.md`
  - `apps/AGENTS.md`
  - `backend/AGENTS.md`
- `docs/dev-plan.html` parsed successfully with Python `html.parser`.
- Unity package manifest contains `com.unity.robotics.urdf-importer`, but no `com.unity.robotics.ros-tcp-connector` dependency was found.
- Search found no Unity ROS-TCP runtime usage such as `ROSConnection` or `Unity.Robotics.ROSTCPConnector`.

## TurtleBot Reachability

- Reference bot MAC from `turtlebo`: `2c:cf:67:47:38:03`
- Reference last IP: `192.168.0.116`
- Current check:
  - ping to `192.168.0.116` failed
  - SSH BatchMode to `kim@192.168.0.116` timed out
  - local `/24` ARP sweep did not show MAC `2c:cf:67:47:38:03`
- conclusion: the referenced TurtleBot was not reachable from this Mac during this check.

## Unity Batchmode Evidence

Command:

```bash
/Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit \
  -projectPath /Users/family/jason/URHYNIX/unity-src \
  -logFile /tmp/urhynix-unity-batch.log
```

Result:

- Unity package registration started successfully.
- Batchmode exited with code `1`.
- Failure: `Scripts have compiler errors.`
- first representative errors:
  - `KineTutor3D.App.Fairino` namespace missing
  - `KineTutor3D.Kinematics` namespace missing
  - `RobotControlV3RuntimeController`, `RobotControlV3RuntimeSnapshot`, `Waypoint`, `TeachingSequenceBlock` types missing

## Verdict

Current machine cannot yet run an end-to-end Unity ↔ ROS2 ↔ TurtleBot interaction test.

Primary blockers:

1. ROS2 CLI/runtime is not installed or not on PATH on the Mac.
2. `ros-ws` has no ROS2 packages to build or launch.
3. Unity project does not currently include ROS-TCP-Connector runtime wiring.
4. Unity project does not compile in batchmode due to missing application namespaces/types.
5. The referenced TurtleBot is not reachable on the current network.

## Next Test Gate

Minimum gate before interaction smoke:

1. Decide stack alignment: ROS 2 Jazzy from `turtlebo` vs Humble from URHYNIX docs.
2. Make the TurtleBot reachable and verify MAC `2c:cf:67:47:38:03`.
3. Bring up TurtleBot topics: `/scan`, `/odom`, `/tf`, `/battery_state`.
4. Add or scaffold ROS2 packages under `ros-ws/src`.
5. Add Unity ROS-TCP-Connector and a minimal pose/event subscriber scene.
6. Clear Unity compile errors before PlayMode smoke.

