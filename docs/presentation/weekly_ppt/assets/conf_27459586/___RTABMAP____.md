<!-- 동료_RTABMAP_실행법.md — 동료(우분투)가 RTAB-Map으로 D435 bag을 3D 맵으로 재처리하는 초간단 안내.
     상세/함정은 [[urhynix-rtabmap-docker-mac-blocked]] 메모리·scripts/rtabmap_*.sh 참고. -->

# RTAB-Map 3D 맵 만들기 (동료용, 우분투)

받은 것: `rtabmap_setup_ubuntu.sh`, `rtabmap_replay_bag.sh`, 그리고 bag 폴더(`d435_rot_...`).
3개를 같은 폴더(예: `~/urhynix/`)에 두고 터미널에서 그 폴더로 이동.

## 전체 흐름 (촬영 → 3D 맵)

1. **T1 로봇** SSH에서 bag 녹화 (`_robot_bringup_ns.sh`, `_t1_rs_pointcloud.sh`, `d435_record_only.sh`)
2. bag 폴더를 노트북 `~/urhynix_rtabmap/` 으로 복사
3. 아래 ② 실행

상세 절차: `RTABMAP_재처리_작업기록_2026-06-26.txt`

## 딱 2번 실행 (노트북)

```bash
# ① 설치 (처음 한 번만, 10~20분. sudo 비번 물어봄)
bash rtabmap_setup_ubuntu.sh

# ② 3D 맵 만들기 (창이 뜨고 맵이 실시간으로 쌓임 → 끝나면 PLY 자동 저장)
bash rtabmap_replay_bag.sh d435_rot_1782453993
```

끝나면 같은 위치 `rtabmap_out/` 안에 **PLY 파일**이 생겨요. CloudCompare나 MeshLab으로 열면 3D로 보여요.

## 보는 법
- ②를 실행하면 **rtabmap_viz** 창이 떠요. bag이 재생되는 동안 **맵이 눈앞에서 자라요.**
- 다 돌면(약 3분) 창은 그대로 두고, 터미널에 `PLY: ...` 경로가 찍혀요.
- 이미 만든 맵 다시 보기:
  ```bash
  cloudcompare ~/urhynix_rtabmap/rtabmap_out/rtabmap_cloud.ply
  # 또는
  rtabmap-databaseViewer ~/urhynix_rtabmap/rtabmap_out/rtabmap.db
  ```
  → DB 뷰어 창/터미널은 **그냥 닫아도 됨** (이미 저장된 DB 읽기만 함)

## 잘 안 되면
- `bash: ros2: command not found` → `source /opt/ros/jazzy/setup.bash` 후 다시. (우분투 22.04면 jazzy 대신 humble)
- 맵이 안 쌓이고 "Did not receive data"만 뜨면 → 터미널 로그(`rtabmap_out/rtabmap.log` 끝 40줄) 캡처해서 URHYNIX팀에 전달. (※ 이건 Mac/Docker에서만 나던 증상이라 네이티브 우분투면 정상일 것)
- bag 폴더 안에 `*.mcap` + `metadata.yaml` 있는지 확인.

## 참고
- bag 2개(`d435_rot_1782453993` 178초, `d435_rot_1782454248` 156초) 각각 ②로 돌리면 돼요. 큰 거 하나만 해도 충분.
- 이 데이터는 무결성 검증됨(토픽·타임스탬프 정상). 네이티브 우분투에서 동작하는 게 정상.
