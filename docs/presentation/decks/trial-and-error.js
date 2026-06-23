/*
 * trial-and-error.js — deck 5: 시행착오와 배운 점 (발표용).
 * 출처: Confluence SCRUM 회의록 디제스트(2026.06.02~06.18) — 개발 중 실패·막힘·방향전환 9건.
 * 역할: "처음부터 잘 된 건 없다" 를 솔직하게. 시도 → 막힘 → 해결 구조로.
 * 이미지: img/trial-slam.png, img/trial-camera.png (없으면 점선 placeholder).
 */
registerDeck({
  id: "trial-error",
  title: "⑤ 시행착오와 배운 점",
  theme: "amber",
  slides: [
    {
      type: "cover",
      title: "쉽지 않았다 — 우리가 부딪힌 벽들",
      subtitle: "처음부터 잘 된 건 거의 없습니다. 막히고, 고치고, 방향을 바꾼 기록입니다.",
      tags: ["개발 일지", "회의록 정리", "2026년 6월"]
    },
    {
      type: "cards",
      title: "연결과 지도에서 막힌 것",
      lead: "로봇을 움직이기도 전에 통신과 지도부터 애를 먹였습니다.",
      cols: 3,
      cards: [
        { title: "와이파이가 자꾸 끊김", body: "무선으로 로봇에 접속했더니 배터리가 낮을 때 끊기고 신호도 불안정.", sub: "해결: 맥과 로봇을 직접 선으로 연결해 우회", badge: { text: "통신", kind: "warn" } },
        { title: "지도가 깨짐", body: "라이다로 지도를 그리는데, 로봇이 제자리에서 돌면 지도가 자주 망가졌습니다.", sub: "해결: 돌지 말고 늘 앞으로 가며 스캔", badge: { text: "SLAM", kind: "warn" } },
        { title: "주행 값 맞추기", body: "자동 주행 값을 잘못 잡으면 길을 못 찾거나 멀리 돌아갔습니다.", sub: "해결: 맵이 작아 DWB 방식 선택 + 값 다시 조정", badge: { text: "Nav2", kind: "warn" } }
      ]
    },
    {
      type: "cards",
      title: "카메라와 인식에서 막힌 것",
      lead: "보는 것도 생각보다 까다로웠습니다.",
      cols: 3,
      cards: [
        { title: "영상이 뚝뚝 끊김", body: "RealSense 고해상도 영상은 데이터가 커서 화면이 끊겼습니다.", sub: "해결: 해상도 424×240 · 15fps로 낮춰 부드럽게", badge: { text: "카메라", kind: "info" } },
        { title: "학습 사진 부족", body: "찍은 사진으로 바로 물체 인식을 학습했더니, 각도·조명이 적어 잘 못 맞혔습니다.", sub: "해결: 여러 각도로 300장 넘게 다시 모으는 중", badge: { text: "YOLO", kind: "info" } },
        { title: "좌표가 안 맞음", body: "화면 속 로봇 위치가 실제와 어긋났습니다.", sub: "해결: 출발점과 지도 원점을 손으로 맞춤", badge: { text: "디지털 트윈", kind: "info" } }
      ]
    },
    {
      type: "image",
      title: "이미지 인식(YOLO) — 지금 학습 중",
      lead: "직접 모은 데이터로 화재를 탐지하는 중. 신뢰도 0.26~0.35로 아직 초기라, 각도·조명을 늘려 데이터를 더 모으고 있습니다.",
      src: "img/yolo-fire-training.png",
      label: "YOLO 화재 탐지 학습 화면",
      caption: "T1 RealSense 라이브 — `FIRE` 박스가 잡히기 시작(신뢰도 낮음 = 학습 진행 중)"
    },
    {
      type: "cards",
      title: "욕심을 줄인 결정들",
      lead: "다 하려다 일정이 막힐 것 같아, 무거운 건 과감히 뺐습니다.",
      cols: 3,
      cards: [
        { title: "자동 충전 포기", body: "충전독에 스스로 도킹하려니 접점 정밀도와 복잡도가 컸습니다.", sub: "결정: ArUco 마커로 주차까지만, 충전은 사람이 연결", badge: { text: "범위 조정", kind: "bad" } },
        { title: "무선 충전 접음", body: "무선 충전을 알아봤지만 배터리 호환·회로·일정이 안 맞았습니다.", sub: "결정: 그냥 유선 충전으로", badge: { text: "범위 조정", kind: "bad" } },
        { title: "ROS2 재설치", body: "젠지 로봇의 ROS2가 지워지는 사고가 있었습니다.", sub: "해결: 다시 설치하고 설정 복구", badge: { text: "환경", kind: "bad" } }
      ]
    },
    {
      type: "image",
      title: "디버깅의 흔적",
      lead: "막힌 순간을 사진으로 남겼습니다.",
      cols: 2,
      images: [
        { src: "img/trial-slam.png", label: "SLAM 지도 사진", caption: "깨진 지도 / 다시 그린 지도" },
        { src: "img/trial-camera.png", label: "디버깅 화면", caption: "Nav2·SLAM 디버깅 (RViz + 터미널 로그)" }
      ]
    },
    {
      type: "bullets",
      title: "그래서 배운 것",
      lead: "고생 끝에 남은 네 가지.",
      items: [
        { h: "작게 시작하기", d: "완벽한 자동화보다, 되는 것부터 확인하고 늘렸습니다." },
        { h: "직접 해보기", d: "문서보다 실제로 돌려본 결과가 늘 더 정확했습니다." },
        { h: "욕심 줄이기", d: "자동 충전처럼 무거운 건 과감히 범위에서 뺐습니다." },
        { h: "기록 남기기", d: "막힌 것과 해결을 회의록에 적어두니 다음이 빨랐습니다." }
      ]
    }
  ]
});
