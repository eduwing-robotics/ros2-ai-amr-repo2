/*
 * comms-workflow.js — deck 1: 로봇 ↔ Unity 통신 워크플로우.
 * 출처: docs/ref/ARCHITECTURE.md, docs/ref/CONTRACT.md(토픽 표 §1), unity/ControlRoom/Assets/Scripts/Ros/*.
 * 슬롯 교체로 통신 주제를 갱신. (docs/presentation/CLAUDE.md 참조)
 */
registerDeck({
  id: "comms-workflow",
  title: "② 시스템 구조 — 데이터가 화면까지",
  theme: "cyan",
  slides: [
    {
      type: "cover",
      title: "로봇은 어떻게 Unity 화면에 나타날까?",
      subtitle: "센서·카메라·위치 데이터가 로봇에서 출발해 관제 UI에 그려지기까지의 한 흐름.",
      tags: ["ROS2", "ROS-TCP-Endpoint", "Unity ROS-TCP-Connector", "Domain ID 210"]
    },
    {
      type: "bullets",
      title: "큰 그림 — 3단계로 끝",
      lead: "어려워 보여도 데이터는 항상 같은 길을 지나요.",
      items: [
        { h: "1. 로봇이 내보낸다", d: "로봇이 자신의 위치, 라이다, 카메라, 배터리, 센서값을 ROS2 토픽으로 내보낸다." },
        { h: "2. 가운데 다리가 받는다", d: "ROS-TCP-Endpoint라는 중간 프로그램이 TCP(포트 10000)로 메시지를 Unity에 전달한다." },
        { h: "3. Unity가 받아서 그린다", d: "Unity의 Subscriber가 토픽을 받아 지도, 카메라, 센서 카드 같은 화면에 표시한다." }
      ]
    },
    {
      type: "diagram",
      title: "전체 데이터 경로 (↓ 키로 한 칸씩 따라가기)",
      lead: "로봇 하드웨어에서 관제 화면까지. 화살표를 따라가면 데이터 흐름이 보입니다.",
      nodes: [
        { label: "로봇 HW", sub: "TurtleBot3 · LiDAR · 카메라 · OpenCR · Arduino" },
        { label: "ROS2 노드", sub: "bringup · cartographer · sensor_bridge" },
        { label: "ROS-TCP-Endpoint", sub: "TCP :10000 다리" },
        { label: "ROS-TCP-Connector", sub: "Unity 측 수신 라이브러리" },
        { label: "Subscriber", sub: "토픽별 C# 구독자" },
        { label: "UI View", sub: "지도·카메라·센서 카드" }
      ],
      note: "같은 네트워크에서 통신하려면 모든 노드가 같은 **Domain ID(210)** 와 같은 **RMW** 를 써야 합니다."
    },
    {
      type: "table",
      title: "주요 토픽 계약 (CONTRACT.md §1)",
      lead: "Unity가 구독하는 핵심 토픽. 토픽 이름이 조금만 틀려도 양쪽 모두 깨지므로 이렇게 계약서처럼 정해두었습니다.",
      columns: ["Topic", "메시지 타입", "Hz", "Unity 처리"],
      rows: [
        [{ v: "`/tb3_1/pose`", kind: "accent" }, "PoseStamped", "10", "로봇 위치 마커"],
        [{ v: "`/map`", kind: "accent" }, "OccupancyGrid", "1", "2D 지도 배경"],
        [{ v: "`/tf`", kind: "accent" }, "TFMessage", "30+", "좌표계 → pose 계산"],
        [{ v: "`/tb3_2/camera/image_raw`", kind: "accent" }, "Image", "15", "카메라 라이브 패널"],
        [{ v: "`/tb3_1/battery_state`", kind: "accent" }, "BatteryState", "1", "배터리 % 표시"],
        [{ v: "`/security/event`", kind: "warn" }, "SecurityEvent", "단발", "이벤트 마커·센서 카드"],
        [{ v: "`/goal_pose`", kind: "ok" }, "PoseStamped", "단발", "Unity→로봇 출동 명령"]
      ]
    },
    {
      type: "flow",
      title: "예시로 보는 구독 흐름 (↓)",
      lead: "토픽에서 메시지를 받아 Unity의 Subscriber가 화면에 표시하는 과정입니다.",
      chains: [
        { label: "카메라", steps: [
          { k: "topic", v: "`/tb3_2/camera/image_raw`" },
          { k: "msg", v: "Image / CompressedImage" },
          { k: "subscriber", v: "CameraStreamSubscriber.cs" },
          { k: "view", v: "카메라 라이브 패널(RawImage)" }
        ]},
        { label: "배터리", steps: [
          { k: "topic", v: "`/tb3_1/battery_state`" },
          { k: "msg", v: "BatteryState (전압)" },
          { k: "subscriber", v: "BatterySubscriber.cs" },
          { k: "view", v: "상단바 배터리 %" }
        ]},
        { label: "위치", steps: [
          { k: "topic", v: "`/tf` + `/pose`" },
          { k: "msg", v: "TFMessage" },
          { k: "subscriber", v: "RobotPoseSubscriber.cs" },
          { k: "view", v: "지도 로봇 마커" }
        ]}
      ]
    },
    {
      type: "cards",
      title: "Unity 구독자/발행자 모음",
      lead: "unity/ControlRoom/Assets/Scripts/Ros/ 폴더. 각 토픽마다 하나의 스크립트가 담당합니다.",
      cols: 3,
      cards: [
        { title: "RobotPoseSubscriber", body: "/tf를 받아서 지도 기준 로봇 위치 계산", sub: "→ 지도에 표시" },
        { title: "MapSubscriber", body: "/map을 이미지로 변환", sub: "→ 2D 지도 배경" },
        { title: "CameraStreamSubscriber", body: "카메라 이미지를 JPEG로 디코딩", sub: "→ 카메라 화면" },
        { title: "BatterySubscriber", body: "배터리 전압을 %로 계산", sub: "→ 배터리 표시" },
        { title: "PirSubscriber", body: "PIR 센서 신호를 감지/정상으로 판정", sub: "→ 센서 카드 색 바뀜" },
        { title: "SoundSubscriber", body: "소음 swing 값을 받아 임계 초과 표시", sub: "→ 센서 카드" },
        { title: "TemperatureSubscriber", body: "온도 raw 값을 받아 표시(NTC, 1Hz)", sub: "→ 센서 카드" },
        { title: "LaserSubscriber", body: "레이저 송신부 상태(PIR 종속). 현재 미결선", sub: "→ 센서 카드(비활성)" },
        { title: "DispatchPublisher", body: "지도에서 우클릭하면 /goal_pose 발행", sub: "→ 로봇이 출동" }
      ]
    },
    {
      type: "diagram",
      title: "반대 방향 — Unity가 명령을 보낸다 (↓)",
      lead: "한쪽 방향만 아니라, 관제자가 지도를 우클릭하면 로봇에게 출동 명령이 날아갑니다.",
      nodes: [
        { label: "지도 우클릭", sub: "출동 메뉴 선택" },
        { label: "DispatchPublisher", sub: "Unity → ROS" },
        { label: "/goal_pose", sub: "PoseStamped 목표 좌표" },
        { label: "Nav2", sub: "경로 생성·주행" },
        { label: "로봇 이동", sub: "현장으로 출동" }
      ]
    },
    {
      type: "bullets",
      title: "왜 환경을 맞춰야 할까",
      lead: "통신이 안 될 때 원인의 90%가 이 세 가지 때문입니다.",
      items: [
        { h: "Domain ID = 210", d: "숫자가 다르면 같은 와이파이라도 로봇과 Unity가 서로를 못 본다." },
        { h: "RMW = rmw_fastrtps_cpp", d: "DDS 구현이 다르면 로봇을 찾는(discovery) 단계부터 실패한다." },
        { h: "발견 모드 = multicast(SUBNET)", d: "Discovery Server를 섞어 쓰면 안 된다. 한쪽만 달라도 끊긴다." }
      ]
    }
  ]
});
