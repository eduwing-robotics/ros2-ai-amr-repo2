# Unity Tech Ref

URHYNIX Unity 작업의 빠른 진입점이다. 현재 관제 UI 구현은 `unity/ControlRoom`이 우선이고, `unity-src`는 기존 Unity 하네스/패턴 참고원이다.

## Read First

1. `docs/ref/TECH-INDEX.md`
2. `unity/ControlRoom/README.md`
3. `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md`
4. 필요 시 `unity-src/CLAUDE.md`
5. C# 구현 패턴 참고가 필요하면 `unity-src/docs/ref/csharp-master-harness.md`, `unity-src/docs/ref/code-patterns.md`

## Current Truth

- Unity version: `6000.3.16f1` (Unity 6.3 LTS).
- Current project: `unity/ControlRoom`.
- UI stack: UI Toolkit (`UXML`, `USS`, binder C#).
- ROS bridge: `com.unity.robotics.ros-tcp-connector` v0.7.0.
- Camera topics:
  - Genji Pi Camera: `/tb3_2/camera/image_raw/compressed`
  - T1 D435 RGB: `/tb3_1/camera/color/image_raw/compressed`
- Supabase policy: Unity client never receives `service_role`; use anon/RLS and restricted write paths only.

## When Editing

- Read the target file before editing.
- Keep `unity/ControlRoom` as the implementation target unless the request explicitly says `unity-src`.
- Use `unity-src` as pattern/reference only when ControlRoom has no local equivalent yet.
- For camera panel work, prefer `.claude/skills/unity-camera-panel/SKILL.md`.
- For robot/camera bringup evidence, prefer `.claude/skills/robot-camera-bringup/SKILL.md`.

## Verify

- First-open/import smoke: Unity Hub opens `unity/ControlRoom` without package resolution errors.
- Compile smoke: Unity Editor compile after package import.
- Camera UI smoke: Genji and T1 compressed topics render in the Unity panel when ROS2 topics are live.
- Doc sync: update `docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` and `docs/status/PROJECT-STATUS.md` if phase, version, or verified camera behavior changes.

