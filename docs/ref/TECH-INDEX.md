# Technology Ref Index

작업 기술을 먼저 좁히기 위한 얇은 인덱스다. 모든 ref를 한 번에 읽지 말고, 요청 키워드와 파일 경계가 맞는 기술 ref 1개를 먼저 읽은 뒤 필요한 정본 문서로 내려간다.

## Routing Table

| Request hints | Read first | Then read if needed |
|---|---|---|
| Unity, ControlRoom, UI Toolkit, ROS-TCP, 카메라 패널, 씬, UXML/USS | `docs/ref/tech/UNITY.md` | `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md`, `unity/ControlRoom/README.md`, `unity-src/CLAUDE.md` |
| ROS2, TurtleBot, SLAM, Nav2, tb3, robot bringup, LiDAR, map | `docs/ref/tech/ROS2-ROBOT.md` | `docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md`, `.claude/skills/slam-nav2-arena-survey/SKILL.md` |
| Arduino, PIR, sound, temperature, laser, serial, OpenCR power | `docs/ref/tech/ARDUINO-SENSORS.md` | `.claude/skills/arduino-flash/SKILL.md`, `docs/ref/ARCHITECTURE.md`. (정본 v18: LDR·불꽃→온도·레이저·워터펌프 변경, DECISION-LOG 2026-06-16 참조) |
| Supabase, DB, schema, RLS, events, dispatches, camera_captures | `docs/ref/tech/DATABASE-SUPABASE.md` | `docs/ref/SCHEMA.md`, `docs/ref/CONTRACT.md`, `db/migrations/2026-05-27_init_security.sql` |
| camera_ros, RealSense, Pi Camera, compressed image, YOLO, vision | `docs/ref/tech/VISION-CAMERA.md` | `.claude/skills/robot-camera-bringup/SKILL.md`, `.claude/skills/unity-camera-panel/SKILL.md` |
| Claude/Codex harness, skills, intake, evidence, doc sync | `docs/ref/tech/OPS-HARNESS.md` | `.claude/skills/README.md`, `.claude/commands/intake.md` |

## Agent Rule

1. 새 요청은 `/intake` 또는 `task-intake-router`로 verdict를 잡는다.
2. 요청 기술이 명확하면 위 표의 기술 ref만 먼저 읽는다.
3. 기술 ref는 압축 인덱스다. 구현 판단은 연결된 정본 문서와 실제 파일을 다시 읽고 내린다.
4. 기술 ref를 바꿨으면 `PROJECT-PLAN.md`의 `Intake Verdict` 또는 `PROJECT-STATUS.md`의 `Evidence Status`에 근거를 남긴다.
5. 이 폴더 자체의 작성 규칙은 `docs/ref/tech/AGENTS.md`를 따른다.
