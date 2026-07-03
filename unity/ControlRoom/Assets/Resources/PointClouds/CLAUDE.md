# Resources/PointClouds/

> RTAB-Map(D435 RGB-D SLAM) 컬러 점군 `.ply` — `jp.keijiro.pcx` 임포터가 Mesh 컨테이너로 자동 변환.
> `Map3DPointCloudView.cs`가 `Resources.Load<GameObject>("PointClouds/<파일명>")`로 로드해 3D 탭에 인스턴스화.

## 파일 규칙

- 파일명(확장자 제외)이 곧 `Resources.Load` 경로 — 리네임 시 로더 코드도 같이 고칠 것.
- 원본 산출 절차: `docs/evidence/3d_maps/` + `rtabmap-bag-to-ply` 스킬(캡처→PLY→정합검증→정리) → 정리 완료본만 여기 복사.
- PLY는 `x,y,z,red,green,blue`(+ 여분 property는 Pcx가 자동 스킵)를 갖는 `binary_little_endian` 형식이어야 함.
