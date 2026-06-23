/*
 * sensor-dataflow.js — deck 4: 센서별 데이터 흐름 (전환 라인업 반영).
 * 출처: docs/ref/CONTRACT.md §4 (정본 v18, 2026-06-16) + DECISION-LOG 2026-06-16.
 * 전환: 조도(LDR)·불꽃(Flame) 제거 → 온도센서·레이저 송신 모듈·워터펌프 추가. 상태는 badge 로 표기.
 */
registerDeck({
  id: "sensor-dataflow",
  title: "③ 로봇과 센서",
  theme: "green",
  slides: [
    {
      type: "cover",
      title: "센서 신호는 어떻게 화면까지 오나?",
      subtitle: "Arduino에 꽂은 센서 하나의 신호가 ROS 메시지로 바뀌어 Unity 화면에 카드로 나타나기까지의 여정.",
      tags: ["Arduino Uno", "pyserial", "/security/event", "정본 v18"]
    },
    {
      type: "cards",
      title: "센서 라인업 - 현재와 바뀔 예정",
      lead: "정본 v18(2026-06-16): 조도·불꽃 빠짐 → 온도·레이저·워터펌프 들어옴. 뱃지는 지금 상태를 보여줍니다.",
      cols: 3,
      cards: [
        { title: "PIR (HC-SR501)", body: "사람의 움직임을 감지해서 침입을 알림. 핀 D2.", badge: { text: "현재", kind: "ok" } },
        { title: "소형 사운드 (KY-038)", body: "큰 소리를 감지해서 이상 알람 울림. 핀 D3.", badge: { text: "현재", kind: "ok" } },
        { title: "레이저 송신 모듈", body: "PIR이 감지할 때 함께 켜져서 표시. 핀 D8.", badge: { text: "이미 달음", kind: "accent" } },
        { title: "온도 센서 모듈", body: "화재나 과열을 감지하는 보조 역할. 핀 A0.", badge: { text: "현재", kind: "ok" } },
        { title: "워터 펌프 (릴레이)", body: "화재가 감지되면 물을 분사. 액추에이터 핀 D5.", badge: { text: "새로 달 예정", kind: "info" } },
        { title: "조도 (LDR) · 불꽃(Flame)", body: "밤시간/불꽃 감지. 정본 v18부터 사용 중단.", badge: { text: "없앨 예정", kind: "bad" } }
      ]
    },
    {
      type: "diagram",
      title: "모든 센서가 가는 같은 길 (↓ 키로 따라가기)",
      lead: "어떤 센서든 같은 경로로 신호가 오갑니다.",
      nodes: [
        { label: "센서 4종", sub: "PIR · 사운드 · 온도 · 레이저" },
        { label: "미니 브레드보드", sub: "전기 공급(5V, GND 공통선)" },
        { label: "Arduino Uno", sub: "핀의 신호를 읽어서 시리얼로 보냄" },
        { label: "USB-B → RPi", sub: "통신속도 115200" },
        { label: "sensor_bridge", sub: "시리얼 데이터 해석 프로그램" },
        { label: "/security/event", sub: "해석된 이벤트를 메시지로 발행" },
        { label: "Unity", sub: "지도 마커 표시 · 센서 카드 업데이트" }
      ],
      note: "전원은 **OpenCR 5V → 점퍼 2줄 → Arduino 5V** (별도 배터리 없음)."
    },
    {
      type: "flow",
      title: "Arduino 한 줄이 화면의 이벤트가 되기까지 (↓)",
      lead: "Arduino가 보내는 글자들이 어떻게 변환되는지 보기.",
      chains: [
        { label: "PIR 감지", steps: [
          { k: "arduino", v: "D2 HIGH" },
          { k: "serial", v: "`EVT,pir,3,<ts>`" },
          { k: "bridge", v: "시리얼 해석 → 로봇 ID 추가" },
          { k: "topic", v: "`/security/event` (위험도 3)" },
          { k: "unity", v: "지도에 마커 표시 + PIR 카드 빨강" }
        ]},
        { label: "사운드", steps: [
          { k: "arduino", v: "D3 HIGH" },
          { k: "serial", v: "`EVT,noise,2,<ts>`" },
          { k: "bridge", v: "소음 이벤트로 해석" },
          { k: "topic", v: "`/security/event`" },
          { k: "unity", v: "이상 소음 알림" }
        ]},
        { label: "온도", steps: [
          { k: "arduino", v: "A0 수치 높음" },
          { k: "serial", v: "`EVT,fire,3,<ts>`" },
          { k: "bridge", v: "화재 이벤트 → 워터펌프 시작" },
          { k: "topic", v: "`/security/event` + 액추에이터" },
          { k: "unity", v: "화재 경보 화면" }
        ]}
      ]
    },
    {
      type: "table",
      title: "핀맵 (정본 v18, 현재 상태)",
      lead: "센서가 Arduino의 어디에 꽂혀 있는지, 통신속도는 115200으로 고정.",
      columns: ["센서 / 모듈", "Arduino 핀", "시리얼 이름", "상태"],
      rows: [
        ["PIR (HC-SR501)", "D2", "`pir`", { v: "지금 사용", kind: "ok" }],
        ["소리 (KY-038)", "D3", "`noise`", { v: "지금 사용", kind: "ok" }],
        ["레이저 송신 모듈", "D8", "(PIR과 함께)", { v: "이미 달음", kind: "accent" }],
        ["온도 센서 모듈", "A0", "`fire`", { v: "지금 사용", kind: "ok" }],
        ["워터 펌프 (릴레이)", "D5", "액추에이터", { v: "곧 달 예정", kind: "info" }],
        ["조도 (LDR)", "~~A0~~", "~~dark~~", { v: "없앰", kind: "bad" }],
        ["불꽃 (Flame)", "~~D4~~", "~~fire~~", { v: "없앰", kind: "bad" }]
      ]
    },
    {
      type: "image",
      title: "실제 결선 모습",
      lead: "Arduino 하나에 센서 네 종류를 꽂은 실물입니다.",
      src: "img/sensor-wiring.png",
      label: "센서 결선 사진",
      caption: "PIR · 레이저 · 사운드 · 온도 — Arduino Uno에 함께 연결"
    },
    {
      type: "bullets",
      title: "센서가 바뀌면 Unity 화면도 바뀐다",
      lead: "센서를 빼고 더하면 관제 화면의 센서 카드도 손을 봐야 합니다. (다음 과제)",
      items: [
        { h: "없앤 것", d: "LuxSubscriber.cs 이미 삭제 — 남은 건 Unity 조도 카드 제거(dark 이벤트 더 이상 안 옴)." },
        { h: "추가할 것", d: "온도 카드 + SensorRegistry에 온도 항목 추가, 화재 때 워터펌프 표시." },
        { h: "레이저 표시", d: "PIR이 감지할 때 레이저가 켜지는 모습을 UI에 보조 표시로." },
        { h: "문서 규칙", d: "센서 변경할 때는 CONTRACT.md §4 + DECISION-LOG를 함께 갱신하고 PR로 요청." }
      ]
    }
  ]
});
