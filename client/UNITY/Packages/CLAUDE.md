# Packages/

> Unity 패키지 의존성. `manifest.json`이 정본.

## 현재 manifest 핵심

| 패키지 | 버전 | 용도 |
|---|---|---|
| `com.unity.robotics.ros-tcp-connector` | embedded `0.7.0-preview` | ROS2 ↔ Unity TCP 다리, multi-endpoint race patch 포함 |
| `com.unity.render-pipelines.universal` | 17.0.4 | URP 렌더링 |
| `com.unity.inputsystem` | 1.17.0 | 신 입력 시스템 |
| `com.unity.ugui` | 2.0.0 | UI 기본 |
| `com.unity.modules.uielements` | 1.0.0 | UI Toolkit |
| `com.unity.ai.navigation` | 2.0.9 | NavMesh |
| `jp.keijiro.pcx` | commit `ffc3447`(master) | PLY 점군 임포터+렌더러(RTAB-Map 3D 탭용, Mesh 컨테이너 모드). ⚠️ 태그(v0.1.5)는 구 `Assets/Pcx` 레이아웃이라 `Packages/jp.keijiro.pcx` 경로엔 커밋해시로만 고정 가능 |

## 규칙

- 패키지 추가는 `manifest.json` 편집 후 Unity 자동 fetch.
- git URL 의존은 commit hash 또는 tag 잠금 (floating reference 금지).
- 사용 안 하는 패키지는 즉시 제거 (Library 캐시 크기 절약).
- 이 문서는 `manifest.json`의 실제 상태와 항상 함께 갱신한다.

## ROS-TCP-Connector resolver 상태

- 실제 lock source는 `packages-lock.json`의 `file:com.unity.robotics.ros-tcp-connector` / `embedded`다.
- `Packages/com.unity.robotics.ros-tcp-connector/`의 `ROSConnection.cs`에는 reader별 로컬 buffer를 사용하는 multi-endpoint race patch가 있다.
- `manifest.json`의 v0.7.0 git URL은 원본 출처를 잠그는 fallback이며, 현재 프로젝트에서는 embedded package가 우선한다.
- upstream으로 교체할 때는 patch 유실 여부와 `packages-lock.json` source를 함께 확인한다.
