/*
 * db-relationship-map.js — deck: DB·Unity·센서·터틀봇 관계 지도.
 * 출처: docs/ref/SCHEMA.md + docs/ref/CONTRACT.md + docs/ref/ARCHITECTURE.md
 *       + docs/evidence/2026-06-18-unity-supabase-direct-write.md.
 * 목적: 현재 적용 DB와 Unity/센서/터틀봇 데이터 관계를 발표용 키워드 HTML로 시각화한다.
 */
registerDeck({
  id: "db-relationship-map",
  title: "⑤ DB 관계 지도",
  theme: "green",
  slides: [
    {
      type: "cover",
      title: "DB · Unity · 센서 · 터틀봇 관계",
      subtitle: "센서와 로봇이 만든 신호가 ROS2와 Unity를 지나 Supabase 테이블로 남고, 다시 관제 화면과 발표 지표로 읽히는 구조입니다.",
      tags: ["현재 적용 중심", "키워드 발표", "Supabase", "ROS2 Domain 210", "Unity ControlRoom"]
    },
    {
      type: "diagram",
      title: "전체 흐름 — 감지에서 기록까지",
      nodes: [
        { label: "센서 4종", sub: "PIR · Sound · Temp · Laser" },
        { label: "tb3_2 젠지", sub: "Arduino USB · Pi Camera · 센서 브릿지" },
        { label: "ROS2", sub: "/sensors/* · /tf · /goal_pose" },
        { label: "Unity ControlRoom", sub: "맵 · 마커 · 로그 · 출동" },
        { label: "Supabase DB", sub: "events · dispatches · pose_logs · logs" },
        { label: "발표 지표", sub: "감지 수 · 출동 시간 · 확인 결과" }
      ],
      note: "아래 화살표로 단계 강조. 센서 이벤트는 로봇 PC 브릿지가 DB에 직접 저장하고, Unity는 화면 로그·수동 출동·pose 기록을 anon/RLS 경로로 저장합니다."
    },
    {
      type: "cards",
      title: "두 터틀봇 역할",
      lead: "로봇별 데이터의 성격이 다릅니다. T1은 비전/위치, Genji는 센서/확인 흐름이 중심입니다.",
      cols: 2,
      cards: [
        { title: "tb3_1 · 티원", body: "비전 중심 순찰 로봇. D435 RGB-D, LiDAR, odom, Nav2 경로를 Unity와 DB 기록에 연결합니다.", sub: "D435 · scan · odom · pose_logs", badge: { text: "Vision", kind: "info" } },
        { title: "tb3_2 · 젠지", body: "센서 중심 출동/확인 로봇. Arduino 센서 4종과 Pi Camera가 events와 camera_captures의 주 입력입니다.", sub: "PIR · sound · temp · laser · PiCam", badge: { text: "Sensor", kind: "ok" } }
      ]
    },
    {
      type: "flow",
      title: "저장 경로 5개 — 무엇이 어느 테이블로 가나",
      lead: "핵심은 원본 신호를 작은 테이블 단위로 나눠 저장하는 것입니다.",
      chains: [
        { label: "센서", steps: [
          { k: "arduino", v: "PIR / Sound / Temp / Laser" },
          { k: "bridge", v: "arduino_bridge_quad.py" },
          { k: "db", v: "`events`" }
        ]},
        { label: "출동", steps: [
          { k: "unity", v: "맵 우클릭 / 이벤트 대응" },
          { k: "ros", v: "`/<robotId>/goal_pose`" },
          { k: "db", v: "`dispatches`" }
        ]},
        { label: "위치", steps: [
          { k: "ros", v: "/tf · /odom · pose" },
          { k: "unity", v: "RobotPoseSubscriber" },
          { k: "db", v: "`pose_logs`" }
        ]},
        { label: "카메라", steps: [
          { k: "robot", v: "Pi Camera / D435" },
          { k: "unity", v: "카메라 패널" },
          { k: "db", v: "`camera_captures`" }
        ]},
        { label: "화면", steps: [
          { k: "unity", v: "ControlRoom 로그 라인" },
          { k: "queue", v: "비차단 저장 큐" },
          { k: "db", v: "`logs`" }
        ]}
      ]
    },
    {
      type: "filetree",
      title: "현재 DB 관계 — 부모/자식 구조",
      lead: "한 시연(session_meta) 아래에 이벤트·출동·카메라·위치·화면 로그가 붙습니다.",
      tree: [
        { name: "session_meta", desc: "시연 1회 · 모든 기록의 부모", open: true, children: [
          { name: "events", desc: "센서 감지 · robot_id/x/y/theta/severity", open: true, children: [
            { name: "dispatches", desc: "출동 명령 · event_id nullable(수동 출동 허용)", open: true, children: [
              { name: "camera_captures", desc: "카메라 확인 · result/ai_label/image_path" }
            ]}
          ]},
          { name: "pose_logs", desc: "로봇 이동 좌표 · robot_id/x/y/theta/nav_mode" },
          { name: "logs", desc: "Unity 화면 로그 · level/category/message" }
        ]}
      ]
    },
    {
      type: "table",
      title: "테이블별 키워드",
      lead: "발표에서는 컬럼 전체보다 역할 키워드만 잡으면 됩니다.",
      columns: ["테이블", "역할", "주요 연결", "상태"],
      rows: [
        ["session_meta", "시연 회차", "session_id", { v: "현재", kind: "ok" }],
        ["events", "센서 감지", "session_id · robot_id · pose", { v: "현재", kind: "ok" }],
        ["dispatches", "출동 기록", "event_id · target_x/y · nav_mode", { v: "현재", kind: "ok" }],
        ["camera_captures", "확인 결과", "dispatch_id · image_path · result", { v: "현재", kind: "ok" }],
        ["pose_logs", "이동 좌표", "session_id · robot_id · x/y/theta", { v: "현재", kind: "ok" }],
        ["logs", "화면 로그", "session_id · category · message", { v: "현재", kind: "ok" }],
        ["media_artifacts", "원본 미디어 메타", "storage_path", { v: "예정", kind: "warn" }],
        ["protected_assets", "전시물/액자 등록", "asset_id · x/y · marker", { v: "예정", kind: "warn" }]
      ]
    },
    {
      type: "cards",
      title: "Unity와 DB의 관계",
      lead: "Unity는 로봇의 진실값을 만들지 않습니다. 관제와 기록, 제한된 쓰기만 담당합니다.",
      cols: 3,
      cards: [
        { title: "읽기", body: "pose_logs, events, dispatches, logs를 읽어 관제 화면과 검증 콘솔에 표시합니다.", sub: "SELECT · anon/RLS", badge: { text: "조회", kind: "info" } },
        { title: "쓰기", body: "맵 클릭 출동, 화면 로그, pose 샘플을 UnityWebRequest로 비차단 저장합니다.", sub: "INSERT · 큐 · 디스크 버퍼", badge: { text: "시연", kind: "ok" } },
        { title: "금지", body: "service_role 키는 Unity에 넣지 않습니다. 관리 키는 RobotPC/관리 환경에만 둡니다.", sub: "service_role 미반입", badge: { text: "보안", kind: "bad" } }
      ]
    },
    {
      type: "diagram",
      title: "읽기/쓰기 책임 경계",
      nodes: [
        { label: "RobotPC", sub: "센서 이벤트 · service/환경키" },
        { label: "ROS2", sub: "주행 진실값 · 토픽" },
        { label: "Unity", sub: "관제 · 제한 쓰기" },
        { label: "Supabase RLS", sub: "anon 정책 · 테이블별 허용" },
        { label: "DB", sub: "발표 근거 · KPI" }
      ],
      note: "주행 판단은 ROS/Nav2, 관제와 발표 증거는 Unity/DB가 담당합니다."
    },
    {
      type: "bullets",
      title: "발표용 한 줄 요약",
      lead: "이 다섯 문장만 잡으면 관계 설명이 끝납니다.",
      items: [
        { h: "DB는 증거 저장소", d: "시연 회차, 이벤트, 출동, 카메라, 위치, 화면 로그를 남깁니다." },
        { h: "ROS2는 실시간 진실값", d: "주행·센서·pose 토픽은 ROS2 Domain 210에서 흐릅니다." },
        { h: "Unity는 관제와 제한 쓰기", d: "화면 표시, 맵 클릭 출동, 로그/pose 저장을 담당합니다." },
        { h: "센서는 events로", d: "Arduino 브릿지가 PIR/sound/temp/laser를 이벤트 기록으로 바꿉니다." },
        { h: "원본 미디어/전시물은 다음 확장", d: "media_artifacts와 protected_assets는 발표 구조상 예정 레이어입니다." }
      ]
    }
  ]
});
