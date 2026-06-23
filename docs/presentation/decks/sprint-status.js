/*
 * sprint-status.js — deck 3: Jira 스프린트 진행 현황 (정적 스냅샷).
 * 출처: Jira 라이브 동기화 (SCRUM-104~110 에픽 + 하위 카드, 2026-06-18). docs/ref/JIRA-MAP.md 참조.
 * 갱신: mcp__atlassian__searchJiraIssuesUsingJql (project=SCRUM AND statusCategory!=Done) 결과를
 *       아래 items/rows 에 옮겨 적고 lastSynced 날짜를 바꾼다. (라이브 API는 file://에서 불가)
 */
var SPRINT_SYNCED = "2026-06-18";
registerDeck({
  id: "sprint-status",
  title: "⑥ 진행 현황 (Jira)",
  theme: "amber",
  slides: [
    {
      type: "cover",
      title: "지금 우리는 어디까지 왔나",
      subtitle: "Jira의 작업 현황을 7개 주간으로 나눠 봅니다. 여기는 그때 기록이라 갱신된 날을 함께 봅니다.",
      tags: ["SCRUM 프로젝트", "스프린트 7", "마지막 동기화 " + SPRINT_SYNCED]
    },
    {
      type: "progress",
      title: "스프린트별 진행률",
      lead: "1·2·3주차는 끝났고, 지금 4주차(로봇 띄우기)를 진행 중입니다. 5~7주차는 대기. 마지막으로 확인한 날: " + SPRINT_SYNCED,
      items: [
        { label: "1주차 · 기획·팀 구성", done: 4, total: 4, status: "완료" },
        { label: "2주차 · 요구사항·아키텍처", done: 4, total: 4, status: "완료" },
        { label: "3주차 · 동작 검증 시나리오", done: 3, total: 3, status: "완료" },
        { label: "4주차 · SLAM·Nav2·센서 결선", done: 4, total: 9, status: "진행", sub: "지금 진행 중 (06/16~06/22) · 완료 4 / 진행 3 / 대기 2" },
        { label: "5주차 · Unity 관제 UI", done: 0, total: 7, status: "대기" },
        { label: "6주차 · AI 인식·출동 대응", done: 0, total: 5, status: "대기" },
        { label: "7주차 · 통합·최종 발표", done: 0, total: 4, status: "대기" }
      ]
    },
    {
      type: "table",
      title: "주차별 큰 묶음 (에픽) — SCRUM-104~110",
      lead: "7개 주차의 큰 작업 묶음. 지금은 4주차가 진행 중입니다. (Jira 라이브 동기화)",
      columns: ["에픽", "주차", "기간", "핵심 내용", "상태"],
      rows: [
        ["SCRUM-104", "1주차", "05/26~06/01", "기획·팀 구성", { v: "완료", kind: "ok" }],
        ["SCRUM-105", "2주차", "06/02~06/08", "요구사항·아키텍처", { v: "완료", kind: "ok" }],
        ["SCRUM-106", "3주차", "06/09~06/15", "동작 검증 시나리오", { v: "완료", kind: "ok" }],
        ["SCRUM-107", "4주차", "06/16~06/22", "SLAM·Nav2·센서 결선", { v: "진행 중", kind: "warn" }],
        ["SCRUM-108", "5주차", "06/23~06/29", "Unity 관제 UI", { v: "대기", kind: "" }],
        ["SCRUM-109", "6주차", "06/30~07/06", "AI 인식·출동 대응", { v: "대기", kind: "" }],
        ["SCRUM-110", "7주차", "07/07~07/13", "통합·최종 발표", { v: "대기", kind: "" }]
      ]
    },
    {
      type: "cards",
      title: "이번 주 할 일 — 4주차 (로봇 띄우기, SCRUM-107)",
      lead: "지금 돌아가는 일들입니다. 완료된 것과 진행 중인 것을 함께 봅니다. (클릭 시 Jira)",
      cols: 3,
      cards: [
        { title: "SCRUM-122 · SLAM·Nav2 주행", body: "지도를 만들고 길찾기 주행을 맞춥니다 (임현찬)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-122)", badge: { text: "진행 중", kind: "warn" } },
        { title: "SCRUM-124 · 로봇–Unity 연동", body: "ROS-TCP로 로봇 데이터를 Unity 화면에 보냅니다 (김주영)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-124)", badge: { text: "진행 중", kind: "warn" } },
        { title: "SCRUM-141 · 시나리오 시퀀스", body: "시나리오 흐름도를 그립니다 (김선일)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-141)", badge: { text: "진행 중", kind: "warn" } },
        { title: "SCRUM-123 · 센서 결선", body: "Arduino에 센서 4종을 연결했습니다 (박태진)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-123)", badge: { text: "완료", kind: "ok" } },
        { title: "SCRUM-143 · 하드웨어 조사", body: "센서·워터펌프 구성을 조사했습니다 (박태진)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-143)", badge: { text: "완료", kind: "ok" } },
        { title: "SCRUM-146 · DB 1차 작성", body: "데이터베이스 첫 버전을 만들었습니다 (박태진)", sub: "[Jira 열기](https://jason1127.atlassian.net/browse/SCRUM-146)", badge: { text: "완료", kind: "ok" } }
      ]
    },
    {
      type: "bullets",
      title: "다음 주 계획 — 5주차 (Unity 관제 UI, SCRUM-108)",
      lead: "06/23~06/29. 관제 화면을 본격적으로 만듭니다.",
      items: [
        { h: "SCRUM-127", d: "관제 지도에서 좌표를 만들고 지우고 경로를 편집합니다" },
        { h: "SCRUM-128", d: "주행 모드 버튼 (수동·자동·스캔·가속)" },
        { h: "SCRUM-129", d: "배터리·센서 상태 패널 + 위험 알람 팝업" },
        { h: "SCRUM-130", d: "카메라 라이브 화면 (켜고 끄기)" }
      ]
    },
    {
      type: "bullets",
      title: "이 정보는 어떻게 유지하나",
      lead: "여기는 자동 업데이트가 아니라 정기적으로 손으로 갱신합니다.",
      items: [
        { h: "정보 원본", d: "docs/ref/JIRA-MAP.md에 있는 표가 정답입니다." },
        { h: "갱신하는 방법", d: "Jira에서 `project=SCRUM AND statusCategory!=Done` 검색 결과를 이 파일에 옮겨 적고 마지막 날짜를 바꿉니다." },
        { h: "마지막 갱신", d: SPRINT_SYNCED + " — 발표 전에 다시 한 번 갱신하길 권합니다." }
      ]
    }
  ]
});
