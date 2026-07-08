---
name: urhynix-dogfood-audit
description: URHYNIX ControlRoom(Unity 관제 UI + 로봇 스택)을 페르소나 서브에이전트(관제 운영자·시연 진행자·강건성/보안·성능/리소스)가 유저 여정으로 "써보며" 결함·UX마찰·시연리스크를 발굴하는 3단(정찰→워커→메인 검증·종합) 도그푸딩 감사. "감사해줘", "개선할점 찾아줘", "도그푸딩", "여러 유저로 써봐", "시연 리허설 점검", "dog-audit" 요청에 발동. ChatterBox dogfood-audit의 URHYNIX 이식판.
user_invocable: true
tags: [audit, dogfooding, persona, multi-agent, ux, unity, review]
version: 1
---

<!-- ChatterBox .claude/skills/dogfood-audit 이식 (2026-07-08). 웹플랫폼 페르소나(보안공격자류) → 관제/시연/Unity 런타임 페르소나로 각색. -->

# URHYNIX Dogfood Audit

페르소나 서브에이전트가 ControlRoom 코드 경로(=유저 여정)를 걸어보며 **결함·UX마찰·시연리스크·잘되는점**을 한 번에 발굴한다. 라이브 플랫폼 대신 **Unity 런타임 + 로봇 스택**이 대상 — "써본다" = 여정을 코드로 리허설한다(Play 불필요, 로봇 OFF여도 가능).

## Use When

- "또 개선할 점", "감사", "도그푸딩", "시연 전 점검" 류 요청
- 새 기능(예: 박물관 decor, 셔터) 직후 회귀·완성도 훑기
- 시연/발표 전 리허설 리스크 사전 발굴

## 모델 분담 (전역 규칙 준수)

| 단계 | 모델 | 이유 |
|---|---|---|
| 지형 확정 | 메인 직접(bash 인벤토리) | 싸고 즉답 |
| 정찰 | `Explore` 1기 (medium) | 여정 표면지도 — 워커 급식자료 |
| 페르소나 워커 | `general-purpose` + `model: opus` 병렬 4기 | 심층 여정. 병렬화 목적 |
| **검증·종합** | **메인 직접(성역, 스킵 금지)** | 워커 과대평가 재조정 + 거짓양성 반증 |

## Steps

1. **지형 확정(직접)** — `find`/`wc -l`로 Scripts 하위(App/UI/Map/Ros/…) 파일·LOC 인벤토리. ⚠️ rtk 프록시가 `ls`를 "(empty)"로 뱉을 수 있음 → `/bin/ls` 또는 `find`.
2. **정찰(Explore 1기)** — "관제 운영자 여정 표면지도": 탭/뷰 전환, 로봇선택→우클릭 출동→순찰 발행, 연결상태 UX, 상태 영속(PlayerPrefs/persistentDataPath). 추측 금지·file:line 강제.
3. **페르소나 워커(Opus 4기 병렬)** — 정찰 지도를 프롬프트에 급식. 모든 발견에 `file:line + 심각도 + Confidence(Confirmed/Likely/Refuted)` 강제, **안전하면 Refuted 명시**(거짓양성 억제), 현 규모(로봇 2대·2m 아레나·시연용) 기준 오버엔지니어링 금지.
4. **검증(메인 직접·성역)** — 최고심각도 Confirmed는 인용 파일을 직접 열어 대조. 심각도를 실임팩트로 재조정.
5. **종합 리포트(BLUF)** — 확정 발견 표(심각도순) + 반증 기록 + 잘되는점(회귀 금지) + 권장 수정 순서(effort S/M/L).
6. **수정까지 요청받으면** — S급 묶음/큰 항목 분리해 `phase-loop`로 이관(자기리뷰는 메인 직접).

## URHYNIX 표준 페르소나 세트

