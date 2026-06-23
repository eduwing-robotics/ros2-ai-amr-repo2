# URHYNIX ROS 2 Workspace

TurtleBot3 + 카메라 인식 + Unity 디지털트윈 브릿지가 들어가는 ROS 2 워크스페이스 자리.

## 상태
- **준비됨**: 폴더 자리만 (sprint 2부터 본격 구성 예정)
- **타깃 ROS 배포판**: ROS 2 Humble (Ubuntu 22.04)
- **빌드 시스템**: colcon

## 예상 구조 (sprint 2 진입 시)

```
ros-ws/
├── src/
│   ├── urhynix_bringup/          # 런치 파일, 파라미터
│   ├── urhynix_unity_bridge/     # ROS-TCP-Connector 브릿지 (Unity ↔ ROS2)
│   ├── urhynix_obstacle_detect/  # 카메라 + LiDAR 융합 인식
│   └── urhynix_logger/           # 주행 데이터 → Supabase/Postgres
├── install/                       # colcon build 산출물 (.gitignore)
├── build/                         # 빌드 캐시 (.gitignore)
└── log/                           # 런타임 로그 (.gitignore)
```

## 다음 액션 (Sprint 2)

1. `ros2 pkg create urhynix_bringup --build-type ament_python`
2. ROS-TCP-Endpoint 의존성 추가
3. TurtleBot3 SLAM/Nav2 런치 파일 작성
4. `.gitignore`에 `build/`, `install/`, `log/`는 이미 추가됨 (루트 .gitignore 참고)

## 참고
- 메인 PRD: `../docs/ref/PRD.md`
- 아키텍처: `../docs/ref/ARCHITECTURE.md`
- Unity 브릿지 상대편: `../unity-src/`
