# Assets/Resources/MuseumDecor/

> 2.5D 맵 박물관 스킨 자산. `Map25DView`(Wall.mat)와 `MuseumDecorSpawner`(prefab들)가 Resources.Load로 사용.
> 원본은 `Assets/Gallery Room/` — 메시/텍스처는 GUID 참조 공유(용량 중복 없음).
> Wall.mat 없으면 플랫컬러 폴백, prefab 없으면 해당 장식만 생략(경고 로그).
> 바닥은 파일 없이 코드 생성 그리드(`MakeGridFloorMat`). 장식 배치는 `StreamingAssets/Maps/<slot>.decor.json`.
> `tb3_burger.obj` — ROBOTIS 공식 STL 4종(mm)을 URDF 오프셋 베이크+Unity y-up 미터로 병합(Apache-2.0),
> `Map25DRobotMarkerLayer`가 로봇 마커 실모델로 사용. LightStand는 원작이 7.94m 수평 트랙레일 — 벽당 1개 가로 배치.
