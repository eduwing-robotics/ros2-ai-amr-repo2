# Assets/Scripts/Features/

> 로봇 기능 토글 (자율주행/SLAM/스캔/카메라/가속) 인터페이스 + Registry.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `IRobotFeature.cs` | 기능 추가용 공통 인터페이스 |
| `FeatureRegistry.cs` ✅ | 기능 등록소 (`FeatureConfig/default_features.json` 로드 + ID/로봇별 조회) |
| `AutoDriveFeature.cs` | 자율주행 |
| `SlamFeature.cs` | SLAM |
| `ScanFeature.cs` | 360도 스캔 |
| `CameraFeature.cs` | 카메라 ON/OFF |
| `TurboFeature.cs` | 가속 모드 |

## 새 기능 추가 절차

1. `Resources/default_features.json`에 기능 ID/표시 이름/아이콘/기본 상태/연결 명령 추가.
2. 필요하면 `IRobotFeature` 구현체 만들기.
3. `FeatureRegistry`에 등록.
4. UI는 `Scripts/UI/FeatureToggleListView`가 자동 생성.
5. ROS 명령이 필요하면 `Robot/RobotCommandService` 또는 전용 `Ros/*Publisher` 연결.
