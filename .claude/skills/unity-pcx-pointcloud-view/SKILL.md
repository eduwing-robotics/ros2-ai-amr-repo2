---
name: unity-pcx-pointcloud-view
description: Unity ControlRoom "3D" 맵 탭에 RTAB-Map RGB-D 컬러 점군(.ply)을 jp.keijiro.pcx 패키지로 렌더링하고, 2D SSOT맵/AMCL과 같은 map-frame 좌표계로 정렬하는 절차. "3D 탭에 점군 렌더링", "유니티에 점군 넣어줘", "Pcx 패키지", "점군 좌표 정렬" 요청에 발동. git 패키지 서브폴더 경로가 태그마다 바뀌는 함정, 정점 직접변환으로 회전합성 혼동 회피, 점 크기 튜닝, 같은 Offset을 쓰는 여러 3D뷰의 카메라 상호간섭을 레이어로 분리, 그리고 "성긴 점군은 클릭 좌표입력에 안 맞는다"는 스코프 결정까지 포함. (2026-07-03 구현+역할재정의 완료)
tags: [unity, pcx, pointcloud, rtabmap, urhynix]
version: 1
---

# Unity Pcx 점군 뷰 (3D 탭)

RTAB-Map이 만든 컬러 점군(.ply)을 Unity ControlRoom의 "3D" 탭에서 자유 궤도 카메라로 보여준다. 좌표계를 2D SSOT맵(arena_shared)/2.5D와 맞춰서 웨이포인트 마커가 같은 자리에 뜨게 한다.

## Use When

- "3D 탭에 실제 점군 보여줘", "RTAB-Map 결과 유니티에 넣어줘"
- 이미 [[rtabmap-bag-to-ply]]로 PLY를 뽑아둔 상태에서 Unity 표시가 다음 단계일 때

## 핵심 결정 — 3D는 보기 전용

**2D=좌표입력 기준(정확), 2.5D=시각맥락+정확한 클릭(바닥평면 레이캐스트 안정적), 3D(점군)=보기 전용.** 성긴 점군은 화면 각도/줌마다 클릭 판정이 근본적으로 불안정해서(무한평면 레이캐스트는 방 밖 먼 좌표로 튐, 최근접점 피킹도 실사용에서 불안정) 클릭-좌표입력 기능은 만들지 않는다. 전문 점군 툴(CloudCompare 등)도 단순 클릭으로 정확한 좌표를 안 주는 이유가 이거다. 3D는 "실제로 어떻게 생겼나" 확인용, 웨이포인트는 2D/2.5D에서 찍는다.

## 절차

### Step 1 — Pcx 패키지 설치

`Packages/manifest.json`에 git URL 의존 추가:
```json
"jp.keijiro.pcx": "https://github.com/keijiro/Pcx.git?path=/Packages/jp.keijiro.pcx#<커밋해시>"
```

**⚠️ 태그(v0.1.5 등)는 구 레이아웃(`Assets/Pcx/`)이라 `Packages/jp.keijiro.pcx` 경로가 없다** — `path=` 서브폴더 구조는 최근 리팩터(태그 없음)에만 있음. `gh api repos/keijiro/Pcx/contents/Packages?ref=<태그>`로 그 태그 시점에 해당 경로가 실제 있는지 먼저 확인하고, 없으면 `gh api repos/keijiro/Pcx/commits/master --jq '.sha'`로 최신 커밋 해시를 받아 그걸로 고정(project 규칙상 tag/hash 고정 필수, floating 금지).

새 git 패키지는 **에디터 재시작이 필요할 수 있다** — `unityctl asset refresh`만으론 `packages-lock.json`에 안 걸릴 수 있고(`resolved: 0.0.0, lock: null`), `unityctl package resolve --project <P> --json`으로 `hasMismatch`/`recommendedNextCommand` 확인 → 안내대로 에디터 종료(`kill -15 <PID>`, `osascript quit`이 안 먹힐 수 있음)→재실행.

### Step 2 — PLY를 Resources에 배치

`Assets/Resources/PointClouds/<이름>.ply`에 정리된(clean) PLY를 둔다. Pcx의 `PlyImporter`(ScriptedImporter)가 자동으로 Mesh 컨테이너 프리팹을 만든다(기본값, 컨테이너타입 변경 불필요 — Mesh 모드가 MeshFilter+MeshRenderer라 코드에서 바로 다루기 쉬움). `Resources.Load<GameObject>("PointClouds/<이름>")`로 런타임 로드.

PLY에 `element camera`/`element face` 같은 비표준 요소가 있으면(PCL/RTAB-Map 기본 export) CloudCompare 등에서 파싱 에러 날 수 있음(별개 이슈지만 Pcx importer 자체는 안 알려진 property를 4바이트 단위로 안전하게 스킵하므로 무관 — vertex만 정상 파싱됨).

### Step 3 — map-frame 좌표 정렬 (정점 직접 변환)

RTAB-Map 점군은 자기 odom 프레임 기준. 2D/2.5D와 같은 좌표계로 맞추려면 [[rtabmap-bag-to-ply]]에서 구한 map↔odom SE2 변환(θ, tx, ty)을 적용한다.

