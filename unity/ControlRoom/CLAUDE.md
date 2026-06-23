# unity/ControlRoom/

> URHYNIX 박물관/미술관 디지털트윈경비로봇 **관제 UI** Unity 프로젝트 루트.
> `robot_control_system.html`을 Unity C#로 전환하는 정본 위치.

## 무엇이 들어가는가

- `Assets/` — 모든 게임/UI 자산 (Scenes, Scripts, UI, Art, Robots, Editor, Resources)
- `Packages/manifest.json` — Unity 패키지 의존성
- `ProjectSettings/` — Unity 자동 관리 (사람이 직접 편집 금지, ProjectVersion.txt 제외)
- `README.md` — 사람용 진입 안내 (Unity Hub Add 절차, 폴더 구조, Phase 로드맵)

## 환경 (요약)

| 항목 | 값 |
|---|---|
| Unity 버전 | 6000.3.16f1 (Unity 6.3 LTS) |
| Render | Universal RP 17.0.4 |
| UI | UI Toolkit (`com.unity.modules.uielements`) |
| ROS 브리지 | ROS-TCP-Connector v0.7.0 |
| Supabase | `https://ueupkrxwybuuqxflstvg.supabase.co` |

## 에이전트 행동 규칙

1. **service_role 키 절대 Unity 클라이언트 미반입** — anon key만, `Resources/SupabaseConfig.local.asset` (`.gitignore` 차단).
2. **새 폴더 만들면 안에 CLAUDE.md 1개 박기** (3~10줄, 폴더 용도 설명).
3. **새 파일 최상단에 1~5줄 헤더 주석** (파일 역할/기능). JSON 예외.
4. **검증된 unity-smoke 코드 재활용**: Phase 5에서 `CameraStreamPanel.cs`, `CameraPanelSetup.cs`를 UI Toolkit 베이스에 맞춰 재이식 (단순 copy 금지).
5. **URDF Importer 호환성**: Unity 6 불안정. Phase 6 진입 전 smoke 1건, fallback은 community fork.

## 관련 SSOT

- `../../docs/ref/UNITY-CONTROLROOM-CONVERSION-PLAN.md` — 13절 phase + 검증 체크리스트
- `../../docs/ref/tech/UNITY.md` — 기술별 ref 진입
- `../../docs/status/DECISION-LOG.md` 2026-06-02 — 버전/Supabase 결정
- `README.md` — 사람 진입 안내
