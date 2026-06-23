// 박물관 경비 로봇 시나리오 그래프 데이터 (D3+dagre 렌더 소스).
// 원천 SSOT: Confluence "Sequence diagram" (jason1127.atlassian.net, page 19431426, v13) — 손그림 플로우 6장.
//   s0 = 마스터(순찰 및 이벤트 사항대응), s1~s5 = 개별 시나리오. 다이어그램에 1:1 충실.
// node.type: start|process|decision|end  (다이어그램의 "관리자 판단" 평행사변형 = 분기이므로 decision 으로 모델링).
// node.risk: safe|watch|check|danger|evac — 다이어그램엔 색이 없어 심각도 기준으로 위험 등급 매핑(앱 범례 SAFE→EVACUATE).
// tour: 발표 단계 진행 순서(노드 id). 인접 엣지가 있으면 점이 그 엣지를 따라 흐른다.
// 결정 노드 엣지 정렬: [0]=← (복귀·오탐), [1]=→ (격상·조치). 3분기 결정은 [2]가 추가 분기(클릭 점프).
window.SCENARIOS = [
  {
    id: "s0",
    title: "#0 순찰 및 이벤트 사항대응",
    summary: "전체 개요 · 순찰대기↔배터리 교대 + 순찰중 이벤트 감지(장애물·이상소리·도난) → 의심 시 경찰 신고·Gen.G",
    nodes: [
      { id: "s",       type: "start",    label: "Start" },
      { id: "wait",    type: "process",  risk: "safe",  label: "순찰 대기" },
      { id: "charge",  type: "process",  risk: "safe",  label: "충전소 이동" },
      { id: "bat",     type: "decision", label: "배터리\n30% 이하?" },
      { id: "gx",      type: "process",  risk: "check", label: "Gen.G 교대" },
      { id: "patrol",  type: "process",  risk: "safe",  label: "순찰 중" },
      { id: "ev",      type: "decision", label: "이벤트\n감지?" },
      { id: "obj",     type: "decision", label: "장애물\n판단" },
      { id: "avoid",   type: "process",  risk: "safe",  label: "우회함" },
      { id: "waitobj", type: "process",  risk: "watch", label: "사라질 때까지\nor 7초간 대기" },
      { id: "notify",  type: "process",  risk: "watch", label: "관리자에게 알림" },
      { id: "track",   type: "process",  risk: "check", label: "의심자 트래킹" },
      { id: "susp",    type: "decision", label: "의심?" },
      { id: "police",  type: "process",  risk: "danger",label: "경찰 신고/알림\nGen.G 출동" }
    ],
    edges: [
      { from: "s",      to: "wait" },
      { from: "charge", to: "wait",   label: "완충시" },
      { from: "wait",   to: "bat" },
      { from: "bat",    to: "patrol", label: "순찰명령" },
      { from: "bat",    to: "gx",     label: "출동요청" },
      { from: "gx",     to: "charge" },
      { from: "patrol", to: "ev" },
      { from: "ev",     to: "obj",    label: "장애물 감지" },
      { from: "ev",     to: "track",  label: "도난" },
      { from: "ev",     to: "notify", label: "이상소리 감지" },
      { from: "obj",    to: "avoid",  label: "정적" },
      { from: "obj",    to: "waitobj",label: "동적" },
      { from: "avoid",  to: "patrol" },
      { from: "waitobj",to: "avoid" },
      { from: "notify", to: "patrol" },
      { from: "track",  to: "susp",   label: "경비원 호출" },
      { from: "susp",   to: "patrol", label: "의심 해소" },
      { from: "susp",   to: "police", label: "의심 유지" },
      { from: "police", to: "patrol" }
    ],
    tour: ["s", "wait", "bat", "patrol", "ev", "track", "susp", "police"]
  },

  {
    id: "s1",
    title: "#1 폐관 후 침입자 확인",
    summary: "순찰 중 소리·인체 감지 → 지속여부 분석 → 사람 판독 → Gen.G 재확인 → 관리자 판단 → 112 신고·차단벽",
    nodes: [
      { id: "s",       type: "start",    label: "Start" },
      { id: "patrol",  type: "process",  risk: "safe",  label: "순찰 중" },
      { id: "ev",      type: "decision", label: "이벤트\n감지?" },
      { id: "move",    type: "process",  risk: "watch", label: "소리난 곳으로\n이동" },
      { id: "rec",     type: "process",  risk: "watch", label: "인체 감지 기록 및\n사람 지속여부 분석" },
      { id: "read",    type: "decision", label: "사람\n판독" },
      { id: "geng",    type: "process",  risk: "check", label: "Gen.G 출동" },
      { id: "recheck", type: "decision", label: "재확인" },
      { id: "mgr",     type: "decision", label: "관리자\n판단" },
      { id: "report",  type: "process",  risk: "danger",label: "112 신고\n차단벽 폐쇄 요청" }
    ],
    edges: [
      { from: "s",       to: "patrol" },
      { from: "patrol",  to: "ev" },
      { from: "ev",      to: "move",   label: "소리감지" },
      { from: "ev",      to: "rec",    label: "인체 감지" },
      { from: "move",    to: "rec" },
      { from: "rec",     to: "read",   label: "인체 감지" },
      { from: "read",    to: "patrol", label: "사람 아님" },
      { from: "read",    to: "geng",   label: "관리자 호출" },
      { from: "geng",    to: "recheck",label: "재확인 결과 표시" },
      { from: "recheck", to: "patrol", label: "사람 아님" },
      { from: "recheck", to: "mgr",    label: "의심 유지" },
      { from: "mgr",     to: "patrol", label: "사람 아님" },
      { from: "mgr",     to: "report", label: "도둑·강도 결정" },
      { from: "report",  to: "patrol" }
    ],
    tour: ["s", "patrol", "ev", "rec", "read", "geng", "recheck", "mgr", "report"]
  },

  {
    id: "s2",
    title: "#2 중요 전시품 분실",
    summary: "전시품 위치 이동 → 주위 순찰 2번 스캔 → 상황 판단 → Gen.G 출동 → 관리자 판단 → 112 신고·차단벽",
    nodes: [
      { id: "s",      type: "start",    label: "Start" },
      { id: "patrol", type: "process",  risk: "safe",  label: "순찰 중" },
      { id: "moveto", type: "process",  risk: "safe",  label: "전시품 위치 이동" },
      { id: "scan",   type: "process",  risk: "watch", label: "주위 순찰\n2번 스캔" },
      { id: "judge",  type: "decision", label: "상황\n판단" },
      { id: "geng",   type: "process",  risk: "check", label: "Gen.G 출동" },
      { id: "mgr",    type: "decision", label: "관리자\n판단" },
      { id: "report", type: "process",  risk: "danger",label: "112 신고\n차단벽 폐쇄 요청" }
    ],
    edges: [
      { from: "s",      to: "patrol" },
      { from: "patrol", to: "moveto" },
      { from: "moveto", to: "scan",   label: "지정위치 스캔" },
      { from: "scan",   to: "judge",  label: "관리자 호출" },
      { from: "judge",  to: "patrol", label: "이상없음" },
      { from: "judge",  to: "geng",   label: "분실 상황발생" },
      { from: "geng",   to: "mgr",    label: "재확인" },
      { from: "mgr",    to: "patrol", label: "이상없음" },
      { from: "mgr",    to: "report", label: "도둑·강도 결정" },
      { from: "report", to: "patrol" }
    ],
    tour: ["s", "patrol", "moveto", "scan", "judge", "geng", "mgr", "report"]
  },

  {
    id: "s3",
    title: "#3 화재 의심 즉시 대응",
    summary: "화재 판단 → 안전거리 이동·Gen.G 대피경로 안내 → 관리자 판단 → 119 신고 → 안전유지 순찰 → 대피자 판단 → 대피",
    nodes: [
      { id: "s",          type: "start",    label: "Start" },
      { id: "patrol",     type: "process",  risk: "safe",  label: "순찰 중" },
      { id: "fire",       type: "decision", label: "화재\n판단" },
      { id: "safezone",   type: "process",  risk: "check", label: "안전거리 이동" },
      { id: "geng",       type: "process",  risk: "check", label: "Gen.G 출동\n대피 경로 안내" },
      { id: "mgr",        type: "decision", label: "관리자\n판단" },
      { id: "call119",    type: "process",  risk: "evac",  label: "119 신고" },
      { id: "safepatrol", type: "process",  risk: "evac",  label: "안전 유지 순찰" },
      { id: "evacA",      type: "decision", label: "대피자\n판단" },
      { id: "alert",      type: "process",  risk: "danger",label: "사람 있음 알림" },
      { id: "evacB",      type: "decision", label: "대피자\n판단" },
      { id: "evac",       type: "process",  risk: "evac",  label: "대피" },
      { id: "e",          type: "end",      label: "종료" }
    ],
    edges: [
      { from: "s",          to: "patrol" },
      { from: "patrol",     to: "fire" },
      { from: "fire",       to: "patrol",     label: "연소" },
      { from: "fire",       to: "safezone",   label: "화재감지 대피 알림" },
      { from: "safezone",   to: "geng",       label: "대피 경로 안내" },
      { from: "geng",       to: "mgr",        label: "화재 재확인 요청" },
      { from: "mgr",        to: "patrol",     label: "상황 종료" },
      { from: "mgr",        to: "call119",    label: "화재 발생" },
      { from: "call119",    to: "safepatrol" },
      { from: "safepatrol", to: "evacA" },
      { from: "evacA",      to: "alert",      label: "남은 사람 있음" },
      { from: "evacA",      to: "evac",       label: "모두 대피" },
      { from: "alert",      to: "evacB" },
      { from: "evacB",      to: "evac",       label: "모두 대피" },
      { from: "evac",       to: "e" }
    ],
    tour: ["s", "patrol", "fire", "safezone", "geng", "mgr", "call119", "safepatrol", "evacA", "alert", "evacB", "evac", "e"]
  },

  {
    id: "s4",
    title: "#4 개장 중 전시품 접촉",
    summary: "개장 순찰 중 이벤트 감지(장애물·이상소리·도난) → 의심자 트래킹 → 의심 → 경찰 신고·Gen.G",
    nodes: [
      { id: "s",       type: "start",    label: "Start" },
      { id: "wait",    type: "process",  risk: "safe",  label: "순찰 대기" },
      { id: "patrol",  type: "process",  risk: "safe",  label: "순찰 중" },
      { id: "ev",      type: "decision", label: "이벤트\n감지?" },
      { id: "obj",     type: "decision", label: "장애물\n판단" },
      { id: "avoid",   type: "process",  risk: "safe",  label: "우회함" },
      { id: "waitobj", type: "process",  risk: "watch", label: "사라질 때까지\nor 7초간 대기" },
      { id: "notify",  type: "process",  risk: "watch", label: "관리자에게 알림" },
      { id: "track",   type: "process",  risk: "check", label: "의심자 트래킹" },
      { id: "susp",    type: "decision", label: "의심?" },
      { id: "police",  type: "process",  risk: "danger",label: "경찰 신고/알림\nGen.G 출동" }
    ],
    edges: [
      { from: "s",      to: "wait" },
      { from: "wait",   to: "patrol" },
      { from: "patrol", to: "ev" },
      { from: "ev",     to: "obj",    label: "장애물 감지" },
      { from: "ev",     to: "track",  label: "도난" },
      { from: "ev",     to: "notify", label: "이상소리 감지" },
      { from: "obj",    to: "avoid",  label: "정적" },
      { from: "obj",    to: "waitobj",label: "동적" },
      { from: "avoid",  to: "patrol" },
      { from: "waitobj",to: "avoid" },
      { from: "notify", to: "patrol" },
      { from: "track",  to: "susp",   label: "경비원 호출" },
      { from: "susp",   to: "patrol", label: "의심 해소" },
      { from: "susp",   to: "police", label: "의심 유지" },
      { from: "police", to: "patrol" }
    ],
    tour: ["s", "wait", "patrol", "ev", "track", "susp", "police"]
  },

  {
    id: "s5",
    title: "#5 배터리 부족",
    summary: "순찰 대기 → 배터리 30% 이하 판단 → 출동요청 시 Gen.G 교대·충전소 이동 / 순찰명령 시 순찰 지속",
    nodes: [
      { id: "s",      type: "start",    label: "Start" },
      { id: "wait",   type: "process",  risk: "safe",  label: "순찰 대기" },
      { id: "charge", type: "process",  risk: "safe",  label: "충전소 이동" },
      { id: "bat",    type: "decision", label: "배터리\n30% 이하?" },
      { id: "gx",     type: "process",  risk: "check", label: "Gen.G 교대" },
      { id: "patrol", type: "process",  risk: "safe",  label: "순찰 중" }
    ],
    edges: [
      { from: "s",      to: "wait" },
      { from: "charge", to: "wait",   label: "완충시" },
      { from: "wait",   to: "bat" },
      { from: "bat",    to: "patrol", label: "순찰명령" },
      { from: "bat",    to: "gx",     label: "출동요청" },
      { from: "gx",     to: "charge" },
      { from: "patrol", to: "bat" }
    ],
    tour: ["s", "wait", "bat", "gx", "charge", "wait"]
  }
];

// 위험 등급 범례 (앱 색상 레이어 · 심각도 기준).
window.RISK_LEGEND = [
  { key: "safe",   tag: "SAFE",     ko: "정상",      desc: "이상 없음 · 순찰/대기" },
  { key: "watch",  tag: "WATCH",    ko: "주의 관찰", desc: "이상 징후 최초 감지 · 재촬영·재분석" },
  { key: "check",  tag: "CHECK",    ko: "현장 확인", desc: "두 번째 확인 · Gen.G 현장 출동" },
  { key: "danger", tag: "DANGER",   ko: "위험 확인", desc: "위험 가능성 높음 · 신고·차단벽 요청" },
  { key: "evac",   tag: "EVACUATE", ko: "긴급 대피", desc: "즉시 대피 · 위험 구역 설정" }
];
