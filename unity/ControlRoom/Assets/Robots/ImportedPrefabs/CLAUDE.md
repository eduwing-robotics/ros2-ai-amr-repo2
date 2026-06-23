# Assets/Robots/ImportedPrefabs/

> Unity URDF Importer가 생성한 prefab + 커스터마이즈.

## 예정 자산

- `TurtleBot3Burger.prefab` — Burger URDF import 결과
- `TurtleBot3WafflePi.prefab` — Waffle Pi (옵션)
- `RobotModelMap.asset` — `robot_id` ↔ prefab 매핑 ScriptableObject

## 규칙

- prefab 안에 ArticulationBody가 자동 생성됨 (URDF Importer 의존).
- 추가 카메라/센서 부착물은 prefab에 child GameObject로 올림.
- 원본 URDF의 mesh/joint 구조는 변경하지 않음. 변경 필요 시 `UrdfSource/`의 URDF를 패치한 뒤 재import.

## 호환성 주의

Unity 6 + URDF Importer 호환성 미검증. fallback 후보:
- gkjohnson/urdf-loaders (Unity 패키지)
- 사전 변환된 prefab을 직접 받기
- 마지막 수단: 단순 mesh + 수동 prefab
