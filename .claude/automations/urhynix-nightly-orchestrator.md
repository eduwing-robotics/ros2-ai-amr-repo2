---
name: urhynix-nightly-orchestrator
purpose: 매일 밤 URHYNIX 작업 마감 · 슬랙 요약 · 주간 메타 작업 통합 실행
status: planned
owner: 코워크
schedule: "0 22 * * 1-5"  # 평일 22:00 KST (주말은 weekly로 처리)
lock: docs/status/.nightly-orchestrator.lock
based_on: TaillogToss/taillog-nightly-orchestrator (구조 차용)
---

# URHYNIX Nightly Orchestrator

평일 밤 10시, 그날 작업 마감 + 슬랙 요약 + 주간 메타 작업.

## 공통 원칙 (MUST)

- lock 존재 + running이면 즉시 종료
- lock 없으면 생성, 종료 시 해제
- DRY_RUN=true면 파일 저장만, 슬랙·외부 호출 차단
- 각 TASK 실패해도 다음 진행, 결과는 RESULTS 배열에 기록

## TASK 목록 (순서 고정)

### TASK 1: daily-recap (메인 슬랙 요약)

프롬프트 파일: `.claude/automations/daily-recap.md`
실행: 해당 파일을 Read로 읽고 지침대로 수행 → 채널 `C0B5Q43A27R`로 슬랙 전송

성공 조건: 슬랙 응답 200 OK 또는 DRY_RUN 모드에서 preview 파일 생성

### TASK 2: docs/daily 격자 정리

직접 실행:
1. `docs/daily/$(date +%m-%d)/` 디렉토리 존재 확인 (없으면 생성)
2. 디렉토리가 빈 상태로 7일 경과면 자동 삭제 (정리)
3. 결과 `docs/status/NIGHTLY-RUN-LOG.md` 에 append

### TASK 3: skill-harvest 주 1회 (일요일만)

요일 == 일요일일 때만 실행.

프롬프트 파일: `.claude/automations/skill-harvest.md`
실행: 해당 파일을 Read로 읽고 지침대로 수행 → 후보 카드 출력만 (자동 생성 X)

DRY_RUN 강제 적용 (첫 회차부터): 슬랙 미발송, 파일 저장만.

### TASK 4: 빌드 캐시 정리 (선택)

매일 X, **금요일만** 실행.

```bash
# unity-src 빌드 캐시는 .gitignore라 OK, 단지 디스크 절약용
find /Users/family/jason/URHYNIX/unity-src -type d \( -name "Library" -o -name "Temp" -o -name "Obj" \) -mtime +7 -exec rm -rf {} + 2>/dev/null || true
```

### TASK 5: 종합 보고

모든 TASK 완료 후 `docs/status/NIGHTLY-RUN-LOG.md` 에 다음 형식 append:

```
## YYYY-MM-DD HH:MM
- TASK 1 daily-recap: {OK/FAIL}
- TASK 2 daily-grid: {OK/FAIL}
- TASK 3 skill-harvest: {SKIP/OK/FAIL}
- TASK 4 cache-cleanup: {SKIP/OK/FAIL}
```

## 코워크 등록 시 체크리스트

- [ ] cron `0 22 * * 1-5` (평일 22시 KST)
- [ ] 첫 회차 dry-run 강제 (TASK 1, TASK 3 모두)
- [ ] 주인님 첫 슬랙 메시지 확인 후 활성화
- [ ] NIGHTLY-RUN-LOG.md 위치 초기화

## 한줄정리
평일 밤 자동으로 슬랙 요약 + 일일 격자 정리 + (일요일) 스킬 수확 + (금요일) 캐시 정리를 한 번에 처리.
