# Assets/Tests/

> Unity Test Framework 테스트 코드 (NUnit 기반). EditMode + PlayMode 분리.

## 폴더

- `EditMode/` — 에디터에서 실행되는 단위 테스트 (Play 모드 진입 없이 즉시)
- `PlayMode/` — Play 모드에서 실행되는 통합 테스트 (Unity runtime 활성)

## 예정 테스트

| 파일 | 영역 |
|---|---|
| `EditMode/RobotInfoTests.cs` | 데이터 클래스 직렬화/역직렬화 |
| `EditMode/FeatureRegistryTests.cs` | Registry 등록/조회 로직 |
| `EditMode/SensorRegistryTests.cs` | Sensor Registry |
| `EditMode/UiTokensTests.cs` | USS 토큰 ↔ C# 상수 동기화 검증 |
| `PlayMode/RosConnectionTests.cs` | ROS-TCP 연결 smoke (실기기 또는 mock) |
| `PlayMode/CameraStreamTests.cs` | 카메라 토픽 subscribe smoke |
| `PlayMode/Map2DRenderTests.cs` | 2D 맵 렌더링 (스냅샷 비교) |

## 규칙

- 테스트 파일명 = `<대상클래스>Tests.cs` (예: `RobotInfoTests.cs`).
- EditMode/PlayMode 각각에 `*.asmdef` 파일 필요 (Unity가 첫 테스트 추가 시 자동 생성 또는 Editor 메뉴에서 생성).
- ROS/Supabase 외부 의존은 mock 또는 fake로 격리. 실기기 의존 테스트는 별도 마커(`[Category("Integration")]`)로 분리.
- Play Mode 테스트는 CI에서 batch mode로 돌릴 수 있게 무인터랙션화.

## 실행

```bash
# CLI batch mode (Unity 6.3 LTS)
/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -nographics -quit \
  -projectPath /Users/family/jason/URHYNIX/unity/ControlRoom \
  -runTests \
  -testPlatform EditMode \
  -logFile /tmp/unity-tests-editmode.log
```

## 의존 패키지

- `com.unity.test-framework` 1.6.0 (현재 manifest에 포함)
- NUnit (test-framework가 자동 포함)
