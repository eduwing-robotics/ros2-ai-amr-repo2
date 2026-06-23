/*
 * db-schema.js — deck 5: 데이터베이스 구조와 저장 흐름 (발표 슬라이드).
 * 출처: docs/ref/SCHEMA.md(정본) + docs/evidence/2026-06-18-unity-supabase-direct-write.md
 *       + DECISION-LOG.md의 2026-06-18 항목(Unity에서 Supabase로 직접 데이터 쓰기).
 * 적용상태(2026-06-18): session_meta, events, dispatches, camera_captures, pose_logs는 완료.
 *       logs와 일부 익명 키 권한 설정은 데이터베이스 복구 후 적용. 뱃지로 상태를 표시합니다.
 */
registerDeck({
  id: "db-schema",
  title: "④ 관제 화면과 데이터",
  theme: "violet",
  slides: [
    {
      type: "cover",
      title: "우리 로봇 데이터는 어디에 모이나",
      subtitle: "센서가 감지한 이벤트, 로봇이 움직인 위치, 출동 명령, 카메라 확인 결과를 클라우드(Supabase의 Postgres)에 저장했다가 발표 성과로 정리합니다.",
      tags: ["Supabase, Postgres(클라우드 데이터베이스)", "도쿄 서버 (ap-northeast-1)", "직접 저장(Unity에서 HTTP로)", "익명 키 + 행 단위 보안"]
    },
    {
      type: "image",
      title: "이 화면의 정보가 그대로 저장됩니다",
      lead: "관제 화면에 보이는 로봇 위치·로그·출동이 곧 데이터베이스 한 줄입니다.",
      cols: 2,
      images: [
        { src: "img/control-room.png", label: "관제 화면 스크린샷", caption: "Unity 관제 화면" },
        { src: "img/live-map.png", label: "지도 스크린샷", caption: "SLAM 지도 + 로봇 위치 마커" }
      ]
    },
    {
      type: "cards",
      title: "한눈에 보기 — 6개 테이블 저장 현황",
      lead: "뱃지는 실제 데이터베이스 적용 상태입니다. ✅는 이미 적용, ⏳는 데이터베이스 복구 후 진행할 예정입니다.",
      cols: 3,
      cards: [
        { title: "session_meta", body: "시연 1회 정보. 모든 기록의 부모.", sub: "scenario · started_at", badge: { text: "적용", kind: "ok" } },
        { title: "events", body: "센서가 감지한 이벤트(사람 침입, 소음, 온도, 화재).", sub: "robot_id · x,y,θ · severity", badge: { text: "적용", kind: "ok" } },
        { title: "dispatches", body: "로봇 출동 명령과 도착 시간 기록.", sub: "target_x,y · response_time", badge: { text: "적용", kind: "ok" } },
        { title: "camera_captures", body: "라즈베리파이 카메라로 확인한 결과(맞음/틀림).", sub: "result · ai_label", badge: { text: "적용", kind: "ok" } },
        { title: "pose_logs", body: "로봇이 이동한 위치 기록(초당 2회 저장).", sub: "x,y,θ · nav_mode · 2Hz", badge: { text: "적용", kind: "ok" } },
        { title: "logs", body: "관제 화면의 로그 라인(화면 내용과 데이터베이스 일치 확인용).", sub: "level · category · message", badge: { text: "복구 후 적용", kind: "warn" } }
      ]
    },
    {
      type: "filetree",
      title: "테이블 관계도 — 부모와 자식 연결",
      lead: "한 시연 아래 모든 기록이 달려있습니다. 센서 이벤트 → 출동 → 카메라 확인으로 연결되고, 위치와 로그는 시연 바로 아래 붙습니다.",
      tree: [
        { name: "session_meta  (시연 1회)", desc: "session_id(고유번호) — 모든 기록의 부모", open: true, children: [
          { name: "events  (센서 감지)", desc: "session_id 연결 · 한 시연에 여러 개", open: true, children: [
            { name: "dispatches  (로봇 출동)", desc: "event_id 연결 · 이벤트마다 0개 또는 1개 (손으로 명령하면 이벤트 없음)", open: true, children: [
              { name: "camera_captures  (카메라 확인)", desc: "dispatch_id 연결 · 출동마다 0개 또는 1개" }
            ]}
          ]},
          { name: "pose_logs  (위치 기록)", desc: "session_id 연결 · 초당 2회 저장" },
          { name: "logs  (화면 로그)", desc: "session_id 연결 · 관제 화면 라인" }
        ]}
      ]
    },
    {
      type: "table",
      title: "중요한 컬럼 — 위치 추적과 화면 기록 중심",
      lead: "발표의 핵심 두 가지: 로봇이 움직인 경로(pose_logs) + 화면 로그와 데이터베이스 일치 확인(logs). 좌표는 미터 단위, 각도는 라디안입니다.",
      columns: ["테이블", "컬럼명", "데이터 종류", "용도", "상태"],
      rows: [
        ["pose_logs", "x, y, theta", "소수점(높은 정밀도)", "맵 위 로봇 위치와 방향 표시", { v: "적용", kind: "ok" }],
        ["pose_logs", "nav_mode", "텍스트", "순찰 중인지 출동 중인지 구분", { v: "적용", kind: "ok" }],
        ["dispatches", "target_x, target_y", "소수점(높은 정밀도)", "맵 클릭으로 지정한 좌표", { v: "적용", kind: "ok" }],
        ["dispatches", "response_time", "숫자(초 단위)", "출동 응답시간(성과 지표)", { v: "적용", kind: "ok" }],
        ["logs", "level / category", "텍스트", "정보/경고/오류 등 로그 등급과 분류", { v: "대기", kind: "warn" }],
        ["logs", "message", "텍스트", "화면에 보인 로그 내용 그대로", { v: "대기", kind: "warn" }]
      ]
    },
    {
      type: "flow",
      title: "데이터 저장 흐름 — \"직접 저장\" 방식 (아래 화살표로 따라가기)",
      lead: "Unity가 HTTP로 데이터베이스에 직접 저장합니다. 로봇 명령(ROS)과 기록(데이터베이스)이 별개로 움직입니다.",
      chains: [
        { label: "맵 클릭 출동", steps: [
          { k: "unity", v: "맵에서 우클릭 → 좌표(x,y) 선택" },
          { k: "ros", v: "출동 메시지 발행 → 로봇 이동 시작 (`/goal_pose`)" },
          { k: "db", v: "출동 정보를 데이터베이스 저장 (dispatches 테이블)" },
          { k: "postgrest", v: "익명 키로 권한 확인 → 저장 완료" }
        ]},
        { label: "위치 기록 저장", steps: [
          { k: "ros", v: "로봇의 현재 위치 정보 수신 (x,y,yaw)" },
          { k: "throttle", v: "초당 2회로 제한 · 최소 이동만 저장(너무 많이 쌓이는 걸 막기 위해)" },
          { k: "db", v: "위치를 데이터베이스에 저장 (pose_logs 테이블, 고유번호는 자동 생성)" },
          { k: "unity", v: "맵에 표시 + 이동 궤적 그리기" }
        ]},
        { label: "화면 로그", steps: [
          { k: "unity", v: "화면에 로그 한 줄 추가 (ControlRoomEvents.OnLogAdded 호출)" },
          { k: "db", v: "그 로그를 데이터베이스에 저장 (logs 테이블)" },
          { k: "verify", v: "검증: 화면의 로그 수 = 데이터베이스 로그 수" }
        ]}
      ]
    },
    {
      type: "cards",
      title: "설계 원칙 — 발표 중 끊김 0 + 안전",
      lead: "발표가 멈추지 않아야 하고, 중요한 키가 노출되면 안 됩니다.",
      cols: 2,
      cards: [
        { title: "비차단 저장", body: "모든 저장 요청을 대기줄에 넣고 바로 반환. 네트워크 지연이 화면 프레임을 막지 않으므로 발표가 끊기지 않습니다.", badge: { text: "끊김 방지", kind: "accent" } },
        { title: "오프라인 보호", body: "데이터베이스가 다운되거나 와이파이가 끊기면 디스크에 모아두었다가 복구되면 자동으로 순서대로 전송. 데이터 유실이 없습니다.", badge: { text: "데이터 유실 방지", kind: "ok" } },
        { title: "저장 빈도 조절", body: "위치는 초당 2회만 저장하고, 실제로 움직였을 때만 기록. 요청이 너무 많아지는 걸 막습니다.", badge: { text: "속도 제한", kind: "info" } },
        { title: "권한 분리 (행 단위 보안)", body: "모바일 앱은 공개 키로만 접근. 중요한 관리 키는 로봇 컴퓨터에만 설치. 테이블마다 누가 뭘 할 수 있는지 세세하게 제어합니다.", badge: { text: "관리 키 미반입", kind: "ok" } }
      ]
    },
    {
      type: "table",
      title: "발표용 성과 지표 — 한눈에 정리",
      lead: "데이터베이스 테이블들을 묶어 시나리오별 로봇 성능을 한 번에 계산합니다(테스트 값).",
      columns: ["시나리오", "감지 횟수", "평균 출동 시간", "카메라 확인 성공률"],
      rows: [
        ["침입 감지", "12회", { v: "4.2초", kind: "ok" }, { v: "92%", kind: "ok" }],
        ["소음 감지", "7회", { v: "3.8초", kind: "ok" }, { v: "86%", kind: "ok" }],
        ["화재 감지", "3회", { v: "5.1초", kind: "warn" }, { v: "100%", kind: "ok" }],
        ["야간 순찰", "21회", { v: "—", kind: "" }, { v: "—", kind: "" }]
      ]
    },
    {
      type: "progress",
      title: "데이터베이스 구축 진행률",
      lead: "데이터베이스 구조를 설계하고 5개 테이블을 적용했습니다. 로그 테이블과 일부 권한 설정은 데이터베이스 복구 후 진행하기로 했습니다.",
      items: [
        { label: "데이터베이스 구조 설계 (정본: docs/ref/SCHEMA.md)", done: 6, total: 6, status: "완료" },
        { label: "테이블 5개 적용 (시연/이벤트/출동/카메라/위치)", done: 5, total: 6, status: "진행", sub: "로그 1개 남음" },
        { label: "Unity에서 직접 저장하는 코드 작성 및 빌드", done: 3, total: 3, status: "완료", sub: "클라이언트·서비스·검증" },
        { label: "로그 테이블 + 익명 키 권한 설정", done: 0, total: 1, status: "대기", sub: "Supabase 데이터베이스 복구 후" },
        { label: "발표 환경에서 화면=데이터베이스 일치 확인", done: 0, total: 1, status: "대기", sub: "DbVerifyConsole.Verify()" }
      ]
    }
  ]
});
