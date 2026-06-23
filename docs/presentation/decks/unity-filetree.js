/*
 * unity-filetree.js — deck 2: Unity 프로젝트(ControlRoom) 파일·폴더 구조 소개.
 * 출처: unity/ControlRoom/Assets/ 실제 트리(2026-06-17 확인) + docs/ref/tech/UNITY.md.
 */
registerDeck({
  id: "unity-filetree",
  title: "⑦ (부록) Unity 코드 구조",
  theme: "violet",
  slides: [
    {
      type: "cover",
      title: "Unity 관제실은 어떻게 구성돼 있나",
      subtitle: "unity/ControlRoom 프로젝트의 폴더·파일 지도. 어디를 열면 무엇이 나오는지 한눈에.",
      tags: ["UI Toolkit", "ROS-TCP-Connector", "Supabase", "C#"]
    },
    {
      type: "bullets",
      title: "먼저 알아둘 3가지",
      items: [
        { h: "위치", d: "unity/ControlRoom/ — 씬은 Scenes/ControlRoomMain.unity 하나." },
        { h: "화면은 UI Toolkit으로", d: "UXML로 배치, USS로 꾸민다. Assets/UI/ 가 정본." },
        { h: "코드는 일 별로", d: "통신, 상태, 화면, 지도 — 폴더가 달라. Scripts/ 안에 정리됨." }
      ]
    },
    {
      type: "filetree",
      title: "Assets 폴더 트리",
      lead: "▸ 를 눌러 펼치세요. 회의 중 특정 폴더에 메모를 달 수도 있어요(📌).",
      tree: [
        { name: "Assets/", open: true, children: [
          { name: "Scenes/", desc: "ControlRoomMain.unity — 관제 메인 씬" },
          { name: "UI/", desc: "UI Toolkit 화면 정본", open: true, children: [
            { name: "ControlRoomMain.uxml", desc: "최상위 레이아웃(상단바+3열)" },
            { name: "ControlRoomStyle.uss / ControlRoomTokens.uss", desc: "스타일 + 디자인 토큰" },
            { name: "Parts/", desc: "TopBar · LeftControlPanel · MapPanel · CameraAndLogPanel · RightStatusPanel" }
          ]},
          { name: "Scripts/", desc: "C# 프로그램 코드", open: true, children: [
            { name: "App/", desc: "시작·상태·알림 처리 (ControlRoomApp/State/Events)" },
            { name: "Data/", desc: "변하지 않는 모델(로봇, 센서 정보)" },
            { name: "UI/", desc: "화면 부품이 상태 따라 바뀌도록 연결" },
            { name: "Map/", desc: "2D 지도 그리기 + 마우스 우클릭 버튼" },
            { name: "Ros/", desc: "★ ROS 통신 중추 — 8가지 수신/발행" },
            { name: "Sensors/ · Features/", desc: "센서·기능 등록소" },
            { name: "Database/", desc: "Supabase로 위치 기록 저장/가져오기" },
            { name: "Simulation/", desc: "로봇 없을 때 테스트용 더미 데이터" },
            { name: "Design/", desc: "색·크기·아이콘 이름 모음" }
          ]},
          { name: "Editor/", desc: "에디터 자동화(씬 셋업, 카메라 패널 셋업)" },
          { name: "Art/IconsPng/", desc: "로봇·센서·타깃 아이콘" },
          { name: "Robots/", desc: "TurtleBot3 URDF 소스 + import prefab" },
          { name: "Resources/", desc: "런타임 설정 에셋(Feature/Map/Robot/Sensor/Situation)" },
          { name: "Tests/", desc: "EditMode/PlayMode 스모크 테스트" }
        ]}
      ]
    },
    {
      type: "cards",
      title: "Scripts 도메인 — 폴더가 곧 책임",
      lead: "한 폴더 = 한 가지 일. 어디를 고칠지 헷갈릴 때 이 표를 봅니다.",
      cols: 3,
      cards: [
        { title: "App", body: "실행 시작 + 지금 선택된 로봇·모드 기억 + 화면·통신·DB 연결.", sub: "ControlRoomApp/State/Events" },
        { title: "Ros", body: "ROS 메시지 받기/보내기. 이름은 TopicRegistry 한 곳에만.", sub: "수신기 7개 + 발행기" },
        { title: "UI", body: "화면 조각을 찾아서 상태값으로 그려준다.", sub: "TopBarView, MapPanelView …" },
        { title: "Map", body: "가운데 2D 지도, 로봇·이벤트 점, 클릭하면 출동 명령.", sub: "MapView + Actions/" },
        { title: "Data", body: "로봇·센서·목표 정보. 한 번 정해지면 바뀌지 않음.", sub: "RobotInfo, SensorInfo …" },
        { title: "Database", body: "Supabase에서 로봇 위치 기록 불러오고 저장.", sub: "SupabaseClient" }
      ]
    },
    {
      type: "filetree",
      title: "Scripts/Ros — 통신의 심장",
      lead: "토픽 1종 = 파일 1개. 새 센서가 생기면 여기에 Subscriber 하나가 늘어납니다.",
      tree: [
        { name: "Ros/", open: true, children: [
          { name: "TopicRegistry.cs", desc: "모든 메시지 이름이 한군데. 다른 곳에서 복사하지 말 것" },
          { name: "RobotPoseSubscriber.cs", desc: "로봇이 어디 있는지 받음" },
          { name: "MapSubscriber.cs", desc: "지도 이미지 받음" },
          { name: "CameraStreamSubscriber.cs", desc: "카메라 영상 받아서 화면에 띄움" },
          { name: "BatterySubscriber.cs", desc: "배터리 전압 받음" },
          { name: "PirSubscriber.cs", desc: "동작 감지기 신호 받음" },
          { name: "SoundSubscriber.cs", desc: "소음 swing 값 받음" },
          { name: "TemperatureSubscriber.cs", desc: "온도 raw 값 받음(NTC, 1Hz)" },
          { name: "LaserSubscriber.cs", desc: "레이저 송신부 상태(PIR 종속, 현재 미결선)" },
          { name: "DispatchPublisher.cs", desc: "지도에서 클릭하면 로봇에 명령 보냄" }
        ]}
      ]
    },
    {
      type: "cards",
      title: "화면 한 장 = UXML Part 5개",
      lead: "Assets/UI/Parts/ — 관제 화면은 이 5조각의 조합입니다.",
      cols: 3,
      cards: [
        { title: "TopBar", body: "로봇 고르기, 시간, 경보, 전원." },
        { title: "LeftControlPanel", body: "로봇 손으로 움직이기, 돌아다니기, 패턴 고르기." },
        { title: "MapPanel", body: "가운데 2D/3D 지도. 로봇·사건 표시." },
        { title: "CameraAndLogPanel", body: "카메라 영상. 사건 기록." },
        { title: "RightStatusPanel", body: "배터리, 센서 상태, 기능 켜고 끄기." }
      ]
    },
    {
      type: "bullets",
      title: "새 센서/기능을 추가하려면? (수정 순서)",
      lead: "예: 온도 센서를 새로 붙일 때 손대는 곳.",
      items: [
        { h: "1. TopicRegistry.cs", d: "이름을 한 곳에 등록해둔다." },
        { h: "2. Ros/○○Subscriber.cs", d: "ROS에서 값을 받는 코드를 만든다." },
        { h: "3. App/ControlRoomState + Events", d: "받은 값을 기억했다가 알림으로 퍼뜨린다." },
        { h: "4. UI/SensorCardListView + Sensors/SensorRegistry", d: "화면에 센서 상태 박스를 그린다." }
      ]
    }
  ]
});
