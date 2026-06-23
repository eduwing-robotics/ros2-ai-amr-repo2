"""URHYNIX dev-plan 단일 HTML 번들 생성기.

7개 페이지(메인/역할/모듈/Sprint/시나리오/위험/제외)와 PNG 2장을 하나의 자급 HTML로 합친다.
페이지 전환은 해시 라우팅(#home, #roles, ...). 인터넷 없이 더블클릭만으로 동작.

실행:
    python3 docs/whiteboards/build_bundle.py
결과:
    docs/dev-plan-bundle.html  (단일 파일)
"""
from __future__ import annotations

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
WB = DOCS / "whiteboards"


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def b64_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return b64(path)


MATRIX_B64 = b64_optional(WB / "role_matrix.png")
GRAPH_B64 = b64_optional(WB / "role_graph.png")
MOCKUP_B64 = b64_optional(WB / "unity_ui_mockup.png")

MOCKUP_IMG_HTML = (
    '<img src="data:image/png;base64,%%MOCKUP_B64%%" '
    'alt="Unity 관제 UI 예시 (A.R.O.C. SYSTEM HQ COMMAND)" '
    'style="width: 100%; max-width: 960px; border-radius: 8px; '
    'border: 1px solid var(--border); display: block; margin: 12px 0;" />'
    if MOCKUP_B64
    else '<div class="hint">참고: <code>docs/whiteboards/unity_ui_mockup.png</code>가 없어 UI 목업 이미지는 번들에 포함되지 않았습니다.</div>'
)