| 트랙 | 페르소나 | 반드시 봄 | 피함 |
|---|---|---|---|
| UX | 관제 운영자 | 상황인지(로그/상태 배지), 모드전환 마찰, 멀티로봇 사각, 오프라인 시 액션 동작, 발견성/영속 | 문서 이상론 |
| UX | 시연 진행자 | 데모 버튼→실제 이벤트 결선, 초기 카메라에서 연출 대상 가시성(픽셀 계산), 리허설 왕복비용, 로봇 OFF 시연 경로 | 현 규모 오버엔지니어링 |
| 강건성 | 이벤트/수명주기 | static 이벤트 구독 누수, 코루틴 수명, json 파싱 실패 반경, 재빌드/리소스 정리, 스레드(⚠아래 확정사실) | 근거 없는 트집 |
| 성능 | 리소스 | 폴리곤/라이트/머티리얼 인스턴스 수(수치 계산), 누적 누수, 임포트 세팅 | "이론상" 과장 — 무시 가능이면 Refuted |

## 검증 시 확정 사실 (워커 주장 재조정용 — 2026-07-08 원본 대조 완료)

- **ROS-TCP 콜백은 메인스레드**: `Packages/com.unity.robotics.ros-tcp-connector/Runtime/TcpConnector/ROSConnection.cs` `Update()`가 ConcurrentQueue를 비우며 콜백 호출. "백그라운드 스레드 Transform 크래시" 주장은 반증하라.
- **렌더러는 Forward(m_RenderingMode 0)** — `Assets/Settings/ControlRoom_Renderer.asset`. per-object 추가라이트 한계는 URP asset(`ControlRoom_URP.asset`)의 `m_AdditionalLightsPerObjectLimit`.
- **런타임 생성 머티리얼/텍스처는 `rt_` 이름 규약** — Map25DView.OnDestroy가 스윕. 새 생성물엔 규약 준수 여부를 체크항목에 포함.
- **Play 반복 자체는 누수 아님**(에디터가 Play 종료 시 런타임 오브젝트 해제) — 세션 내 재빌드 경로만 누적 이슈.

## Unity 검증 함정 (이 프로젝트 실측)

- 컴파일 검증은 [[unity-unityctl-ops]] 절차 + **stale check 함정**: 사용자가 Play 중이면 재컴파일 안 됨 → `play stop` 후 `unityctl exec 'UnityEditor.AssetDatabase.Refresh()'`가 키스트로크(Cmd+R)보다 확정적. IPC 락 뜨면 수십초 대기.
- 육안 없이 시각 검증: 에디터 exec로 카메라 렌더 몽타주 PNG(`GalleryRoomUrpUpgrade.RenderStatueViews` 패턴) — UI Toolkit 스크린샷 검정 함정 우회.
- 맵 좌표 ground truth: 2.5D 우클릭 → `[MapClick] map=(x,y)` Editor.log(에디터 전용).

## Output Format

```markdown
## BLUF — 판정 한 줄
## 확정 발견 (검증 완료, 심각도순) | # | 결함 | 심각도 | 근거 | 수정 크기 |
## 반증(거짓양성 억제 기록)
## 잘 되는 점 (회귀 금지)
## 권장 수정 순서
```

## Verify

- [ ] 워커 발견 전부에 file:line + Confidence 존재
- [ ] 최고심각도는 메인이 원본 직접 대조(성역) — 심각도 재조정 기록
- [ ] Refuted 항목 명시
- [ ] 수정 진행 시 phase-loop + 컴파일 사이클 배치(에디터 왕복 최소화)

## 참조

- 원본: `/Users/family/jason/ChatterBox/.claude/skills/dogfood-audit/SKILL.md` (웹플랫폼용 자매)
- `.claude/skills/unity-unityctl-ops/SKILL.md` — 컴파일/exec 안전 절차
- 2026-07-08 1차 실행: 시연 Blocker(데모 화재 버튼 미결선)·운영 Blocker(2.5D 슬롯 stale) 발굴 → phase-loop 7건 수정
