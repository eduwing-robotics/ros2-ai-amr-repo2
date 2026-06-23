# 3D 디지털트윈 아키텍처 결정 + 자료조사 근거 (2026-06-17)

> RealSense 기반 실시간 3D 디지털트윈 방향을 자료조사(소넷 3갈래 병렬, 출처 60개)로 근거 보강해 잠근 기록.
> 결정 주체: 주인님. 조사·종합: 메인(Opus) + 소넷 서브에이전트 3.

## 1. 결정 (LOCKED)

기존 "RealSense depth → depthimage_to_laserscan(가짜 LiDAR) → 2D slam_toolbox" 방식은 **3D 정보를 납작하게 버리므로 디지털트윈 목표에 부적합 → 폐기.**

| 트랙 | 방식 |
|------|------|
| **2D 점유격자** | **LiDAR(LDS-03) → slam_toolbox → /map → Unity 2D 패널** (기존 검증 경로 유지) |
| **3D 재구성** | **RealSense D435 → RTAB-Map(RGB-D SLAM) → 3D 클라우드/메시 → Unity 런타임 컴포넌트** |
| **연산 배치** | **하이브리드: Pi=캡처+압축, Mac=RTAB-Map 본체** (오프로드) |
| **Unity 3D 표시** | **둘 다** — 라이브 포인트클라우드(파티클) + 주기적 메시 임포트(glTFast, 1~5초) |
| **unityctl 역할** | 무대 셋업·검증만 (실시간 빌더 아님 — 아래 기대치 교정) |

목표 재정의: **"near-real-time 1:1 3D 트윈"** — 로봇이 RealSense로 재구성, Unity는 받아서 렌더. per-frame 실시간 메시는 비현실, 메시는 0.5~2초 지연·포인트클라우드는 라이브.

### ⚠️ 기대치 교정 (조사로 드러난 것)
"unityctl로 실시간 1:1 자동 생성"은 **불가**. unityctl(배치/에디터 자동화)은 일회성 GameObject 생성·셋업만 가능하고, **실시간 토픽 구독·per-frame 렌더는 Unity Play Mode 런타임 컴포넌트**의 일이다. 라이브 3D는 런타임 구독자가 담당하고 unityctl은 사전 무대 구성·검증을 맡는다.

## 2. 채택 아키텍처

```
[Pi · 티원] RealSense D435 (30FPS, USB3)
   ├─ depth: Temporal RVL 압축 (~8 Mbps)
   ├─ rgb:   H.264 압축 (~2-3 Mbps)
   └─ /tf 포즈 (50-100Hz, 경량)
        │  WiFi ~20Mbps (총 ~12-15Mbps, 5-8Mbps 여유)
        ▼
[Mac] RTAB-Map 본체 (RGB-D SLAM, 루프클로저, 메시 생성)
   ├─ /map_cloud (데시메이션 포인트클라우드)
   └─ mesh.glb 주기 내보내기 (1~5초)
        │
        ▼
[Unity 6000.3.16f1 · Play Mode 런타임]
   ├─ /tf 구독 → 로봇 마커/포즈 (실시간)
   ├─ PointCloud2 구독 → 파티클 렌더 (라이브, ~30만~100만 점)
   └─ mesh.glb 폴링 → glTFast 런타임 로드 → 환경 메시 교체 (0.5~2초)
[unityctl] 씬 사전 셋업 + 검증만
```

## 3. 자료조사 종합 (3갈래)

### A. 3D 엔진 — RTAB-Map 만장일치
- production급(2013~), BSD(OpenCV nonfree 미사용 시), **ROS2 Jazzy 네이티브**(`ros-jazzy-rtabmap`).
- D435(IMU 없음) 검증됨 — VO + 루프클로저. **3D 클라우드/메시 + 2D 격자 동시** 산출.
- 대안: octomap_server(가벼움·루프클로저 없음), voxblox(ROS2 포팅 비공식), nvblox(**CUDA 필수 → Apple Silicon 불가**), Gaussian Splatting(연구단계).

### B. 연산 배치 — 하이브리드 권장
- **Pi4 단독 RTAB-Map = 10~15FPS·RAM ~430MB로 빠듯** → 실시간 3D 부족.
- D435 on Pi4: 640×480@30 depth+RGB는 USB로 가능하나 비압축 ~368Mbps = WiFi 불가.
- 압축: **Temporal RVL(depth) 20.1:1 → ~8Mbps**, H.264(RGB) ~2-3Mbps, Draco(클라우드). 데시메이션 필수.
- 하이브리드(엣지+오프로드)가 cloud-only 대비 지연 39%↓.

