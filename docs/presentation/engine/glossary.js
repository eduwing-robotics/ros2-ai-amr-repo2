/*
 * glossary.js — 어려운 용어 → 쉬운 설명 사전 (hover 툴팁 소스).
 * 역할: deck 텍스트에 등장하는 키 용어를 엔진이 자동으로 .term 으로 감싸 툴팁을 띄운다.
 * 추가법: 아래 객체에 "용어": "설명" 한 줄 추가하면 모든 deck에 즉시 반영. 출처: docs/ref/CONTRACT.md, ARCHITECTURE.md.
 */
window.GLOSSARY = {
  "ROS-TCP-Endpoint": "ROS2 쪽에서 Unity와 TCP(포트 10000)로 메시지를 주고받게 해주는 다리 노드. 로봇 PC에서 실행.",
  "ROS-TCP-Connector": "Unity(C#) 쪽 라이브러리. ROS 토픽을 구독/발행해 게임 오브젝트에 연결한다.",
  "Subscriber": "특정 토픽을 '구독'해서 메시지가 도착할 때마다 콜백을 받는 객체.",
  "Publisher": "토픽으로 메시지를 '발행'하는 객체. Unity가 출동 명령을 보낼 때 사용.",
  "토픽": "ROS에서 데이터가 흐르는, 이름표가 붙은 통로. 예: /tb3_1/pose.",
  "OccupancyGrid": "SLAM이 만든 점유 격자 지도. 칸마다 빈공간(0)/벽(100)/모름(-1) 값을 가진다.",
  "DDS": "ROS2가 내부적으로 쓰는 통신 미들웨어(Data Distribution Service). 노드끼리 자동으로 서로를 찾는다.",
  "Domain ID": "같은 숫자를 가진 ROS 노드끼리만 통신한다. 본 프로젝트는 210으로 통일.",
  "CompressedImage": "JPEG 등으로 압축된 이미지 메시지. 카메라 영상의 대역폭을 줄인다.",
  "PoseStamped": "시간(헤더)+좌표계가 붙은 위치/자세 메시지.",
  "BatteryState": "배터리 전압·전류·잔량을 담는 표준 메시지. LiPo 전압으로 % 환산.",
  "Nav2": "ROS2 자율주행 내비게이션 스택. 목표 좌표를 받아 경로를 만들고 로봇을 주행시킨다.",
  "SLAM": "Simultaneous Localization And Mapping. 돌아다니며 지도를 만들고 동시에 자기 위치를 추정.",
  "cartographer": "구글의 SLAM 패키지. 라이다·odom·tf 로 /map 을 생성한다.",
  "UI Toolkit": "Unity의 최신 UI 시스템. 레이아웃은 UXML, 스타일은 USS 로 작성(웹의 HTML/CSS와 유사).",
  "UXML": "UI Toolkit 레이아웃 마크업 파일. HTML 과 비슷하다.",
  "USS": "UI Toolkit 스타일시트. CSS 와 비슷하다.",
  "MonoBehaviour": "Unity 스크립트의 기본 클래스. 씬의 게임 오브젝트에 붙어 매 프레임 동작.",
  "Texture2D": "Unity의 이미지 버퍼. 카메라/맵 픽셀을 화면에 그릴 때 사용.",
  "pyserial": "파이썬에서 시리얼 포트(USB)를 읽는 라이브러리. 아두이노 → 라즈베리파이 브릿지에 사용.",
  "OpenCR": "TurtleBot3의 제어 보드. 모터·IMU·배터리 전압을 ROS로 올려준다.",
  "RMW": "ROS Middleware. DDS 구현 선택 계층. 본 프로젝트는 rmw_fastrtps_cpp 통일.",
  "TurtleBot3": "ROBOTIS의 소형 교육용 자율주행 로봇. 본 프로젝트의 경비 로봇 본체(Burger).",
  "LiDAR": "레이저로 거리를 360° 측정하는 센서. SLAM·장애물 회피의 핵심 입력.",
  "Arduino": "센서를 읽는 소형 마이크로컨트롤러 보드. 본 프로젝트는 Uno R3 사용.",
  "Supabase": "오픈소스 백엔드(Postgres + 인증 + 스토리지). 이벤트·사진·로그 저장소.",
  "URDF": "로봇의 링크·관절을 XML로 기술한 모델. Unity로 import해 3D 로봇을 만든다.",
  "prefab": "Unity에서 재사용하는 게임 오브젝트 템플릿. import한 로봇 모델을 prefab으로 보관.",
  "SecurityEvent": "센서 감지를 담는 커스텀 ROS 메시지(robot_id·종류·심각도·pose).",
  "severity": "이벤트 심각도. 0(info)~3(high). 높을수록 즉시 대응이 필요.",
  "보드레이트": "시리얼 통신 속도(bps). 아두이노·라즈베리파이 양쪽 115200으로 통일.",
  "HC-SR501": "대표적인 PIR 모션 센서 모듈. 사람 움직임(적외선 변화)을 감지.",
  "KY-038": "마이크 기반 소리 감지 모듈. 임계값 초과 시 디지털 신호 출력.",
  "릴레이": "작은 신호로 큰 전류(워터펌프 등)를 켜고 끄는 전자 스위치.",
  "TFMessage": "좌표계(프레임)들 사이의 변환을 담는 메시지. /tf 토픽으로 흐른다.",
  "robot_id": "어느 로봇의 데이터인지 구분하는 식별자. \"tb3_1\"(티원) / \"tb3_2\"(젠지)."
};
