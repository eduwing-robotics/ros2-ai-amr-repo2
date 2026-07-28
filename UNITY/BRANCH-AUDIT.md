# Unity Branch Audit

감사 기준일: 2026-07-28
기준 저장소: `eduwing-robotics/ros2-ai-amr-repo2`
감사 기준 `main`: `fee2cb983920c99c97555e6bb7774ce4d5d8ef7e`

## 결론

- 공개 Unity 프로젝트 정본은 `main`의 저장소 루트 `UNITY/` 하나로 둡니다.
- T1·Gen.G 주행 package는 후속 작업에서 `Slam_Nav2/robot_navigation/` 아래로 통합됐습니다.
- feature branch는 Git 스냅샷이므로 정본 파일이 함께 보이는 것이 정상입니다. 폴더만 삭제하면 이후 merge에서 `main`의 Unity 프로젝트까지 삭제하는 충돌을 만들 수 있습니다.
- 고유 주행·비전 커밋이 있는 브랜치는 Unity 폴더 유무만 보고 삭제하지 않습니다.
- 완전히 `main`에 포함된 과거 브랜치는 원격 branch 삭제 후보입니다. 삭제 전 아래 SHA로 복구 가능성을 보존합니다.

## 후속 원격 상태

README 시각화 푸시 직전 원격을 다시 fetch한 결과, 이전 T1·Gen.G feature branch는 삭제되고 두 package가 `Slam_Nav2`로 통합돼 있었습니다.

| 현재 브랜치 | main 대비 | 내용 | 판정 |
|---|---:|---|---|
| `main` | 기준 | 공개 Unity 정본과 공통 ROS 2 코드 | 유지 |
| `Slam_Nav2` · `cdd51e7` | 20 unique commits | `robot_navigation/{t1_rpp_patrol2_aruco_dock,geng_rpp_patrol_dock}` | 유지 · 두 주행 package 통합 |
| `backup/genji-drive-20260710` | 2 unique commits | Gen.G drive·bringup 기록 | 유지 |
| `integration/museum-bacchus` | 19 unique commits | vision/navigation integration | 유지 |

아래 전수조사 표는 feature branch 통합 전의 역사 기록입니다.

## 전수조사 결과

| 브랜치 | Unity 관련 트리 | main 대비 | 판정 |
|---|---:|---:|---|
| `main` · `fee2cb983920` | `client/ControlRoom` 1,531 files · tree `29052828a3e8` | 기준 | 최종적으로 루트 `UNITY`로 rename |
| `feature/geng-rpp-patrol-aruco-dock` · `996d8fed4ed1` | `client/ControlRoom` 1,531 files · 동일 tree | 8 unique commits | 유지 · Gen.G RPP/ArUco package 고유 |
| `feature/t1-rpp-patrol2-aruco-dock` · `e481e9bfe38a` | `client/ControlRoom` 1,531 files · 동일 tree | 6 unique commits | 유지 · T1 RPP/ArUco package 고유 |
| `backup/genji-drive-20260710` · `bca844c39dd6` | `unity/ControlRoom` 1,529 files, `unity-smoke` 84, `vendor/unityctl-plugin` 743 | 2 unique commits | 보류 · Gen.G drive 고유 커밋 보존 |
| `integration/museum-bacchus` · `d228dab0d152` | Unity project 없음 | 19 unique commits | 유지 · vision/navigation integration 고유 |
| `codex/robot-goal-pose-bridge` · `1ec6f3021291` | legacy `unity/ControlRoom` 401, smoke 84, vendor 743 | main의 ancestor, 0 unique | 2026-07-28 원격 branch 삭제 완료 |
| `sunil/nav-axis-drive` · `266231b20548` | legacy `unity/ControlRoom` 401, smoke 84, vendor 743 | main의 ancestor, PR #1 merged | 2026-07-28 원격 branch 삭제 완료 |

## 고유성 확인

- T1·Gen.G feature branch의 `client/ControlRoom` tree hash는 당시 `main`과 정확히 같았습니다. Unity 고유 수정이 아니라 branch snapshot에 포함된 정본 사본입니다.
- backup branch의 Unity tree는 당시 `main`보다 `GalleryCinematicCameraShotBook.cs`와 `.meta` 두 파일이 적고, Unity 고유 추가분은 없습니다.
- backup branch의 고유 변경은 `patch_nav_params_genji.py`, Nav2 bringup, patrol bridge와 관련된 주행 코드입니다.
- `integration/museum-bacchus`는 Unity 프로젝트를 포함하지 않습니다.
- Gen.G feature의 `geng_rpp_patrol_dock/docs/UNITY_POSE_AND_CONTROL.md`는 도킹 package 사용 문서이므로 삭제 대상이 아닙니다.

## 삭제 원칙

1. feature branch 안의 Unity 폴더만 삭제하지 않습니다.
2. 고유 커밋이 있는 branch는 main 통합 여부를 먼저 확인합니다.
3. 완전히 병합된 branch를 지울 때는 branch 이름과 마지막 SHA를 함께 기록합니다.
4. branch 삭제는 Git 객체 용량 최적화와 별개입니다. 같은 blob은 Git이 공유하므로, snapshot 안의 동일 파일을 다시 삭제해도 저장소 크기가 줄지 않습니다.

## 삭제 완료와 복구 기준

아래 두 원격 branch는 `main`에 완전히 포함된 것을 재확인한 뒤 2026-07-28 삭제했습니다.
필요하면 기록된 마지막 SHA에서 같은 이름의 branch를 다시 만들 수 있습니다.

```text
codex/robot-goal-pose-bridge  1ec6f30212915abf904ca05386617305fd6768d0
sunil/nav-axis-drive          266231b20548e6c106055fed1fb45ae1c1d0de45
```

`backup/genji-drive-20260710`과 `integration/museum-bacchus`는 고유 커밋을 보존하기 위해 삭제하지 않았습니다. T1·Gen.G feature branch의 고유 내용은 후속 `Slam_Nav2`에 통합됐습니다.