### C. Unity 연동 — 라이브 클라우드 + 주기 메시
- PointCloud2는 ROS-TCP-Connector로 역직렬화되나 **렌더러는 직접 구현**(파티클/지오메트리셰이더/컴퓨트버퍼). ~30만 점 이상은 GPU 방식 필요(Pcx/FastPoints 참고).
- 라이브 메시 스트리밍은 비표준 → **RTAB-Map 메시 → .glb 주기 내보내기 → Unity glTFast 런타임 로드**(0.5~2초)가 현실 패턴.
- 디지털트윈 표준: `/tf` 포즈 실시간 + 환경 메시 정적/주기. per-frame 메시 재구성 아님.

## 4. 핵심 리스크
1. **D435 IMU 없음** → VO 드리프트. 루프클로저 + LiDAR 오도메트리 융합으로 완화.
2. **WiFi 대역폭이 최대 제약** (codelab 불안정) → 압축/데시메이션 없으면 실패. [[urhynix-wifi-codelab-status]]
3. **Pi4 단독 불가** → Mac 오프로드 전제. Mac에 ROS2 Jazzy + RTAB-Map 환경 구축 필요.
4. **Unity 3D 컴포넌트 미구현** — 현재 MapView는 2D 전용, 3D 컨테이너는 Phase 6 placeholder. PointCloud2 구독자 + glTFast 로더 신규 개발 필요.
5. **좌표 1:1 정렬** — 2D(LiDAR) `map` 프레임과 3D(RealSense) 재구성 원점 정합.

## 5. 다음 세션 구현 체크리스트
- [ ] Mac에 ROS2 Jazzy + `rtabmap`/`rtabmap_ros` 환경 (Apple Silicon 빌드 경로 확인)
- [ ] 티원: RealSense depth/RGB 압축 전송(image_transport: rvl/ffmpeg) 파이프라인
- [ ] Pi→Mac 대역폭 실측 (Temporal RVL + H.264, 목표 ≤15Mbps)
- [ ] Mac RTAB-Map: `/cloud_map` + 메시 .glb 주기 내보내기
- [ ] Unity: `PointCloudSubscriber.cs`(파티클) + `MeshGlbLoader.cs`(glTFast) 신규 — 3D 컨테이너에 결선
- [ ] 좌표 정합 + 2D(LiDAR)/3D 오버레이 검증

## 6. 출처

### A. 3D 엔진 (20)
RTAB-Map jazzy-devel(github introlab/rtabmap_ros), docs.ros.org rtabmap, D435+RTAB-Map 통합가이드(jacobmoroni wiki, simonbogh repo), RTAB-Map 2024 논문(arxiv 2403.06341), octomap_server Jazzy, voxblox_ros2_minimal(snt-arg), isaac_ros_nvblox(CUDA), librealsense Apple Silicon, RTAB-Map Pi4 3D 스캐너(geoweeknews), KISS-ICP, GS-SLAM, D435 vs D435i(no IMU), 라이선스 파일 3종.

### B. 연산·대역폭 (20)
SLAM-on-Raspberry-Pi(AdroitAnandAI), Pi-SLAM(weixr18), rtabmap_ros#995(CPU벤치), Jetson depth recon(arxiv 1907.07210), Intel RealSense USB2 D435, librealsense RaspberryPi3.md(SDK v2.36), ros-realtime-rpi4-image, Temporal RVL 20.1:1(Stanford VHIL), Cloud Robotics offloading(arxiv 1902.05703), FogROS2(arxiv 2205.09778, H.264 -54% 지연), Edge SLAM(arxiv 2112.13222, -39% 지연), Clearpath camera compression, draco_point_cloud_transport, ORB-SLAM3 on Pi5.

### C. Unity 연동 (16)
ROS-TCP-Connector #310(클라우드 지연), Point-Cloud-Renderer(컴퓨트셰이더, ~100만점), Pcx(keijiro), FastPoints(octree), Unity+ROS 디지털트윈 케이스(PMC11397808), DT path planning(machines14040387), Kimera+D435(ibrahimovnijat), glTFast Runtime 로드 문서, Foxglove mesh markers, PointCloud2Unity(Hydran00, 4렌더방식), ORB-SLAM2+D435i, DT additive manufacturing(arxiv 2501.18016), Unity headless 제약(partiallydisassembled).

## 한줄정리
RealSense 3D 디지털트윈은 **RTAB-Map(Mac 오프로드) + Unity 런타임(라이브 포인트클라우드 + 주기 .glb 메시)** 구조로 잠금. 기존 2D-via-RealSense는 폐기(2D는 LiDAR 유지). unityctl은 실시간 빌더가 아니라 셋업·검증 담당이며, 목표는 per-frame이 아닌 near-real-time(메시 0.5~2초) 1:1 트윈.
