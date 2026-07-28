# Assets/Editor/

> Unity Editor 전용 스크립트. 빌드에 포함 안 됨.

## 현재 주요 파일

| 파일 | 역할 |
|---|---|
| `ControlRoomSceneSetup.cs` | `ControlRoomMain.unity`와 UI hierarchy 구성 |
| `CameraStreamSetup.cs` | 카메라 subscriber와 scene binding 구성 |
| `ControlRoomCaptureMenu.cs` | 발표·검증용 화면 캡처 |
| `GalleryRoomUrpUpgrade.cs` | Gallery asset의 URP 호환 보정 |
| `GalleryCinematicCameraShotBook.cs` | 영상 shot preset |

## CLI 실행 패턴

```bash
/Applications/Unity/Hub/Editor/6000.3.16f1/Unity.app/Contents/MacOS/Unity \
  -batchmode -quit \
  -projectPath /path/to/ros2-ai-amr-repo2/client/UNITY \
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
