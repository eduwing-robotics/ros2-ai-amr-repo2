# D435 3D 점군 캡처 — 2026-06-25

티원 RealSense D435로 공간 3D 컬러 점군을 떠서 디지털트윈 입력을 만든 세션. 스킬 `urhynix-d435-3d-pointcloud-capture`로 굳힘.

## 산출물
| 파일 | 내용 |
|---|---|
| `2026-06-25-d435-rot/rot360_odom.ply` | **메인** — 360° 회전 odom 누적 컬러 점군, 1,200만 점 (182MB) |
| `2026-06-25-d435-rot/rot_verify.png` | 탑다운 평면도 + 측면 (사방 벽 사각형 = 회전 성공 확인) |
| `2026-06-25-d435-rot/d435_rot_1782378952/` | 원본 rosbag (mcap, 245MB) |
| `2026-06-25-d435-static/static_snapshot.ply` | 정적 단일시점 7.4만 점 (파이프라인 검증용) |
| `2026-06-25-d435-static/ply_verify.png` | 정적 정면+평면도 |

## 절차 (경로 B — 티원 캡처, Mac 복원)
1. `_t1_rs_pointcloud.sh` — D435 aligned depth 640x480x15 (wrapper가 pointcloud.enable 미지원 → aligned depth 사용).
2. `_t1_bringup_only.sh` — turtlebot3 bringup으로 odom/tf 확보.
3. static tf `tb3_1/base_link → camera_link` (추정 x0.04 z0.10).
4. `d435_record_smoke.sh 0.3 21` — record(timeout INT) + drive_rotate(TwistStamped) 제자리 360°.
5. scp → Mac → `d435_bag_to_ply.py --accumulate` (rosbags deproject + odom tf 누적).
6. numpy 탑다운 렌더로 360° 분포 육안 검증.

## 측정값
- aligned depth 14.85Hz, USB3 SuperSpeed(5000M), 티원 load ~1.0 여유.
- intrinsics fx=604.5 fy=603.2 cx=324.1 cy=254.2 (640x480).
- 누적 점군 범위: x±3.1m, y±3.7m, z −0.5~1.6m (odom frame).

## 한계
- odom 누적 = 드리프트(loop closure 없음). 정밀은 RTAB-Map.
- 단일 위치 = 가림(물체 뒤·먼 구석 빈 곳).
- D435 0.3~3m → 먼 벽 부분적.

## 보류 (다음 세션)
- Phase 3: `rot360_odom.ply`를 Unity ControlRoom `map-3d-container`에 띄우기 (Map3DSceneCloudLayer.cs).
- Phase 2B: 같은 bag으로 RTAB-Map A/B 비교(visual loop closure vs odom 누적).
