# URHYNIX Git — 최소 룰 (1페이지)

> 학생 팀의 7-8주 MVP. 룰은 적게, 사고만 막자.

## 1. 폴더는 이렇게 나눠 쓰자

| 팀원 | 주 폴더 | Jira |
|---|---|---|
| **김주영** | `unity-src/` | SCRUM-8, 9, 15, 22, 25 |
| **임현찬** | `ros-ws/src/urhynix_bringup/`, `urhynix_unity_bridge/` | SCRUM-10, 11, 12, 20 |
| **김선일** | `ros-ws/src/urhynix_obstacle_detect/`, `urhynix_logger/`, `vision/`, `backend/` | SCRUM-13, 14, 21, 23 |
| **박태진** | `demo/`, `docs/evidence/` | SCRUM-16, 17, 18, 19, 24 |

> **자기 폴더에서만 작업하면 충돌 거의 없어요.** 다른 폴더 건드릴 일 생기면 슬랙에서 "나 이거 건드릴게" 한마디.

## 2. 브랜치는 2개만

```
main         ← 시연/발표용. PR 통해서만 머지.
 └ <자기이름>  ← 본인 작업 브랜치. push 자유.
```

예: `juyoung`, `hyunchan`, `sunil`, `taejin`

> 티켓 단위로 더 쪼개고 싶으면 `juyoung/SCRUM-9-arena-ui` 같이 슬래시로 (선택).

## 3. 매일 5단계

```bash
# ① 아침: 최신 main 받기
git checkout main
git pull

# ② 본인 브랜치로 이동
git checkout juyoung    # 본인 이름

# ③ main 변경사항 흡수 (충돌 방지)
git merge main

# ④ 작업 → 자주 커밋 → 자주 push
git add .
git commit -m "ROS topic 수신 연결"
git push

# ⑤ 끝났으면 PR 열기 (한 줄이라도 OK)
gh pr create --base main
# 슬랙에 링크 공유 → 누구든 1명 승인하면 머지
```

## 4. 절대 안 되는 것 (3개만)

1. ❌ **`main`에 직접 push** (GitHub 보호 룰로 자동 차단됨)
2. ❌ **남의 브랜치에 force push** (`git push --force` 금지. 본인 브랜치만 `--force-with-lease`)
3. ❌ **`.env`, 토큰, 비밀번호 커밋** — `bash .claude/skills/secret-scan/scan.sh` 한 번 돌려보기

## 5. 충돌나면

| 상황 | 대응 |
|---|---|
| 같은 파일 다른 사람이 먼저 머지함 | `git pull --rebase origin main` → 충돌 수동 해결 → push |
| Unity 씬(`.unity`) 충돌 | **늦게 작업한 쪽이 양보** → 슬랙에 알리고 본인 변경분 메모 → 먼저 머지된 거 pull 후 다시 작업 |
| 도저히 모르겠음 | 슬랙에 스크린샷 + 김주영(주인님)에게 호출 |

## 6. PR은 가볍게

- 제목: `SCRUM-N: 한 줄 요약` 정도
- 본문: 무엇 / 어떻게 테스트했는지 2~3줄
- 리뷰: 누구든 1명 OK 누르면 머지

## 7. 도움 도구

- **PR/이슈**: GitHub
- **할 일**: Jira (SCRUM 보드)
- **소통**: Slack `C0B5Q43A27R` — daily-recap이 매일 22시 그날 작업 자동 정리해줌
- **시크릿 점검**: `bash .claude/skills/secret-scan/scan.sh`

## 한줄정리
자기 폴더에서 본인 이름 브랜치로 작업 → 자주 push → PR로 main에 합치기, 그게 다.