HTML = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>URHYNIX · 팀 개발 플랜 (단일 번들)</title>
<style>
  :root {
    --c-juyoung:   #1f6feb;
    --c-sunil:     #9333ea;
    --c-taejin:    #f59e0b;
    --c-hyeonchan: #10b981;
    --m1: #4c7cf3;
    --m2: #f39c4c;
    --m3: #7c4cf3;
    --m4: #4cc2f3;
    --m5: #21c07a;
    --s1: #4c7cf3;
    --s2: #f39c4c;
    --s3: #7c4cf3;
    --s4: #ef4444;
    --night: #4c7cf3;
    --pir:   #ef4444;
    --noise: #f59e0b;
    --fire:  #b91c1c;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Apple SD Gothic Neo",
                 "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    font-size: 18px;
    background: var(--bg);
    color: var(--fg);
    transition: background 0.2s ease, color 0.2s ease;
  }

  /* 페이지별 테마 (data-page에 따라 cascade) */
  body[data-page="home"] {
    --bg: #0f172a; --fg: #f8fafc; --muted: #94a3b8;
    --accent: #f59e0b; --accent-dark: #b45309;
    --card: #1e293b; --border: #334155; --hover: #334155;
  }
  body[data-page="roles"] {
    --bg: #eff6ff; --fg: #1e293b; --muted: #64748b;
    --accent: #2563eb; --accent-dark: #1e3a8a;
    --card: #ffffff; --border: #bfdbfe; --hover: #dbeafe;
  }
  body[data-page="modules"] {
    --bg: #faf5ff; --fg: #1e1b4b; --muted: #6b7280;
    --accent: #9333ea; --accent-dark: #581c87;
    --card: #ffffff; --border: #e9d5ff; --hover: #f3e8ff;
  }
  body[data-page="sprints"] {
    --bg: #ecfdf5; --fg: #064e3b; --muted: #6b7280;
    --accent: #059669; --accent-dark: #064e3b;
    --card: #ffffff; --border: #a7f3d0; --hover: #d1fae5;
  }
  body[data-page="scenarios"] {
    --bg: #eef2ff; --fg: #1e1b4b; --muted: #64748b;
    --accent: #4f46e5; --accent-dark: #312e81;
    --card: #ffffff; --border: #c7d2fe; --hover: #e0e7ff;
  }
  body[data-page="risks"] {
    --bg: #fff7ed; --fg: #1c1917; --muted: #78716c;
    --accent: #d97706; --accent-dark: #92400e;
    --card: #ffffff; --border: #fed7aa; --hover: #fde68a;
  }
  body[data-page="exclusions"] {
    --bg: #fef2f2; --fg: #1c1917; --muted: #78716c;
    --accent: #dc2626; --accent-dark: #991b1b;
    --card: #ffffff; --border: #fecaca; --hover: #fee2e2;
  }

  .page { display: none; }
  .page.active { display: block; }

  .wrap { max-width: 960px; margin: 0 auto; padding: 56px 32px 80px; }
  .wrap.home { max-width: 1040px; padding-top: 64px; }

  .topbar {
    display: flex; justify-content: space-between; align-items: center;
    font-size: 14px; color: var(--muted); margin-bottom: 40px;
  }
  .topbar a { color: var(--accent); text-decoration: none; }
  .topbar a:hover { text-decoration: underline; }

  h1 {
    font-size: 56px; line-height: 1.15; margin: 0 0 16px;
    letter-spacing: -0.02em;
  }
  .sub-h1 {
    font-size: 64px; line-height: 1.1; margin: 0 0 16px;
    letter-spacing: -0.025em; color: var(--accent-dark);
  }
  .subtitle { color: var(--muted); font-size: 20px; margin: 0 0 48px; }
  .lead { font-size: 22px; color: var(--muted); margin: 0 0 48px; line-height: 1.55; }

  .badge {
    display: inline-block; background: var(--accent); color: #fff;
    padding: 6px 14px; border-radius: 999px; font-size: 13px;
    letter-spacing: 0.08em; text-transform: uppercase;
    font-weight: 600; margin-bottom: 16px;
  }

  /* HOME */
  .mvp {
    background: var(--card); border-left: 6px solid var(--accent);
    border-radius: 8px; padding: 28px 32px; font-size: 22px;
    line-height: 1.55; margin: 0 0 56px;
  }
  .mvp .label {
    display: block; font-size: 13px; color: var(--accent);
    letter-spacing: 0.12em; text-transform: uppercase;
    margin-bottom: 10px; font-weight: 600;
  }
  .pages-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 20px; margin: 0 0 56px;
  }
  @media (max-width: 1000px) { .pages-grid { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 640px)  { .pages-grid { grid-template-columns: 1fr; } }
  .page-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 28px 24px;
    color: inherit; text-decoration: none; display: block;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .page-card:hover { transform: translateY(-3px); border-color: currentColor; }
  .page-card .icon { font-size: 32px; margin-bottom: 10px; }
  .page-card .title { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
  .page-card .desc { font-size: 15px; line-height: 1.5; opacity: 0.78; }
  .page-card[data-kind="roles"]     { color: #60a5fa; }
  .page-card[data-kind="modules"]   { color: #c084fc; }
  .page-card[data-kind="sprints"]   { color: #34d399; }
  .page-card[data-kind="scenarios"] { color: #818cf8; }
  .page-card[data-kind="risk"]      { color: #fbbf24; }
  .page-card[data-kind="exclude"]   { color: #f87171; }
  .home-meta {
    color: var(--muted); font-size: 14px;
    border-top: 1px solid var(--border); padding-top: 24px;
  }
  .home-meta a { color: #93c5fd; text-decoration: none; }
  .home-meta a:hover { text-decoration: underline; }
  .home-meta .row { margin-bottom: 6px; }

  /* 공통 카드 */
  .item, .person, .module, .sprint, .scenario, .risk {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; padding: 28px 32px; margin-bottom: 22px;
  }

  /* 역할 */
  .person { border-left: 8px solid #9ca3af; }
  .person[data-person="김주영"]   { border-left-color: var(--c-juyoung); }
  .person[data-person="김선일"]   { border-left-color: var(--c-sunil); }
  .person[data-person="박태진"]   { border-left-color: var(--c-taejin); }
  .person[data-person="임현찬"]   { border-left-color: var(--c-hyeonchan); }
  .person-head, .sprint-head, .scenario-head {
    display: flex; align-items: baseline; gap: 16px;
    margin-bottom: 8px; flex-wrap: wrap;
  }
  .person h2 { font-size: 38px; line-height: 1.15; margin: 0; letter-spacing: -0.015em; }
  .person .count {
    font-size: 15px; color: #fff; padding: 4px 12px;
    border-radius: 999px; background: var(--muted); font-weight: 600;
  }
  .person[data-person="김주영"]   .count { background: var(--c-juyoung); }
  .person[data-person="김선일"]   .count { background: var(--c-sunil); }
  .person[data-person="박태진"]   .count { background: var(--c-taejin); }
  .person[data-person="임현찬"]   .count { background: var(--c-hyeonchan); }
  .summary { font-size: 20px; line-height: 1.55; margin: 0; color: var(--fg); }

  /* 모듈 */
  .module { border-top: 8px solid var(--m1); }
  .module[data-module="M1"] { border-top-color: var(--m1); }
  .module[data-module="M2"] { border-top-color: var(--m2); }
  .module[data-module="M3"] { border-top-color: var(--m3); }
  .module[data-module="M4"] { border-top-color: var(--m4); }
  .module[data-module="M5"] { border-top-color: var(--m5); }
  .mod-id {
    font-size: 14px; color: #fff; padding: 4px 12px;
    border-radius: 5px; background: var(--m1); display: inline-block;
    margin-bottom: 10px; font-weight: 700; letter-spacing: 0.05em;
  }
  .module[data-module="M1"] .mod-id { background: var(--m1); }
  .module[data-module="M2"] .mod-id { background: var(--m2); }
  .module[data-module="M3"] .mod-id { background: var(--m3); }
  .module[data-module="M4"] .mod-id { background: var(--m4); }
  .module[data-module="M5"] .mod-id { background: var(--m5); }
  .module h2 { font-size: 30px; line-height: 1.25; margin: 0 0 12px; letter-spacing: -0.015em; }
  .module .summary { font-size: 19px; margin: 0 0 16px; }
  .owners { display: flex; gap: 6px; flex-wrap: wrap; }
  .owner-chip {
    display: inline-block; font-size: 14px; padding: 4px 12px;
    border-radius: 999px; color: #fff; background: #9ca3af; font-weight: 500;
  }
  .owner-chip[data-owner="김주영"]   { background: var(--c-juyoung); }
  .owner-chip[data-owner="김선일"]   { background: var(--c-sunil); }
  .owner-chip[data-owner="박태진"]   { background: var(--c-taejin); }
  .owner-chip[data-owner="임현찬"]   { background: var(--c-hyeonchan); }

  /* Sprint */
  .timeline {
    display: flex; gap: 6px; margin: 0 0 40px;
    border-radius: 8px; overflow: hidden;
  }
  .timeline .tb {
    color: #fff; padding: 14px 16px; font-size: 14px;
    font-weight: 600; text-align: center;
  }
  .timeline .tb.s1 { background: var(--s1); flex-grow: 2; }
  .timeline .tb.s2 { background: var(--s2); flex-grow: 2; }
  .timeline .tb.s3 { background: var(--s3); flex-grow: 2; }
  .timeline .tb.s4 { background: var(--s4); flex-grow: 1; }
  .sprint { border-left: 8px solid var(--s1); }
  .sprint[data-sprint="S1"] { border-left-color: var(--s1); }
  .sprint[data-sprint="S2"] { border-left-color: var(--s2); }
  .sprint[data-sprint="S3"] { border-left-color: var(--s3); }
  .sprint[data-sprint="S4"] { border-left-color: var(--s4); }
  .sprint-id {
    font-size: 14px; color: #fff; padding: 4px 12px;
    border-radius: 5px; background: var(--s1);
    font-weight: 700; letter-spacing: 0.05em;
  }
  .sprint[data-sprint="S1"] .sprint-id { background: var(--s1); }
  .sprint[data-sprint="S2"] .sprint-id { background: var(--s2); }
  .sprint[data-sprint="S3"] .sprint-id { background: var(--s3); }
  .sprint[data-sprint="S4"] .sprint-id { background: var(--s4); }
  .sprint h2 { font-size: 32px; line-height: 1.2; margin: 0; letter-spacing: -0.015em; }
  .sprint .duration { font-size: 15px; color: var(--muted); font-weight: 600; }
  .sprint .goal { font-size: 20px; line-height: 1.55; margin: 8px 0 0; }
  .ticket {
    display: block; text-decoration: none; color: inherit;
    background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
  }
  .ticket:hover { border-color: var(--accent); }
  .ticket-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
  .ticket-id {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12px; color: var(--accent); font-weight: 600;
  }
  .ticket .title { font-size: 16px; line-height: 1.45; margin: 0 0 8px; }
  .ticket .owners .owner-chip { font-size: 12px; padding: 2px 9px; }

  /* 시나리오 */
  .scenario { border-top: 8px solid var(--night); }
  .scenario[data-kind="night"] { border-top-color: var(--night); }
  .scenario[data-kind="pir"]   { border-top-color: var(--pir); }
  .scenario[data-kind="noise"] { border-top-color: var(--noise); }
  .scenario[data-kind="fire"]  { border-top-color: var(--fire); }
  .scn-icon { font-size: 32px; }
  .scenario h2 { font-size: 36px; line-height: 1.2; margin: 0; letter-spacing: -0.015em; }
  .sensor-chip {
    font-size: 13px; color: #fff; padding: 4px 12px;
    border-radius: 5px; background: var(--night); font-weight: 600;
  }
  .scenario[data-kind="night"] .sensor-chip { background: var(--night); }
  .scenario[data-kind="pir"]   .sensor-chip { background: var(--pir); }
  .scenario[data-kind="noise"] .sensor-chip { background: var(--noise); }
  .scenario[data-kind="fire"]  .sensor-chip { background: var(--fire); }
  .flow {
    background: var(--bg); border-radius: 8px;
    padding: 12px 16px; margin: 8px 0;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 14px; line-height: 1.8; color: var(--accent-dark);
  }

  /* 위험 & 제외 */
  .risk-num, .item-num {
    font-size: 22px; color: var(--accent);
    font-weight: 700; letter-spacing: 0.05em;
  }
  .risk h2, .item h2 {
    font-size: 32px; line-height: 1.25; margin: 0;
    letter-spacing: -0.015em; color: var(--fg);
  }
  body[data-page="exclusions"] .item h2 {
    text-decoration: line-through;
    text-decoration-thickness: 2px;
    text-decoration-color: rgba(220, 38, 38, 0.4);
  }
  .risk-head, .item-head {
    display: flex; align-items: baseline; gap: 20px; margin-bottom: 12px;
  }

  /* details/summary 공통 */
  details {
    margin-top: 20px;
    border-top: 1px dashed var(--border);
    padding-top: 16px;
  }
  details summary {
    cursor: pointer; font-size: 15px; color: var(--accent);
    font-weight: 600; list-style: none; user-select: none; padding: 6px 0;
  }
  details summary:hover { color: var(--accent-dark); }
  details summary::-webkit-details-marker { display: none; }
  details summary::before { content: "▸ "; margin-right: 4px; }
  details[open] summary::before { content: "▾ "; }
  details .body { margin-top: 12px; font-size: 17px; line-height: 1.6; }
  details .body h3 {
    font-size: 15px; margin: 14px 0 6px;
    color: var(--accent); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
  }
  details .body p { margin: 0 0 10px; }
  details .body ul { margin: 4px 0 12px 20px; padding: 0; }
  details .body code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    background: var(--hover); padding: 2px 6px;
    border-radius: 3px; font-size: 15px;
  }

  /* 역할 페이지 PNG 토글 */
  .visual-toggle { margin-top: 48px; }
  .visual-toggle summary {
    padding: 12px 0;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    font-size: 16px;
  }
  .visual-toggle .imgs { margin-top: 20px; display: grid; grid-template-columns: 1fr; gap: 16px; }
  .visual-toggle figure {
    margin: 0; background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 14px;
  }
  .visual-toggle img { width: 100%; height: auto; display: block; border-radius: 4px; }
  .visual-toggle figcaption { margin-top: 10px; color: var(--muted); font-size: 13px; }

  /* 네비게이션 푸터 */
  .nav-footer {
    margin-top: 56px; padding-top: 24px;
    border-top: 1px solid var(--border);
    display: flex; justify-content: space-between; font-size: 16px;
  }
  .nav-footer a {
    color: var(--accent); text-decoration: none;
    padding: 12px 20px; border: 1px solid var(--border);
    border-radius: 8px; background: var(--card);
  }
  .nav-footer a:hover { background: var(--hover); }

  /* 인쇄 친화 */
  @media print {
    .page { display: block !important; page-break-after: always; }
    .nav-footer, .topbar { display: none; }
    body { background: #fff; color: #000; }
    details > summary { display: none; }
    details > *:not(summary) { display: block !important; }
  }
</style>
</head>
<body data-page="home">

<!-- ============== HOME ============== -->
<section class="page active" data-page="home">
<div class="wrap home">
  <h1>URHYNIX</h1>
  <p class="subtitle">디지털트윈경비로봇 · 7주 · 4명</p>
  <div class="mvp">
    <span class="label">MVP 한 줄</span>
    tb3_1이 박물관/미술관 구역을 순찰하며 액자형 중요물품과 센서 이벤트를 감지하면 Unity 관제 화면에 위치·이벤트가 표시되고, tb3_2가 출동해 카메라로 확인하며, 이동 좌표·사진·영상·사운드와 대응 결과를 DB에 기록한다.
  </div>

  <div style="background: linear-gradient(135deg, #064e3b 0%, #047857 100%); border-radius: 8px; padding: 24px 28px; margin: 0 0 40px; border-left: 6px solid #10b981;">
    <div style="font-size: 12px; color: #6ee7b7; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 10px; font-weight: 600;">🚀 DAY-1 (2026-05-27)</div>
    <div style="font-size: 17px; line-height: 1.6; color: #ecfdf5;">
      <strong style="color: #fff;">김주영 + 임현찬</strong> → Pi Camera + DB 테스트<br>
      <strong style="color: #fff;">박태진</strong> → Arduino + PIR → DB 한 줄 통과<br>
      <strong style="color: #fff;">김선일</strong> → Unity 관제 UI 기능 명세 문서화
    </div>
  </div>
  <div class="pages-grid">
    <a class="page-card" data-kind="roles" href="#roles">
      <div class="icon">👥</div><div class="title">역할 매트릭스</div>
      <div class="desc">4명이 5개 모듈을 어떻게 나눠 맡는지</div>
    </a>
    <a class="page-card" data-kind="modules" href="#modules">
      <div class="icon">🧩</div><div class="title">모듈 카드 · 하드웨어 적층</div>
      <div class="desc">5개 모듈 + Arduino → RPi USB 적층 도면</div>
    </a>
    <a class="page-card" data-kind="sprints" href="#sprints">
      <div class="icon">🗓️</div><div class="title">Sprint 보드 · ⚡ 병렬 매트릭스</div>
      <div class="desc">7주 4 스프린트 · 주차×모듈 동시 진행</div>
    </a>
    <a class="page-card" data-kind="scenarios" href="#scenarios">
      <div class="icon">🎬</div><div class="title">액자 보호 시나리오 4종</div>
      <div class="desc">박물관/미술관 컨셉으로 보여줄 핵심 시연</div>
    </a>
    <a class="page-card" data-kind="risk" href="#risks">
      <div class="icon">⚠️</div><div class="title">위험</div>
      <div class="desc">깨질 수 있는 5가지와 대응</div>
    </a>
    <a class="page-card" data-kind="exclude" href="#exclusions">
      <div class="icon">🚫</div><div class="title">제외 범위</div>
      <div class="desc">이번엔 만들지 않을 6가지</div>
    </a>
  </div>
  <div class="home-meta">
    <div class="row">단일 HTML 번들 — 인터넷 없이 더블클릭으로 열림 · PNG 인라인 포함</div>
    <div class="row">Confluence · <a href="https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1540099">브레인스토밍</a> · <a href="https://jason1127.atlassian.net/wiki/spaces/SCRUM/pages/1605636">역할 분배 보드</a></div>
    <div class="row">Jira · <a href="https://jason1127.atlassian.net/jira/software/projects/SCRUM/boards/1">SCRUM 보드</a></div>
    <div class="row" style="margin-top:14px;">업데이트 2026-05-27</div>
  </div>
</div>
</section>

<!-- ============== ROLES ============== -->
<section class="page" data-page="roles">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">👥 역할 매트릭스</span>
  <h2 class="sub-h1">4명이<br>5개 모듈을<br>나눠 맡는다</h2>
  <p class="lead">한 사람이 다 하는 프로젝트가 아니다. 각자의 라인을 잡고, 겹치는 곳에서 협업한다. 펼치면 어떤 모듈을 맡는지 보인다.</p>

  <div class="person" data-person="김주영">
    <div class="person-head"><h2>김주영</h2><span class="count">모듈 3개</span></div>
    <p class="summary">AI · 백엔드 · 임베디드 데이터 라인. 센서 데이터를 받아 분류하고, DB에 쌓고, 발표 지표를 뽑는 사람.</p>
    <details><summary>맡은 모듈 보기</summary><div class="body">
      <ul>
        <li><strong>M1</strong> 백엔드 DB / ROS-TCP 라벨링 / AI <em>(공동: 김선일)</em></li>
        <li><strong>M2</strong> 아두이노 메인 보드·통신 <em>(공동: 박태진, 임현찬)</em></li>
        <li><strong>M4</strong> 아두이노 센서 <em>(공동: 임현찬, 박태진)</em></li>
      </ul>
      <p><strong>주요 협업</strong>: 김선일과는 백엔드/AI 공동, 임현찬·박태진과는 센서 공동, 박태진·임현찬과는 아두이노 메인 공동.</p>
    </div></details>
  </div>

  <div class="person" data-person="김선일">
    <div class="person-head"><h2>김선일</h2><span class="count">모듈 3개</span></div>
    <p class="summary">통신 · 관제 · 로봇 통합 라인. ROS-TCP로 데이터를 끌어와 Unity 관제 화면에 박고, 터틀봇 주행도 같이 챙긴다.</p>
    <details><summary>맡은 모듈 보기</summary><div class="body">
      <ul>
        <li><strong>M1</strong> 백엔드 DB / ROS-TCP 라벨링 / AI <em>(공동: 김주영)</em></li>
        <li><strong>M3</strong> Unity 관제UI · ROS-TCP 통신 · 영상 라이브 <em>(공동: 박태진)</em></li>
        <li><strong>M5</strong> 터틀봇 LiDAR · 카메라 · SLAM · Nav <em>(공동: 임현찬)</em></li>
      </ul>
      <p><strong>주요 협업</strong>: 가장 많은 라인을 잇는다. 김주영과 백엔드, 박태진과 Unity, 임현찬과 터틀봇 — 사실상 통합자 역할.</p>
    </div></details>
  </div>

  <div class="person" data-person="박태진">
    <div class="person-head"><h2>박태진</h2><span class="count">모듈 3개</span></div>
    <p class="summary">하드웨어 ↔ 클라이언트 ↔ 센서 라인. 보드와 카메라를 손으로 만지고, Unity에서 그 결과가 보이도록 화면 쪽을 같이 잡는다.</p>
    <details><summary>맡은 모듈 보기</summary><div class="body">
      <ul>
        <li><strong>M2</strong> 아두이노 메인 보드·통신 <em>(공동: 임현찬, 김주영)</em></li>
        <li><strong>M3</strong> Unity 관제UI · ROS-TCP 통신 · 영상 라이브 <em>(공동: 김선일)</em></li>
        <li><strong>M4</strong> 아두이노 센서 <em>(공동: 김주영, 임현찬)</em></li>
      </ul>
      <p><strong>주요 협업</strong>: 김선일과 Unity 클라이언트, 임현찬·김주영과 아두이노 메인과 센서. 발표 환경 세팅의 핵심.</p>
    </div></details>
  </div>

  <div class="person" data-person="임현찬">
    <div class="person-head"><h2>임현찬</h2><span class="count">모듈 3개</span></div>
    <p class="summary">임베디드 · 로봇 라인. 보드부터 터틀봇 SLAM/Nav2까지 — "움직이는 것"을 책임진다.</p>
    <details><summary>맡은 모듈 보기</summary><div class="body">
      <ul>
        <li><strong>M2</strong> 아두이노 메인 보드·통신 <em>(공동: 박태진, 김주영)</em></li>
        <li><strong>M4</strong> 아두이노 센서 <em>(공동: 김주영, 박태진)</em></li>
        <li><strong>M5</strong> 터틀봇 LiDAR · 카메라 · SLAM · Nav <em>(공동: 김선일)</em></li>
      </ul>
      <p><strong>주요 협업</strong>: 김주영·박태진과 센서, 박태진·김주영과 아두이노 메인, 김선일과 터틀봇. 하드웨어 디버깅의 중심.</p>
    </div></details>
  </div>

  <details class="visual-toggle">
    <summary>매트릭스 그림으로 보기 (PNG 2장)</summary>
    <div class="imgs">
      <figure>
        <img src="data:image/png;base64,%%MATRIX_B64%%" alt="역할 매트릭스" />
        <figcaption>모듈 × 사람 매트릭스. ● = 담당.</figcaption>
      </figure>
      <figure>
        <img src="data:image/png;base64,%%GRAPH_B64%%" alt="역할 그래프" />
        <figcaption>사람 ↔ 모듈 연결 그래프. 선 색은 담당자 색.</figcaption>
      </figure>
    </div>
  </details>

  <div class="nav-footer">
    <a href="#home">← 메인</a>
    <a href="#modules">모듈 카드 →</a>
  </div>
</div>
</section>

<!-- ============== MODULES ============== -->
<section class="page" data-page="modules">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">🧩 모듈 카드</span>
  <h2 class="sub-h1">5개 모듈<br>한 줄로</h2>
  <p class="lead">프로젝트는 다섯 덩어리로 나뉜다. 각 모듈은 담당자와 핵심 산출물이 정해져 있다. 펼치면 자세한 결과물이 보인다.</p>

  <div class="module" data-module="M1">
    <span class="mod-id">M1</span>
    <h2>백엔드 DB · ROS-TCP 라벨링 · AI</h2>
    <p class="summary">이벤트와 카메라 캡처를 받아 DB에 쌓고, 오탐/실탐을 분류하고, 발표 KPI를 뽑는다.</p>
    <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
    <details><summary>핵심 산출물 보기</summary><div class="body"><ul>
      <li>DB Writer 노드 (<code>/security/*</code> 구독 → <code>events</code>/<code>dispatches</code>/<code>camera_captures</code> insert)</li>
      <li>SCRUM-23 예정: 이동 좌표 로그(<code>pose_logs</code>)와 사진·영상·사운드 메타데이터(<code>media_artifacts</code>) 저장</li>
      <li>SCRUM-21/23 예정: 액자형 중요물품 레지스트리(<code>protected_assets</code>)와 카메라 인식 결과 라벨링</li>
      <li>이벤트·이미지 라벨링 파이프라인 (수동 + 도구)</li>
      <li>AI 오탐/실탐 분류 보조 모델 (간단 분류기 + 임계값 fallback)</li>
      <li>발표용 KPI 집계 쿼리 (감지률·평균 출동·확인 성공률·오탐률)</li>
    </ul></div></details>
  </div>

  <div class="module" data-module="M2">
    <span class="mod-id">M2</span>
    <h2>아두이노 메인 보드 · 통신</h2>
    <p class="summary">MCU에서 센서값을 모아 시리얼로 내보내고, ROS 측에서 <code>/security/event</code>로 변환한다.</p>
    <div class="owners"><span class="owner-chip" data-owner="박태진">박태진</span><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="김주영">김주영</span></div>
    <details><summary>핵심 산출물 보기</summary><div class="body"><ul>
      <li>MCU 펌웨어 (센서 → 시리얼/UART)</li>
      <li>ROS 측 시리얼 브릿지 노드 (<code>urhynix_sensor_bridge</code>)</li>
      <li>보드별 고유 <code>robot_id</code> 매핑 파라미터</li>
      <li>시리얼 포맷 약속 (<code>EVT,pir,3,1716800000</code>)</li>
    </ul></div></details>
  </div>

  <div class="module" data-module="M3">
    <span class="mod-id">M3</span>
    <h2>Unity 관제UI · ROS-TCP 통신 · 영상</h2>
    <p class="summary">실시간 관제 화면. 로봇 위치, 이벤트 마커, 카메라 패널, 운영 대시보드를 한 씬에서 보여준다.</p>
    <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
    <details open style="margin: 12px 0;"><summary style="font-weight: 700; color: var(--accent-dark);">🖥️ Unity 관제 UI 레이아웃 예시 (참고 디자인)</summary><div class="body">
      <p style="margin: 8px 0;">A.R.O.C. SYSTEM 스타일의 다크 톤 관제 UI 예시. URHYNIX UR-04(실시간 위치)·UR-13(이벤트 마커)·UR-14(색상 구분)·UR-15(타임스탬프)·UR-16(듀얼 로봇)·UR-19(출동 시각화)·UR-20(카메라)·UR-28(운영 대시보드)을 한 씬에 모은 형태.</p>
      %%MOCKUP_IMG%%
      <h3 style="margin-top: 16px;">레이아웃 4 분할</h3>
      <ul>
        <li><strong>좌측 사이드바</strong>: 시스템 명 (HQ COMMAND) + 활성 섹터 + 메뉴 (Fleet Overview / Map Tracking / Vision Analytics) + 하단 배터리/속도/상태/EMERGENCY STOP</li>
        <li><strong>중앙 메인 맵</strong>: 실내 도면 위 로봇 위치(<code>UNIT_01_NAV</code>) + waypoint(<code>WAYPOINT_ALPHA</code>) + 이벤트 마커(좌표 라벨 포함) + 줌/레이어 컨트롤</li>
        <li><strong>우측 시각 분석 패널</strong>: 카메라 라이브 + 인식 객체 목록 (사람 / 장애물 / 문) + confidence 퍼센트</li>
        <li><strong>하단 로그 패널</strong>: 이벤트 종류별 로그 (타임스탬프 · 강도 · 좌표 · 주파수 · 상태) + 우측에 노드 수 / 레이턴시</li>
      </ul>
      <h3>색상·상태 매핑 (UR-14)</h3>
      <ul>
        <li>🟢 NORMAL · 🟡 PATROLLING · 🟠 ALERT · 🔴 EMERGENCY</li>
        <li>이벤트 종류별 마커 색: 화재=빨강 · 소음=주황 · PIR=노랑 · 야간=파랑 · 액자 확인=초록</li>
        <li>보호 대상 상태: 정상 / 확인 필요 / 미확인 + 저장된 사진·영상·사운드 링크</li>
      </ul>
      <h3>구현 우선순위 (학생 MVP)</h3>
      <ol>
        <li>중앙 맵 + 로봇 마커 (UR-04, SCRUM-11) — 최우선</li>
        <li>이벤트 마커 + 좌표 라벨 (UR-13/14) — Must</li>
        <li>우측 카메라 라이브 (UR-20, SCRUM-19) — Must</li>
        <li>하단 로그 + 운영 대시보드 KPI (UR-15/28) — Should</li>
        <li>좌측 사이드바 메뉴 전환 + EMERGENCY STOP (UR-32) — Could</li>
      </ol>
    </div></details>
    <details><summary>핵심 산출물 보기</summary><div class="body"><ul>
      <li>Unity 씬: 실내 맵 + 듀얼 로봇 모델 + 이벤트 마커 + 카메라 패널</li>
      <li>ROS-TCP-Connector 셋업 (<code>/tb3_*/pose</code>, <code>/security/*</code> 구독)</li>
      <li>Pi Camera 라이브 스트림 RawImage 표시</li>
    </ul></div></details>
  </div>

  <div class="module" data-module="M4">
    <span class="mod-id">M4</span>
    <h2>아두이노 센서</h2>
    <p class="summary">PIR · 조도 · 소리 · 불꽃(모의) 네 가지 센서 회로와 임계값을 만들고, 조도 이벤트는 LiDAR 강화 모드의 트리거로 쓴다.</p>
    <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
    <details><summary>핵심 산출물 보기</summary><div class="body"><ul>
      <li>PIR → D2, 조도(LDR+10kΩ) → A0, 소리 → D3, 불꽃 → D4, 모의 버튼 → D5</li>
      <li>회로도 + 임계값 보정 절차</li>
      <li>시리얼 포맷 <code>EVT,&lt;type&gt;,&lt;severity&gt;,&lt;unix_ts&gt;\n</code> (115200 baud)</li>
      <li><strong>연결 확정</strong>: Arduino Uno R3 + 브레드보드 → Raspberry Pi USB serial</li>
      <li>시연 직전 광량/노이즈 환경에서 재캘리브레이션 가이드</li>
    </ul></div></details>
  </div>

  <div class="module" data-module="M5">
    <span class="mod-id">M5</span>
    <h2>터틀봇 — LiDAR · 카메라 · SLAM · Nav</h2>
    <p class="summary">tb3_1은 순찰, tb3_2는 출동. ROS2 bringup부터 Nav2 goal까지 — 움직이는 모든 것.</p>
    <div class="owners"><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
    <details><summary>핵심 산출물 보기</summary><div class="body"><ul>
      <li>ROS2 bringup 패키지 (tb3_1, tb3_2 각각)</li>
      <li>SLAM 맵 + waypoint follower (tb3_1 순찰)</li>
      <li>Dispatcher 노드 + tb3_2 Nav2 goal 발행</li>
      <li>Pi Camera 토픽 발행 (<code>/tb3_*/camera/image_raw</code>)</li>
    </ul></div></details>
  </div>

  <div style="margin-top: 24px; background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 28px 32px;">
    <span class="mod-id" style="background: #6b7280;">HW</span>
    <h2 style="font-size: 30px; margin: 0 0 12px;">하드웨어 적층 (TurtleBot 1대당)</h2>
    <p class="summary" style="font-size: 19px; margin: 0 0 16px;">LiDAR는 최상단 그대로. <strong>별도 층 추가 없음</strong> — Arduino + 미니 브레드보드는 Burger 상판 빈 공간에 양면테이프로 부착. 어두움 감지 시에는 저속 순찰·스캔/pose 로그 저장 빈도를 높인다.</p>
    <details><summary>적층 도면 + 부품 리스트 보기</summary><div class="body">
      <pre style="background: var(--bg); padding: 14px; border-radius: 8px; font-size: 13px; line-height: 1.5; overflow-x: auto;">
┌──────────────────────────┐
│  🔵 LDS LiDAR (360°)     │  ← 최상단 (양보 X)
└──────────────────────────┘
┌──────────────────────────┐
│ 🟢 Raspberry Pi (치우침) │  + 반대편 빈 공간에
│ 🟡 Arduino Uno + 미니브  │     양면테이프로 부착 (같은 층)
│    레드보드 + 센서 4종    │     점퍼선은 LiDAR 회전 평면 아래
└──────────────────────────┘
      │ USB Type-B   │ OpenCR 5V 점퍼
      ▼              ▼
┌──────────────────────────┐
│  ⚪ OpenCR (펌웨어 그대로)│
└──────────────────────────┘
┌──────────────────────────┐
│  ⚫ 배터리 / 모터        │
└──────────────────────────┘</pre>
      <h3>마운팅 방향</h3>
      <ul>
        <li><strong>PIR</strong> 정면 · <strong>조도</strong> 위쪽 · <strong>소리</strong> 무방향 · <strong>불꽃/모의</strong> 정면</li>
      </ul>
    </div></details>
  </div>

  <div class="nav-footer">
    <a href="#roles">← 역할</a>
    <a href="#sprints">Sprint 보드 →</a>
  </div>
</div>
</section>

<!-- ============== SPRINTS ============== -->
<section class="page" data-page="sprints">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">🗓️ Sprint 보드</span>
  <h2 class="sub-h1">7주를<br>4 스프린트로</h2>
  <p class="lead">단일 → 센서 → DB+출동 → 데모. 한 발씩 통하게 만든다. 펼치면 그 스프린트의 작업 카드(Jira 링크)가 보인다.</p>

  <div class="timeline">
    <div class="tb s1">S1 · 2주</div>
    <div class="tb s2">S2 · 2주</div>
    <div class="tb s3">S3 · 2주</div>
    <div class="tb s4">S4 · 1주</div>
  </div>

  <details open style="margin: 0 0 32px; background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px 28px;">
    <summary style="font-size: 18px; color: var(--accent-dark); font-weight: 700; padding-bottom: 8px;">⚡ 병렬 작업 매트릭스</summary>
    <div class="body" style="margin-top: 16px;">
      <p><strong>원칙</strong>: 한 모듈 안에서는 순차, 모듈 간에는 병렬. <code>CONTRACT.md</code> 인터페이스만 합의된 상태면 각자 동시에 진행 가능.</p>
      <h3>S1 1주차 동시 시작 4팀</h3>
      <ul>
        <li><strong>DB팀</strong> (김주영·김선일) — SCRUM-14 스키마 SQL</li>
        <li><strong>Unity팀</strong> (김선일·박태진) — SCRUM-9 듀얼 로봇 씬</li>
        <li><strong>HW팀</strong> (박태진·임현찬) — SCRUM-16 트랙 + 키트 점검</li>
        <li><strong>센서팀</strong> (김주영·임현찬·박태진) — 키트 점검 + 회로도</li>
      </ul>
      <h3>주차 × 모듈 매트릭스</h3>
      <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <thead><tr style="background: var(--hover);"><th style="padding: 8px;">주</th><th style="padding: 8px;">M1</th><th style="padding: 8px;">M2</th><th style="padding: 8px;">M3</th><th style="padding: 8px;">M4</th><th style="padding: 8px;">M5</th><th style="padding: 8px;">공통</th></tr></thead>
        <tbody>
          <tr><td style="padding: 6px;"><strong>W1</strong></td><td style="padding: 6px;">SCRUM-14</td><td style="padding: 6px;">키트 점검</td><td style="padding: 6px;">SCRUM-9</td><td style="padding: 6px;">회로도</td><td style="padding: 6px;">—</td><td style="padding: 6px;">SCRUM-8, 16</td></tr>
          <tr><td style="padding: 6px;"><strong>W2</strong></td><td style="padding: 6px;">계속</td><td style="padding: 6px;">키트 확인</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">동작확인</td><td style="padding: 6px;">SCRUM-10</td><td style="padding: 6px;">—</td></tr>
          <tr><td style="padding: 6px;"><strong>W3</strong></td><td style="padding: 6px;">—</td><td style="padding: 6px;">SCRUM-13</td><td style="padding: 6px;">SCRUM-11</td><td style="padding: 6px;">SCRUM-13</td><td style="padding: 6px;">SCRUM-20</td><td style="padding: 6px;">—</td></tr>
          <tr><td style="padding: 6px;"><strong>W4</strong></td><td style="padding: 6px;">—</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">SCRUM-22</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">SCRUM-19</td><td style="padding: 6px;">—</td></tr>
          <tr><td style="padding: 6px;"><strong>W5</strong></td><td style="padding: 6px;">SCRUM-23</td><td style="padding: 6px;">—</td><td style="padding: 6px;">SCRUM-25</td><td style="padding: 6px;">SCRUM-17</td><td style="padding: 6px;">SCRUM-12</td><td style="padding: 6px;">—</td></tr>
          <tr><td style="padding: 6px;"><strong>W6</strong></td><td style="padding: 6px;">SCRUM-21</td><td style="padding: 6px;">—</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">계속</td><td style="padding: 6px;">—</td></tr>
          <tr><td style="padding: 6px;"><strong>W7</strong></td><td style="padding: 6px;">SCRUM-15</td><td style="padding: 6px;">—</td><td style="padding: 6px;">SCRUM-24</td><td style="padding: 6px;">—</td><td style="padding: 6px;">—</td><td style="padding: 6px;">SCRUM-18</td></tr>
        </tbody>
      </table>
      <h3>직렬 병목</h3>
      <ul>
        <li>SCRUM-8 합의 → 모든 작업</li>
        <li>SCRUM-16 → SCRUM-10 SLAM</li>
        <li>SCRUM-13 → SCRUM-12, 21</li>
        <li>SCRUM-14 → SCRUM-23(좌표·미디어·보호 대상 예정), 15</li>
        <li>SCRUM-19 → SCRUM-25, 23</li>
      </ul>
    </div>
  </details>

  <div class="sprint" data-sprint="S1">
    <div class="sprint-head"><span class="sprint-id">S1</span><h2>단일 로봇 베이스라인</h2><span class="duration">2주</span></div>
    <p class="goal">tb3_1 한 대로 순찰 주행 + Unity pose 표시 + DB 스키마 초안까지 라인을 통하게 만든다. 모든 후속의 토대.</p>
    <details><summary>작업 카드 5개 보기</summary><div class="tickets">
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-8" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-8</span></div>
        <div class="title">MVP 범위·역할 매트릭스·SSOT 합의</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-9" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-9</span></div>
        <div class="title">Unity 박물관/미술관 + 듀얼 로봇 표시 관제 UI 초안</div>
        <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-10" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-10</span></div>
        <div class="title">tb3_1 SLAM/Nav2 기본 순찰 베이스라인</div>
        <div class="owners"><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-16" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-16</span></div>
        <div class="title">실내 트랙 + 박물관/미술관 경비 구역 + 야간 모드 환경 세팅</div>
        <div class="owners"><span class="owner-chip" data-owner="박태진">박태진</span><span class="owner-chip" data-owner="임현찬">임현찬</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-14" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-14</span></div>
        <div class="title">DB 스키마 초안 + events 마이그레이션 + 확장 테이블 계획</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
    </div></details>
  </div>

  <div class="sprint" data-sprint="S2">
    <div class="sprint-head"><span class="sprint-id">S2</span><h2>센서 + 이벤트 1종</h2><span class="duration">2주</span></div>
    <p class="goal">아두이노 센서 1종으로 이벤트를 발행해 Unity 마커까지 띄운다. "감지 → 표시" 한 줄 통과.</p>
    <details><summary>작업 카드 5개 보기</summary><div class="tickets">
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-13" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-13</span></div>
        <div class="title">아두이노 센서 1종(PIR/조도) → /security/event 발행</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-19" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-19</span></div>
        <div class="title">Pi Camera 설치 + 카메라 스트림 발행</div>
        <div class="owners"><span class="owner-chip" data-owner="박태진">박태진</span><span class="owner-chip" data-owner="임현찬">임현찬</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-20" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-20</span></div>
        <div class="title">tb3_1 pose ↔ 센서 이벤트 timestamp 동기화</div>
        <div class="owners"><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-11" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-11</span></div>
        <div class="title">Unity에 tb3_1 위치·경로·이벤트 마커 표시</div>
        <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-22" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-22</span></div>
        <div class="title">야간 모드 / 이벤트 패널 / 운영 대시보드 UI</div>
        <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
    </div></details>
  </div>

  <div class="sprint" data-sprint="S3">
    <div class="sprint-head"><span class="sprint-id">S3</span><h2>DB + 2호기 출동 시뮬</h2><span class="duration">2주</span></div>
    <p class="goal">모든 이벤트가 DB에 저장되고, tb3_2가 (시뮬 또는 실기) 출동해 카메라로 액자 주변을 확인하는 흐름 완성.</p>
    <details><summary>작업 카드 5개 보기</summary><div class="tickets">
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-12" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-12</span></div>
        <div class="title">tb3_2 출동 로직 — dispatch 수신 → Nav2 goal</div>
        <div class="owners"><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-17" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-17</span></div>
        <div class="title">추가 센서(소리·불꽃 모의) + 임계값 캘리브</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="임현찬">임현찬</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-21" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-21</span></div>
        <div class="title">라벨링 + AI 오탐/실탐 분류 보조 모델 + 액자형 중요물품 인식</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-23" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-23</span></div>
        <div class="title">이벤트·좌표·사진·영상·사운드 저장 구조 확장</div>
        <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="김주영">김주영</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-25" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-25</span></div>
        <div class="title">Pi Camera 라이브 스트리밍 → Unity 패널</div>
        <div class="owners"><span class="owner-chip" data-owner="김선일">김선일</span><span class="owner-chip" data-owner="박태진">박태진</span></div>
      </a>
    </div></details>
  </div>

  <div class="sprint" data-sprint="S4">
    <div class="sprint-head"><span class="sprint-id">S4</span><h2>2대 실기 확장 + 발표 데모</h2><span class="duration">1주</span></div>
    <p class="goal">박물관/미술관 액자 보호 컨셉으로 시나리오 4종을 시연하고 발표 지표 표를 만든다. 가능하면 2대 실기 동시 주행.</p>
    <details><summary>작업 카드 3개 보기</summary><div class="tickets">
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-15" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-15</span></div>
        <div class="title">액자 보호 시나리오 4종 통합 시연 + 발표 지표 표</div>
        <div class="owners"><span class="owner-chip" data-owner="김주영">김주영</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-18" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-18</span></div>
        <div class="title">최종 시연 환경 — 2대 동시 구동 + 광량 준비</div>
        <div class="owners"><span class="owner-chip" data-owner="박태진">박태진</span><span class="owner-chip" data-owner="임현찬">임현찬</span></div>
      </a>
      <a class="ticket" href="https://jason1127.atlassian.net/browse/SCRUM-24" target="_blank" rel="noopener">
        <div class="ticket-head"><span class="ticket-id">SCRUM-24</span></div>
        <div class="title">발표용 화면/영상/시나리오 컷 캡처</div>
        <div class="owners"><span class="owner-chip" data-owner="박태진">박태진</span><span class="owner-chip" data-owner="김선일">김선일</span></div>
      </a>
    </div></details>
  </div>

  <div class="nav-footer">
    <a href="#modules">← 모듈</a>
    <a href="#scenarios">시나리오 4종 →</a>
  </div>
</div>
</section>

<!-- ============== SCENARIOS ============== -->
<section class="page" data-page="scenarios">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">🎬 액자 보호 시나리오 4종</span>
  <h2 class="sub-h1">발표에서<br>보여줄<br>4가지 장면</h2>
  <p class="lead">박물관/미술관 구역에서 액자형 사진 타깃을 지키며 야간 모드 → 외부자 감지 → 이상 소음 → 화재 의심을 시연한다. 같은 흐름(감지 → Unity 표시 → tb3_2 출동 → 카메라 확인 → 좌표·사진·영상·사운드 DB 저장)을 4가지 트리거로 보여준다.</p>

  <div class="scenario" data-kind="night">
    <div class="scenario-head"><span class="scn-icon">🌙</span><h2>야간 경비 모드</h2><span class="sensor-chip">조도 센서</span></div>
    <p class="summary">실내가 어두워지면 야간 모드가 켜지고 tb3_1이 액자형 보호 대상 주변을 저속 순찰한다. Unity 관제 화면은 <code>Night Patrol</code>과 LiDAR 강화 상태를 함께 표시한다.</p>
    <details><summary>흐름과 표시 방식 보기</summary><div class="body">
      <h3>흐름</h3>
      <div class="flow">조도 임계값 하향 → /security/event(dark) → Unity 모드 토글 → tb3_1 저속 순찰 + pose/LiDAR 로그 빈도 증가</div>
      <h3>발표 포인트</h3>
      <ul>
        <li>발표 시연에서는 손으로 센서를 가려 야간 모드 트리거</li>
        <li>Unity 상단 모드 라벨이 즉시 변하는 것이 시각적 효과</li>
        <li>오탐을 막기 위해 임계값은 시연장에서 재캘리브 (SCRUM-18)</li>
      </ul>
    </div></details>
  </div>

  <div class="scenario" data-kind="pir">
    <div class="scenario-head"><span class="scn-icon">🚶</span><h2>외부자 감지</h2><span class="sensor-chip">PIR + LiDAR</span></div>
    <p class="summary">PIR이 사람 움직임을 감지하면 LiDAR 거리 변화와 pose 맥락을 함께 저장한다. tb3_2가 감지 좌표로 출동해 Pi Camera로 액자 주변 현장을 확인한다.</p>
    <details><summary>흐름과 표시 방식 보기</summary><div class="body">
      <h3>흐름</h3>
      <div class="flow">PIR HIGH + LiDAR 변화 → /security/event(pir) → Unity 마커 표시 → dispatcher → /security/dispatch → tb3_2 Nav2 → 도착 → /security/camera_confirm → DB 기록</div>
      <h3>발표 포인트</h3>
      <ul>
        <li>이 시나리오가 MVP의 가장 핵심 — "감지 → 출동 → 확인"의 전 체인을 보여준다</li>
        <li>Pi Camera 라이브 스트림이 Unity 패널에 뜨는 순간이 클라이맥스</li>
        <li>response_time, pose 로그, 사진/영상 경로가 DB에 저장되어 발표 지표에 사용</li>
      </ul>
    </div></details>
  </div>

  <div class="scenario" data-kind="noise">
    <div class="scenario-head"><span class="scn-icon">🔊</span><h2>이상 소음</h2><span class="sensor-chip">소리 센서</span></div>
    <p class="summary">소리 센서가 임계값 이상을 감지하면 <code>noise_alert</code>가 발행된다. 반복 감지 횟수나 강도에 따라 severity가 올라간다.</p>
    <details><summary>흐름과 표시 방식 보기</summary><div class="body">
      <h3>흐름</h3>
      <div class="flow">마이크 → 임계값 초과 → /security/event(noise, severity=2~3) → Unity 타임라인 누적 → 일정 횟수 이상 시 tb3_2 출동</div>
      <h3>발표 포인트</h3>
      <ul>
        <li>한 번의 단일 이벤트가 아니라 <strong>누적/반복</strong>으로 위험도가 올라가는 패턴</li>
        <li>Unity 타임라인 패널에 점들이 쌓이는 시각적 효과</li>
        <li>오탐(노이즈)이 흔한 영역 — AI 분류 보조 모델(SCRUM-21)의 효과를 보여주는 자리</li>
      </ul>
    </div></details>
  </div>

  <div class="scenario" data-kind="fire">
    <div class="scenario-head"><span class="scn-icon">🔥</span><h2>화재 의심 (모의)</h2><span class="sensor-chip">불꽃 센서 · 모의</span></div>
    <p class="summary">실제 불꽃 테스트는 금지. 모의 입력(버튼·플래그)으로 <code>fire_alert</code>를 발행하고, 카메라는 액자형 사진 타깃 주변을 확인한다. Unity는 빨간 마커와 경고 패널로 즉시 표시.</p>
    <details><summary>흐름과 표시 방식 보기</summary><div class="body">
      <h3>흐름</h3>
      <div class="flow">모의 입력 버튼 → /security/event(fire, severity=3) → Unity 빨간 마커 + 경고 패널 → tb3_2 즉시 출동 → 액자 주변 카메라 확인 + 영상/사운드 저장</div>
      <h3>발표 포인트</h3>
      <ul>
        <li>실제 불꽃 대신 모의 입력을 쓴다는 점을 발표에서 명시 — "안전 우선 설계"의 일부로 소개</li>
        <li>severity 3 이벤트는 다른 모든 이벤트를 가로채고 즉시 출동</li>
        <li>가장 극적인 화면 (빨간 풀스크린 경고)을 시연 마지막에 배치 권장</li>
      </ul>
    </div></details>
  </div>

  <div class="nav-footer">
    <a href="#sprints">← Sprint 보드</a>
    <a href="#risks">위험 →</a>
  </div>
</div>
</section>

<!-- ============== RISKS ============== -->
<section class="page" data-page="risks">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">⚠️ 위험</span>
  <h2 class="sub-h1">이건<br>깨질 수 있다</h2>
  <p class="lead">이번 7주 안에 우리를 막을 수 있는 6가지. 미리 안 보면 막판에 폭발한다. 펼쳐서 대응 방법까지.</p>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">01</span><h2>아두이노 센서 노이즈</h2></div>
    <p class="summary">PIR과 소리 센서가 가짜 신호를 자주 뱉을 수 있다. 발표 도중 오탐이 쏟아지면 끝.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>S2 초반에 센서 임계값을 캘리브레이션. 환경 광량·진동 조건별 두 세트 준비.</li>
      <li>S3에서 AI 오탐/실탐 분류 보조 모델로 한 번 더 거른다 (SCRUM-21).</li>
      <li>발표 직전 시연 장소에서 5분 노이즈 측정 후 임계값 재조정.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">02</span><h2>ROS-Unity 통신 지연</h2></div>
    <p class="summary">카메라 스트림이 Unity까지 느리게 오면 관제 화면이 끊긴다. 발표 임팩트가 즉시 무너진다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>S2 초반에 ROS-TCP-Connector 부하 측정. 토픽별 Hz와 지연 기록.</li>
      <li>카메라 토픽 다운샘플 (15Hz 이하) + 해상도 축소.</li>
      <li>Pose 토픽은 별도 빠른 경로로, 이미지는 별도 채널로 분리.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">03</span><h2>브레드보드 점퍼 빠짐 · LiDAR 시야 가림</h2></div>
    <p class="summary">시연 중 점퍼선이 빠지면 센서 신호가 끊긴다. Arduino 층이 너무 높아 LiDAR 시야를 가리면 SLAM이 깨진다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>발표 직전 점퍼선을 절연테이프로 고정. Arduino + 브레드보드는 양면테이프로 상판 부착.</li>
      <li>여유 있으면 S3쯤 만능기판(perfboard)으로 이전.</li>
      <li>M3 스페이서는 <strong>30~40mm 권장</strong>. 그 이상은 LiDAR 회전 시 진동·시야 가림 위험.</li>
      <li>점퍼 케이블이 LiDAR 회전 반경 안으로 들어가지 않도록 케이블 타이로 정리.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">04</span><h2>TurtleBot3 2대 동시 구동 실패</h2></div>
    <p class="summary">하드웨어 2대가 동시에 안정적으로 돌지 못하면 듀얼 로봇 콘셉트 자체가 무너진다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>S1~S2에 박태진/임현찬이 2대 동시 부팅을 사전 확인. 백업 배터리·부품 확보.</li>
      <li>축소안: <strong>1대 실기 + 1대 Unity 시뮬레이션 로봇</strong>으로 시연 가능하도록 S3까지 코드 유지.</li>
      <li>발표 당일은 일찍 도착해 두 대 모두 부팅·SLAM 확인 후 본 시연.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">05</span><h2>시연 환경 광량 변화 · LiDAR 강화 모드 과다 동작</h2></div>
    <p class="summary">조도 센서가 시연장 조명 조건에서 야간 모드 트리거를 못 하거나 너무 자주 트리거할 수 있다. LiDAR 강화 모드는 저속 순찰·pose 로그 빈도 증가로 표현하므로 과다 저장도 리스크다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>S4 직전 시연 장소에서 조도 임계값 재캘리브레이션 (SCRUM-18).</li>
      <li>발표 중에는 수동 토글(<code>/unity/manual_dispatch</code>)로 야간 모드 강제 진입 가능하도록 백도어 준비.</li>
      <li>어두움 유지 중 중복 row 폭주를 막기 위해 edge-trigger + 히스테리시스를 유지.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">06</span><h2>액자형 사진 타깃 인식 · 미디어 저장 실패</h2></div>
    <p class="summary">카메라가 액자형 보호 대상을 못 찾거나 사진/영상/사운드 저장 경로가 끊기면 박물관 컨셉의 설득력이 떨어진다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>1차 인식은 AprilTag/QR/고대비 프레임 마커로 단순화하고, AI 분류는 보조로 둔다.</li>
      <li>SCRUM-23 확장 후 DB에는 원본 파일을 직접 넣지 않고 <code>media_artifacts.storage_path</code>와 메타데이터만 저장한다.</li>
      <li>시연 전 <code>frame_01</code> 샘플 액자와 test image/video/audio path 1건씩 seed.</li>
    </ul></div></details>
  </div>

  <div class="risk">
    <div class="risk-head"><span class="risk-num">07</span><h2>일정 지연</h2></div>
    <p class="summary">7주는 빠듯하다. S3 끝에 v4(2대 실기)가 위태로우면 단순화 결정을 해야 한다.</p>
    <details><summary>대응 방법 보기</summary><div class="body"><ul>
      <li>S3 종료 시점에 v4 가능성 평가. 어려우면 <strong>2대 실기 → 1대 실기 + 1대 시뮬</strong>로 축소.</li>
      <li>AI 분류(SCRUM-21)는 임계값 비교로 대체 가능.</li>
      <li>화재/소리 시나리오는 모의 입력만 시연하고 발표에서 명시.</li>
    </ul></div></details>
  </div>

  <div class="nav-footer">
    <a href="#scenarios">← 시나리오</a>
    <a href="#exclusions">제외 범위 →</a>
  </div>
</div>
</section>

<!-- ============== EXCLUSIONS ============== -->
<section class="page" data-page="exclusions">
<div class="wrap">
  <div class="topbar">
    <a href="#home">← 메인</a>
    <span>URHYNIX · 디지털트윈경비로봇</span>
  </div>
  <span class="badge">🚫 제외 범위</span>
  <h2 class="sub-h1">이번엔<br>안 만든다</h2>
  <p class="lead">발표 7주 안에 다 하려면 잘라야 한다. 이 6가지는 일부러 뺀다. 펼치면 왜 뺐는지 보인다.</p>

  <div class="item">
    <div class="item-head"><span class="item-num">01</span><h2>FR5 로봇팔 · 픽앤플레이스</h2></div>
    <p class="summary">협동 로봇팔로 물건을 집어 옮기는 작업은 이번에 안 한다.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>2026-05-26 결정. 7~8주 일정 안에서는 TurtleBot3 자율주행·Unity 관제·이벤트 대응에 집중하는 편이 성공 가능성이 훨씬 높다. 로봇팔은 별도 학기 또는 후속 프로젝트로.</p>
    </div></details>
  </div>

  <div class="item">
    <div class="item-head"><span class="item-num">02</span><h2>실시간 사람 추적</h2></div>
    <p class="summary">감지된 사람을 따라다니며 좌표 기반으로 follow 하는 동작은 안 한다.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>사람 좌표 추정 정확도와 안전 제약을 7주에 풀기 어렵다. 대신 <strong>감지 위치로 출동 + Pi Camera 확인</strong>으로 시나리오를 정의했다. 발표 메시지도 "추적"이 아니라 "대응"으로 잡는다.</p>
    </div></details>
  </div>

  <div class="item">
    <div class="item-head"><span class="item-num">03</span><h2>실제 화재 테스트</h2></div>
    <p class="summary">진짜 불꽃으로 불꽃 센서를 테스트하지 않는다. 모의 입력으로 대체.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>실내에서 실제 불꽃을 다루는 건 안전·법적 문제. 모의 입력(버튼·플래그)이나 안전한 발열 소스로만 테스트하고, 발표에서 "안전 우선 설계의 일부"로 명시한다. 센서 자체는 동작하지만 트리거만 모의로.</p>
    </div></details>
  </div>

  <div class="item">
    <div class="item-head"><span class="item-num">04</span><h2>완전 자동 보안 시스템 수준의 인증·권한</h2></div>
    <p class="summary">사용자 인증, 역할 권한, 감사 로그 같은 production 보안 기능은 안 만든다.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>이번은 "시연 가능한 디지털 트윈 프로토타입". 시연 영역 안에서는 모든 사용자가 운영자라고 가정. DB도 단일 운영자 모드로 운영. 인증은 후속 단계로.</p>
    </div></details>
  </div>

  <div class="item">
    <div class="item-head"><span class="item-num">05</span><h2>복잡한 멀티로봇 최적 경로 계획</h2></div>
    <p class="summary">두 로봇이 경로를 협상해 최적화하는 알고리즘은 안 넣는다. waypoint 기반 단순 출동만.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>Multi-robot path planning은 7주에 풀 깊이가 아니다. tb3_2는 <strong>이벤트 좌표 근처 waypoint로 Nav2 goal</strong> 한 번만 발행. 충돌 회피는 각 로봇의 로컬 Nav2 costmap에 맡긴다.</p>
    </div></details>
  </div>

  <div class="item">
    <div class="item-head"><span class="item-num">06</span><h2>로봇 간 물리적 협동 작업</h2></div>
    <p class="summary">두 로봇이 같이 물건을 들거나 미는 등의 물리 협업은 안 한다.</p>
    <details><summary>이유 보기</summary><div class="body">
      <p>본 프로젝트의 "협동"은 <strong>역할 분담 협동</strong>(감지 로봇 + 확인 로봇)이지 물리적 동시 작업이 아니다. 발표에서도 이 점을 명확히 한다.</p>
    </div></details>
  </div>

  <div class="nav-footer">
    <a href="#risks">← 위험</a>
    <a href="#home">메인 →</a>
  </div>
</div>
</section>

<script>
(function(){
  var valid = new Set(['home','roles','modules','sprints','scenarios','risks','exclusions']);

  function route(){
    var hash = (location.hash || '#home').replace('#','');
    if (!valid.has(hash)) hash = 'home';
    document.body.setAttribute('data-page', hash);
    document.querySelectorAll('section.page').forEach(function(sec){
      sec.classList.toggle('active', sec.getAttribute('data-page') === hash);
    });
    window.scrollTo(0, 0);
  }

  window.addEventListener('hashchange', route);
  document.addEventListener('DOMContentLoaded', route);
  route();
})();
</script>

</body>
</html>
"""


def main() -> None:
    out = (HTML
           .replace("%%MATRIX_B64%%", MATRIX_B64)
           .replace("%%GRAPH_B64%%", GRAPH_B64)
           .replace("%%MOCKUP_B64%%", MOCKUP_B64)
           .replace("%%MOCKUP_IMG%%", MOCKUP_IMG_HTML))
    target = DOCS / "dev-plan-bundle.html"
    target.write_text(out, encoding="utf-8")
    size_kb = target.stat().st_size / 1024
    print(f"WROTE: {target}  ({size_kb:,.1f} KB)")


if __name__ == "__main__":
    main()
