# Assets/Robots/

> URDF 원본 + Unity URDF Importer 결과 prefab.

## 폴더

- `UrdfSource/` — ROBOTIS 공식 TurtleBot3 URDF 원본 (jazzy 브랜치)
- `ImportedPrefabs/` — Unity URDF Importer 결과 prefab

## 워크플로

1. ROBOTIS `turtlebot3/jazzy/turtlebot3_description`을 `UrdfSource/`에 복사.
2. Unity URDF Importer 설치 (Unity 6 호환성 smoke 먼저).
3. `*.urdf` import → prefab을 `ImportedPrefabs/`에 저장.
4. `RobotModelMap.asset`(예정)에서 `robot_id` ↔ prefab 매핑.
5. `Scripts/Map/Robot3DSpawner.cs`가 매핑 읽어 3D 화면에 spawn.

## 주의

- URDF 원본과 import 결과는 분리 (원본은 vendored, import 결과만 변경 가능).
- 가져온 commit hash를 `RobotModelMap.asset` 메모에 남겨 재현성 확보.
- Unity 6에서 URDF Importer 호환성 미검증. fallback: gkjohnson/urdf-loaders 또는 사전 변환 prefab.