**⚠️ Unity Transform의 회전 합성(`Quaternion.Euler` 체이닝)으로 하지 말 것** — ROS(Z-up,우수좌표계)→Unity(Y-up,좌수좌표계) 축변환 + 평면 회전정렬을 동시에 하려면 부호/핸디니스가 꼬이기 쉽다(직접 검산해도 여러 번 틀림). 대신 **정점 좌표 자체를 명시적 공식으로 재계산**:
```csharp
float mapX = cosT * v.x - sinT * v.y + Tx;
float mapY = sinT * v.x + cosT * v.y + Ty;
verts[i] = new Vector3(mapX, v.z, mapY);  // 높이(z)는 그대로 Unity Y로
```
이후 GameObject의 `transform.localRotation = Quaternion.identity`, `localPosition = Map25DView.Offset`만 설정하면 끝 — Map25DView가 쓰는 `Offset+(mapX,0,mapY)` 규약과 자동으로 맞아떨어진다.

### Step 4 — 점 크기 튜닝

Pcx "Default Point" 머티리얼의 `_PointSize`(기본 0.05=5cm)가 밀도 높은 점군(방 2m권에 10만+ 점)에는 너무 커서 점들이 서로 겹쳐 매끈한 덩어리로 보인다. 인스턴스 머티리얼(`renderer.material`, `sharedMaterial` 아님 — 패키지 공유 에셋 안 건드림)에서 `_PointSize`를 0.008~0.012 정도로 축소하면 점 사이 틈이 보여서 "점군답게" 보인다. `_Tint`(기본 50% 회색)도 `Color.white`로 복원하면 원래 RGB 색이 살아남.

### Step 5 — 같은 Offset을 쓰는 다른 3D뷰와 카메라 격리

2.5D(Map25DView)와 3D 점군이 좌표정렬을 위해 같은 `Offset`을 공유하면, 두 카메라 다 `cullingMask` 기본값(everything)이라 **서로의 콘텐츠가 다 보이는 버그**가 생긴다(2.5D 벽이 3D에도, 3D 점군이 2.5D에도 뜸). Unity 레이어(예: 9번, 이름 없어도 됨 — `TagManager.asset` 안 건드리고 `gameObject.layer = 9` 코드로 충분)로 점군 콘텐츠만 분리하고:
```csharp
// 점군쪽 카메라
cam.cullingMask = 1 << 9;
// 2.5D쪽 카메라
cam.cullingMask = ~(1 << 9);
```
자식 오브젝트까지 재귀적으로 레이어 세팅하는 걸 잊지 말 것(`SetLayerRecursively` 헬퍼).

### Step 6 — 자유 카메라 + 웨이포인트 마커 표시(유지)

`Map3DOrbitController`(2.5D와 공유)의 pitch/zoom 클램프를 생성자 옵션 파라미터로 빼서, 3D 점군은 실사 재구성이니 훨씬 넓은 범위(pitch -89~89, zoom 0.1~6배) 사용, 2.5D는 기존 스키매틱 클램프(15~80°, 0.3~2.5배) 유지. `Map25DPatrolMarkerLayer`도 `layer`/`billboardCam` 파라미터를 추가해 2.5D/3D 양쪽에서 재사용(번호라벨은 `TextMesh`+`Billboard`(카메라 향해 회전하는 작은 컴포넌트)로 표시).

## 함정표

| 증상 | 원인 | 해결 |
|---|---|---|
| manifest.json 수정+asset refresh 해도 패키지 안 잡힘 | `packages-lock.json`에 안 걸림(git 패키지 첫 fetch는 refresh만으론 부족) | `unityctl package resolve --json`으로 상태 확인, 필요시 에디터 재시작 |
| `Cannot checkout repository ... pathspec 'Packages/xxx' did not match` | 지정한 태그 시점엔 그 서브폴더 구조가 없음 | 최신 커밋 해시로 고정(Step 1 참고) |
| 점군이 매끈한 덩어리로 보임("구름 같지 않다") | `_PointSize` 과대 | Step 4 |
| 2.5D/3D 각자 봐야 할 것 말고 서로의 콘텐츠까지 다 보임 | 같은 Offset+카메라 cullingMask 기본값(everything) | Step 5 |
| 우클릭 좌표 찍기가 3D에서 자꾸 엉뚱한 곳/무반응 | 성긴 점군 특성상 클릭 판정 자체가 불안정(무한평면도, 최근접점 피킹도 실패) | 기능을 아예 빼고 3D는 보기 전용으로(위 "핵심 결정") — 억지로 안정화하려 하지 말 것 |

## 재사용 스크립트/파일

- `Assets/Scripts/Map/Map3DPointCloudView.cs` — 점군 로드+정렬+카메라+마커
- `Assets/Scripts/Map/Map3DOrbitController.cs` — pitch/zoom 범위 파라미터화(2.5D 기본값 보존)
- `Assets/Scripts/Map/Map25DPatrolMarkerLayer.cs` — layer/billboardCam 파라미터로 2.5D/3D 공용
- `Assets/Scripts/Map/Billboard.cs` — 텍스트 라벨이 카메라 향하게

## 검증 (2026-07-03 PASS)

`arena_shared_room.ply`(170K pts, 실측 방 bbox 크롭+SOR필터 정리본) → Pcx 임포트+정렬+렌더 → 3D 탭에서 자유 궤도(위/아래 포함) 확인, 웨이포인트 마커+번호 표시 확인, 2.5D와 상호간섭 없음 확인. 클릭-좌표찍기는 시도 후(최근접점 피킹까지 구현) 불안정 확인돼 제거 — 역할재정의로 최종 스코프 확정.

## 관련

[[rtabmap-bag-to-ply]](PLY 생성+정합검증, map↔odom 변환 계산 출처) · [[urhynix-t1-amcl-saved-map]](맵/좌표계 배경)
