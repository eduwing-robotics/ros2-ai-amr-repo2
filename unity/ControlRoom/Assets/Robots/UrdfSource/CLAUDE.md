# Assets/Robots/UrdfSource/

> ROBOTIS 공식 TurtleBot3 URDF 원본 (vendored).

## 예정 자산

- `turtlebot3_description/urdf/turtlebot3_burger.urdf` + 의존 mesh
- `turtlebot3_description/urdf/turtlebot3_waffle_pi.urdf` + 의존 mesh (옵션)

## 가져오기

```bash
# 1회 fetch, commit hash 잠금
git clone --depth 1 -b jazzy https://github.com/ROBOTIS-GIT/turtlebot3.git /tmp/tb3
cp -R /tmp/tb3/turtlebot3_description Assets/Robots/UrdfSource/
git -C /tmp/tb3 rev-parse HEAD > Assets/Robots/UrdfSource/COMMIT.txt
```

## 규칙

- 원본은 vendored. **수정 금지**. Unity 측 커스터마이즈는 `ImportedPrefabs/`에서.
- jazzy 브랜치가 in-progress라 humble fallback 후보로 별도 평가 필요.
- 카메라/추가 센서 부착물은 URDF를 직접 패치하지 않고 Unity child object로 올림 (최종 확정 시 URDF patch 결정).
