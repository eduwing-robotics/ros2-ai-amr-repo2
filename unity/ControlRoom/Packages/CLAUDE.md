# Packages/

> Unity 패키지 의존성. `manifest.json`이 정본.

## 현재 manifest 핵심

| 패키지 | 버전 | 용도 |
|---|---|---|
| `com.unity.robotics.ros-tcp-connector` | v0.7.0 (**embedded+patched**) | ROS2 ↔ Unity TCP 다리 |
| `com.unity.render-pipelines.universal` | 17.0.4 | URP 렌더링 |
| `com.unity.inputsystem` | 1.17.0 | 신 입력 시스템 |
| `com.unity.ugui` | 2.0.0 | UI 기본 |
| `com.unity.modules.uielements` | 1.0.0 | UI Toolkit |
| `com.unity.ai.navigation` | 2.0.9 | NavMesh |
| `jp.keijiro.pcx` | commit `ffc3447`(master) | PLY 점군 임포터+렌더러(RTAB-Map 3D 탭용, Mesh 컨테이너 모드). ⚠️ 태그(v0.1.5)는 구 `Assets/Pcx` 레이아웃이라 `Packages/jp.keijiro.pcx` 경로엔 커밋해시로만 고정 가능 |

## 추가 예정 (Phase별)

| Phase | 패키지 | 비고 |
|---|---|---|
| 6 | URDF Importer (git URL or community fork) | Unity 6 호환성 smoke 후 결정 |
| 7 | Supabase Unity (kamyker fork or NuGetForUnity) | UniTask 의존 |
| 7 | UniTask | Supabase 비동기 |

## ros-tcp-connector embed+patch (2026-06-29)

- git URL 의존을 **`Packages/com.unity.robotics.ros-tcp-connector/`로 embed**했다 (manifest 줄 제거). 이유: 멀티 endpoint race 패치를 PackageCache에 두면 재import 시 덮어쓰므로 영구화.
- 패치: `Runtime/TcpConnector/ROSConnection.cs` `ReadMessageContents`의 static `s_FourBytes`/`s_TopicScratchSpace` → 호출별 로컬 버퍼(`fourBytes`/`topicScratch`). 2개 reader 스레드(로봇별 ROSConnection) race로 2번째 연결이 "No more data available"로 끊기던 것 해결.
- upstream 갱신 시 폴더 통째 교체 후 위 패치 재적용. 폴더 안에 우리 파일 박지 말 것(diff 보존).

## 규칙

- 패키지 추가는 `manifest.json` 편집 후 Unity 자동 fetch.
- git URL 의존은 commit hash 또는 tag 잠금 (floating reference 금지).
- 사용 안 하는 패키지는 즉시 제거 (Library 캐시 크기 절약).
