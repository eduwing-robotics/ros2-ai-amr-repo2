# Assets/Editor/

> Unity Editor 전용 스크립트. 빌드에 포함 안 됨.

## 예정 파일

| 파일 | 역할 |
|---|---|
| `ControlRoomSceneSetup.cs` ✅ | batch mode로 `ControlRoomMain.unity` 생성 + PanelSettings + GameObject hierarchy 자동 조립 |
| `CameraPanelSetup.cs` | batch mode로 씬에 카메라 패널 자동 추가 (Phase 5에서 unity-smoke 재이식 시) |
| `UrdfImportHelper.cs` | TurtleBot3 URDF import 자동화 (Phase 6) |
| `IconsImportSettings.cs` | PNG 아이콘 자동 Sprite import 설정 (필요 시) |

## CLI 실행 패턴

```bash
/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit \
  -projectPath /Users/family/jason/URHYNIX/unity/ControlRoom \
  -executeMethod <Namespace>.<Class>.<Method> \
  -logFile /tmp/unity_<task>.log
```

## 규칙

- 모든 Editor 스크립트는 `using UnityEditor;`로 시작. 빌드에 들어가면 안 됨.
- 씬을 편집하는 스크립트는 `EditorSceneManager.MarkSceneDirty + SaveScene` 호출.
- `MissingComponentException: RectTransform` 함정 주의 — UI GameObject는 `new GameObject(name, typeof(RectTransform))` 패턴 사용.

## 관련 스킬

- `unity-camera-panel` — Camera 패널 batch 추가 표준.
- (예정) `unity-batch-scene-edit` — Editor CLI batch 자동화 일반 패턴.
