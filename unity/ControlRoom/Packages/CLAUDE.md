# Packages/

> Unity 패키지 의존성. `manifest.json`이 정본.

## 현재 manifest 핵심

| 패키지 | 버전 | 용도 |
|---|---|---|
| `com.unity.robotics.ros-tcp-connector` | v0.7.0 (git URL) | ROS2 ↔ Unity TCP 다리 |
| `com.unity.render-pipelines.universal` | 17.0.4 | URP 렌더링 |
| `com.unity.inputsystem` | 1.17.0 | 신 입력 시스템 |
| `com.unity.ugui` | 2.0.0 | UI 기본 |
| `com.unity.modules.uielements` | 1.0.0 | UI Toolkit |
| `com.unity.ai.navigation` | 2.0.9 | NavMesh |

## 추가 예정 (Phase별)

| Phase | 패키지 | 비고 |
|---|---|---|
| 6 | URDF Importer (git URL or community fork) | Unity 6 호환성 smoke 후 결정 |
| 7 | Supabase Unity (kamyker fork or NuGetForUnity) | UniTask 의존 |
| 7 | UniTask | Supabase 비동기 |

## 규칙

- 패키지 추가는 `manifest.json` 편집 후 Unity 자동 fetch.
- git URL 의존은 commit hash 또는 tag 잠금 (floating reference 금지).
- 사용 안 하는 패키지는 즉시 제거 (Library 캐시 크기 절약).
