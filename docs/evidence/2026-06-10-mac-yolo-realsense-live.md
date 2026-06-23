# 2026-06-10 — Mac MPS + T1 RealSense → YOLOv8n 라이브 PASS

> 박물관 시연용 비전 트랙의 Mac 측 검증 1차 종결. T1(`192.168.10.250`) RealSense D435 영상이 Mac M5에서 26fps (headless) / 16fps (GUI imshow)로 YOLO 추론되며, Foxglove Studio 영상 끊김(라즈베리 11Hz publish + Wi-Fi 65Mbps 대역 초과) 원인 정량 진단 후 compressed 토픽 전환으로 해소.

## 한 줄 결과

| 지표 | 값 |
|------|----|
| Mac MPS + cv2 + YOLOv8n (headless) | **26.0 fps** |
| Mac MPS + cv2.imshow GUI | **16~17 fps** |
| 탐지 객체 | person 0.89 / keyboard 0.91 / cup 0.86 / tv 0.79 / mouse / laptop / cell phone |
| T1 publish (compressed) | 29.22 Hz, 2.17 MB/s |
| T1 publish (raw, 끊김 원인) | 11.27 Hz, 14.24 MB/s (Wi-Fi 65 Mbps 초과) |
| 네트워크 부하 절감 | **-85%** (raw → compressed) |
| 라즈베리 CPU 절감 | realsense_node **-87%p** (87.5% → ~0%) |

결과 이미지: `test/realsense_yolo_result.jpg` (FPS 26.0 HUD + 박스 13개 오버레이).

## 데이터 경로

```
T1 RealSense D435 (USB3, 8086:0b07)
   ↓ ros2 launch realsense2_camera rs_launch.py (color 640x480@30)
T1 /camera/camera/color/image_raw/compressed   (29.22Hz, JPEG)
   ↓ web_video_server (port 8080, multipart/x-mixed-replace MJPEG)
Mac cv2.VideoCapture("http://192.168.10.250:8080/stream?topic=...&type=mjpeg")
   ↓ YOLO(model='yolov8n.pt', device='mps')
Mac cv2.imshow + per-frame box overlay
```

병렬로 같은 T1 토픽을 다음도 sub 가능:
- `/foxglove_bridge` (port 8765) → Foxglove Studio (ws 클라이언트)
- `/ros_tcp_endpoint` (port 10000) → Unity ControlRoom (TCP)
- `web_video_server` (port 8080) → 브라우저 stream_viewer / cv2 / OBS

## T1 setup (이번 세션 적용)

```bash
# 1) 패키지 (sudo 비번 = t1 머신 sudo)
echo "<sudo>" | sudo -S apt-get install -y \
  ros-jazzy-foxglove-bridge \
  ros-jazzy-realsense2-camera \
  ros-jazzy-web-video-server

# 2) 3종 launch (ssh -fn 패턴, 함정 #19 회피)
ssh -fn t1@192.168.10.250 "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 launch realsense2_camera rs_launch.py enable_color:=true enable_depth:=true rgb_camera.color_profile:=640,480,30 depth_module.depth_profile:=640,480,30' > /tmp/local-rs.log 2>&1"

ssh -fn t1@192.168.10.250 "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0' > /tmp/local-fx.log 2>&1"

ssh -fn t1@192.168.10.250 "bash -c 'source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=230 && exec ros2 run web_video_server web_video_server --ros-args -p port:=8080 -p address:=0.0.0.0' > /tmp/local-wvs.log 2>&1"

# 3) turtlebot3_bringup (namespace=tb3_1)
ssh -fn t1@192.168.10.250 "bash -c 'source /opt/ros/jazzy/setup.bash && source ~/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=230 && export TURTLEBOT3_MODEL=burger && export LDS_MODEL=LDS-03 && export OPENCR_PORT=/dev/ttyACM0 && exec ros2 launch turtlebot3_bringup robot.launch.py namespace:=tb3_1' > /tmp/tb3_bringup.log 2>&1"
```

## Mac setup

```bash
brew install --cask foxglove-studio   # Foxglove app
# detect_realsense.py 작성: test/detect_realsense.py
cd /Users/family/jason/URHYNIX/test && source .venv/bin/activate

# 자동 검증 (headless + 120프레임 + 결과 저장)
FRAMES=120 HEADLESS=1 SAVE_LAST=./realsense_yolo_result.jpg python detect_realsense.py

# 라이브 GUI
python detect_realsense.py
```

## 진단 측정 (robot-camera-stream-diag 스킬 결과)

8지표 동시:

| # | 지표 | 측정값 | 임계 |
|---|------|--------|------|
| 1 | raw publish hz | 11.27 Hz | < 25 ❌ |
| 2 | raw bw | 14.24 MB/s = 114 Mbps | > Wi-Fi 65 Mbps ❌ |
| 3 | compressed publish hz | 29.22 Hz | ≥ 25 ✅ |
| 4 | compressed bw | 2.17 MB/s = 17 Mbps | < Wi-Fi 65×0.7=45 Mbps ✅ |
| 5 | realsense_node CPU | 87.5% → 0% | < 80% ✅ (전환 후) |
| 6 | load average (4코어) | 3.45 → ~1.x | < 코어 수 ✅ |
| 7 | Wi-Fi RSSI / link rate | -46 dBm / 65 Mbps | > -65 dBm ✅ |
| 8 | foxglove_bridge drop | 0 (compressed 후) | 0 ✅ |

## 함정 발견 (이번 세션)

| # | 함정 | 우회 | 박제 위치 |
|---|------|------|----------|
| **#19** | `nohup ... & disown` heredoc에서 SSH session 종료 시 같이 죽음 (로그 파일조차 생성 안 됨) | `ssh -fn <host> "bash -c 'cmd' > log 2>&1"` 패턴 (-f detach + -n stdin null) | `robot-camera-bringup` §C |
| Foxglove inactive-tab 20MB drop | macOS App Nap이 디코더 throttle → 큐 누적 → 20MB 한도 → drop | `defaults write dev.foxglove.studio NSAppSleepDisabled YES` + Foxglove 재시작 / 또는 publish rate 낮춤 (15Hz) / 또는 cv2 경로로 우회 | 세션 노트 |
| mDNS `rb.local` resolve 실패 | ARP 라즈베리 OUI(`d8:3a:dd`) + known_hosts ed25519 host key 매칭으로 신원 추적 | `robot-ip-detect-fallback` 신규 스킬 |
| T1 Wi-Fi 대역이 `0.x`→`10.x`로 점프 | 같은 머신, 새 IP. ssh ed25519 key 동일 | 메모리 `project_robot_ip_dynamic.md` 갱신 |
| `web_video_server`가 compressed 토픽도 stream으로 노출 | raw 토픽 그대로 `/stream?topic=...&type=mjpeg`도 동작 (web_video_server가 자체 mjpeg 인코딩) | 본 문서 §"Mac setup" |

## Custom YOLO labeling studio live proxy (2026-06-10 14:12 KST)

사용자용 라벨링 UI를 `scripts/yolo_training/custom_yolo_studio.py`로 추가했다. 목적은 브라우저에서 T1 RealSense 실시간 화면을 보면서 `Space`로 촬영하고, 드래그 박스를 저장한 뒤 Ultralytics YOLO `.pt`를 생성하는 흐름이다.

핵심 패치:
- 브라우저 `<img>`가 T1 LAN 주소를 직접 물지 않고 `http://127.0.0.1:8766/api/live.mjpg` 로컬 MJPEG 프록시를 사용한다.
- 학습용 캡처는 연속 스트림이 아니라 `web_video_server` snapshot endpoint에서 JPEG 1장을 받아 저장한다.
- 촬영 목록에서 기존 이미지/라벨을 다시 열고, 잘못 찍은 사진은 UI에서 이미지와 `.txt` 라벨을 같이 삭제할 수 있다.
- 화면은 실시간 `<img>`와 라벨링 `<canvas>`를 같은 stage에 겹쳐 두어 “화면 2개”처럼 보이지 않게 했다.

추가 패치 (14:30 KST):
- `web_video_server` 8080 MJPEG가 길게 연결하면 1fps 내외로 느려지는 문제가 있어 T1에 `scripts/yolo_training/t1_compressed_mjpeg_server.py`를 배포했다.
- T1 8090 서버는 `/camera/camera/color/image_raw/compressed`를 직접 구독해 `/stream.mjpg`, `/snapshot.jpg`, `/status`를 제공한다.
- 실시간 미리보기는 320px/quality 55로 경량화하고, 학습용 캡처는 640x480 원본 snapshot을 유지한다.
- UI의 촬영 목록은 `jpg 파일명 클릭 = 원본 이미지 새 탭 열기`, `수정 버튼 = 라벨 캔버스 열기`로 분리했다.

복구 이력:
- 증상: `snapshot`/`stream` 모두 5초 동안 0 bytes. Mac UI가 아니라 T1 `web_video_server`가 프레임을 흘리지 않는 상태였다.
- 조치: T1에서 `web_video_server`만 PID 직접 종료 후 재실행. 새 프로세스: `/opt/ros/jazzy/lib/web_video_server/web_video_server` PID `4130`.

검증:
- 원본 snapshot: HTTP 200, `Content-Type: image/jpeg`, `75403` bytes.
- 원본 MJPEG stream: HTTP 200, 7초 동안 `943840` bytes 수신.
- 로컬 프록시 `/api/live.mjpg`: HTTP 200, 7초 동안 `565248` bytes 수신.
- 캡처 API: `/api/capture` HTTP 200, `640x480` 저장 확인 후 테스트 캡처는 삭제하여 데이터셋을 0장으로 복구.
- 브라우저 스크린샷: `docs/evidence/2026-06-10-yolo-labeling-ui-live-proxy.png` (단일 화면 stage + 실시간 영상 표시 확인).
- T1 8090 status: `ok=true`, frame `count` 증가, `age_sec` 약 0.01초.
- 8090 lightweight stream: 4초 동안 26프레임, 평균 JPEG 약 7.7KB/frame.
- jpg 직접 열기: `/api/item_image?split=train&stem=...` 새 탭에서 `640x480` 이미지 표시 확인.
- 14:37 KST 승리 패턴 저장: 긴 MJPEG `<img>` 대신 `preview.jpg` 단발 요청 루프 사용. T1 8090 서버는 `--stream-width 240 --stream-quality 45 --preview-fps 8`, UI는 이전 preview 요청이 끝난 뒤 다음 요청을 보낸다. `/preview.jpg`는 약 4.6KB, 측정상 대체로 0.18~0.53초. 더 낮춘 `200px / quality 35 / 6fps`는 1초 timeout이 섞여 안정 default로 채택하지 않음.
- 하네스 저장: `/Users/family/jason/jason-agent-harness-template/harnesses/robot-yolo-capture-train.md` 의 `URHYNIX Low-Latency Live Pattern`.
- 14:43 KST latency 계측 추가: T1 preview 이미지 좌상단에 `T1 HH:MM:SS.mmm` + frame id 오버레이, 브라우저 stage 우상단에 `브라우저 HH:MM:SS.mmm` 오버레이를 추가했다. 눈으로 두 시각 차이를 비교해 실제 operator 지연을 판단한다.
- UX 결정: `Space` 촬영은 비동기 저장 후 실시간 preview를 유지한다. 라벨링은 촬영 목록의 `수정` 버튼으로 나중에 수행한다. 여러 장을 빠르게 모으는 데이터셋 수집 단계에서 매 촬영마다 라벨 모드로 진입하는 것보다 효율적이다.
- 14:57 KST ROI 자동 연사 UI 추가: `영역 지정`으로 live preview 위에 고정 ROI를 드래그하고, `촬영 장수`/`촬영 간격 ms` 설정 후 `연사 시작`을 누르면 매 사진마다 같은 ROI 박스를 자동 YOLO 라벨로 저장한다. 용도는 물건을 ROI 안에 놓고 손으로 방향을 바꾸며 50~150장 빠르게 모으는 세션. 실제 대량 연사는 사용자 데이터셋 오염 방지를 위해 Codex가 대신 실행하지 않음.

## ROI mask bbox auto-label tightening (2026-06-10 15:18 KST)

ROI 연사 라벨이 너무 넓으면 손/팔/몸통/배경까지 `학습대상`으로 배울 수 있어, `scripts/yolo_training/custom_yolo_studio.py`에 `/api/auto_label_roi`를 추가했다.

새 저장 흐름:
1. 640x480 원본 frame 저장
2. 지정 ROI crop
3. `rembg`가 설치되어 있으면 rembg mask 시도
4. 현재 기본 환경처럼 rembg/SAM이 없으면 OpenCV GrabCut mask 사용
5. mask의 가장 큰 foreground component bbox 계산
6. bbox가 너무 작거나 너무 넓으면 기존 ROI 박스로 fallback
7. 계산된 bbox를 YOLO txt로 저장

UI 변경:
- `영역 자동 연사` 패널에 `ROI 안 물체 bbox 자동 보정` 체크박스 추가(기본 ON).
- 연사 중 `bbox 보정 N · fallback M` 카운터를 표시해 라벨 신뢰도를 사용자가 바로 볼 수 있게 했다.
- 데이터셋 상태에 자동 보정 엔진 상태를 표시한다. 현재 환경: `auto / GrabCut`, `rembg_available=false`, `sam_available=false`.

검증:
- `test/.venv/bin/python -m py_compile scripts/yolo_training/custom_yolo_studio.py` PASS.
- T1 8090 status fresh: `ok=true`, `age_sec=0.002`, `count=64304`.
- 로컬 앱 재시작: `http://127.0.0.1:8766`, PID `53756`.
- `/api/status` PASS: `train_images=122`, `train_labeled=122`, `val_images=30`, `val_labeled=30`, `auto_label.engine=auto`.
- 안전 smoke: 테스트 캡처 `학습대상_20260610_151850_0153` 1장 생성 → `/api/auto_label_roi` 호출 → `engine=grabcut`, `fallback=false`, `mask_area_ratio=0.5436`, 저장 bbox `(116,88)-(470,394)` → 테스트 jpg/txt 즉시 삭제.
- Browser snapshot PASS: 새 UI에서 `ROI 안 물체 bbox 자동 보정` 체크박스 표시 확인, 이전 탭 닫아 live preview 요청 1개로 유지.

스킬화:
- 새 Claude 스킬: `.claude/skills/urhynix-yolo-capture-train/SKILL.md`
- 공용 스킬 복사: `/Users/family/jason/jason-agent-harness-template/.claude/skills/urhynix-yolo-capture-train/SKILL.md`
- 공용 하네스 보강: `/Users/family/jason/jason-agent-harness-template/harnesses/robot-yolo-capture-train.md`
- 공용 레지스트리 등록: `/Users/family/jason/jason-agent-harness-template/harnesses/REGISTRY.md`

### Live segmentation preview (2026-06-10 15:24 KST)

사용자가 ROI 안에서 물건을 움직이며 세그멘테이션이 어떻게 잡히는지 볼 수 있도록 `실시간 세그 보기` 모드를 추가했다.

구현:
- UI: `영역 자동 연사` 패널에 `실시간 세그 보기` 체크박스 추가.
- API: `/api/segment_frame.jpg?x1=...&y1=...&x2=...&y2=...&class_id=...&engine=auto`.
- 저장 없음: 세그 preview는 화면 전용이며 데이터셋 jpg/txt를 생성하지 않는다.
- 입력 frame: 저장용 snapshot 대신 T1 8090 `/preview.jpg`를 640x480으로 맞춰 사용한다. 학습/연사 저장은 계속 640x480 원본 snapshot 사용.
- 속도 최적화: preview 전용 GrabCut은 ROI crop을 최대 220px로 축소하고 2 iteration만 수행한 뒤 mask를 원래 크기로 되돌린다. 저장용 자동 라벨은 기존 정확도 우선 경로 유지.

검증:
- `py_compile` PASS.
- 직접 API 호출 5회: `0.867s`, `0.444s`, `0.536s`, `0.399s`, `0.452s`로 HTTP 200 JPEG 생성.
- Browser snapshot PASS: `실시간 세그 보기` 체크박스 표시 확인.
- 확인 이미지: `/tmp/urhynix-segment-preview-fast-5.jpg`는 ROI가 사람 몸통 쪽이라 `fallback: grabcut: no foreground mask` 표시. 이 경고는 라벨 품질에 유용하며, 실제 학습 물체만 포함한 작은 ROI로 다시 잡아야 한다.

### Dataset multi-delete UI (2026-06-10 15:28 KST)

잘못 모은 기존 학습 데이터셋을 UI에서 안전하게 정리할 수 있도록 촬영 목록에 다중 삭제 기능을 추가했다.

구현:
- 촬영 목록 각 행에 체크박스 추가.
- 버튼 추가: `전체 선택`, `라벨 없음 선택`, `선택 삭제`.
- `선택 삭제`는 선택 0장일 때 disabled.
- 삭제 전 확인창 표시.
- 삭제 API: `/api/delete_items`는 선택된 각 항목의 jpg와 YOLO txt를 같이 삭제한다.

검증:
- `py_compile` PASS.
- `/api/delete_items` 빈 payload smoke: `{"deleted": [], "deleted_files": 0, "errors": []}`.
- Browser snapshot PASS: `전체 선택`, `라벨 없음 선택`, `선택 삭제`, `선택 0장` 표시 확인.
- 이후 기존 잘못된 학습 데이터 삭제 완료 상태 확인: `train_images=0`, `train_labeled=0`, `val_images=0`, `val_labeled=0`. 학습 결과 `.pt` 파일은 `runs/custom_object/.../weights/best.pt`에 남아 있음.

### Fast YOLO detect preview (2026-06-10 15:45 KST)

새 학습 run `/Users/family/jason/URHYNIX/runs/custom_object/학습대상_20260610_153621/weights/best.pt` 검증 후, `탐지 보기`가 너무 끊기는 문제를 확인했다.

원인:
- SAM/rembg 문제가 아니라 UI 탐지 표시 경로 문제.
- 기존 `/api/detect_frame.jpg`는 full snapshot 기반이라 단일 호출이 약 `2.196s`까지 걸렸고, 브라우저도 frame load 뒤 `900ms`를 추가로 기다렸다.

조치:
- `detect_jpeg()`를 T1 8090 `/preview.jpg` 기반 `read_preview_frame()`으로 전환. 학습/저장 캡처는 계속 원본 snapshot 사용.
- 브라우저 detect polling delay를 `900ms`에서 `80ms` 기준으로 단축. 다음 요청은 이전 JPEG load 후에만 보내므로 요청 중첩은 없음.
- 오버레이 텍스트에 `fast best.pt` 표시.

검증:
- 최신 모델 로드: `/api/load_model` → `학습대상_20260610_153621/weights/best.pt`.
- 직접 detect API 5회: `0.340s`, `0.677s`, `0.463s`, `0.287s`, `0.695s`.
- 이전 1장 `2.196s` 대비 UI 표시 병목 크게 감소.
- 확인 이미지: `/tmp/yolo-detect-fast-5.jpg`에 `fast best.pt` HUD 표시.

판단:
- SAM은 실시간 YOLO detect view를 빠르게 만드는 도구가 아니다. SAM/rembg는 라벨 mask/bbox 품질을 높여 재학습 데이터를 좋게 만드는 쪽에 사용한다.
- 탐지 화면이 계속 끊기면 다음 병목은 T1 preview 응답 시간 또는 브라우저 탭 중복 요청 수를 본다.

### Latest best.pt auto-load + SAM2 labeling path (2026-06-10 15:53 KST)

`best.pt 불러오기`가 서버 재시작 후 빈 `train.best_pt`에 의존하지 않도록 `runs/custom_object/*/weights/best.pt` 중 최신 mtime 파일을 자동 선택하는 `/api/load_latest_model` 경로를 추가했다.

검증:
- 최신 후보: `/Users/family/jason/URHYNIX/runs/custom_object/학습대상_20260610_153621/weights/best.pt`
- `/api/load_latest_model` 응답: 위 최신 `best.pt` 로드 PASS.
- `/api/status`: `detect_model`과 `latest_best_pt`가 모두 위 최신 파일을 가리킴.
- `/api/detect_frame.jpg`: 최신 모델 로드 후 `0.254s`, JPEG `30KB`.
- T1 8090 status fresh: `ok=true`, `age_sec=0.009`, `count=126663`.

SAM2:
- `ultralytics.YOLO("sam2_t.pt")` 호출은 잘못된 방식이며 `OrderedDict.float` 오류가 난다.
- 올바른 방식은 `from ultralytics import SAM; SAM("sam2_t.pt")`.
- `sam2_t.pt` 실제 로드 PASS: `SAM2Model`.
- 데이터셋 이미지 bbox prompt → `masks=True`, shape `(1, 480, 640)`, area ratio `0.1339`.
- 앱 내부 `_mask_box_from_roi(..., "sam2")` smoke PASS: `engine=sam2`, `fallback=false`, `mask_area_ratio=0.6237`.
- `/api/segment_frame.jpg?...&engine=sam2` preview는 동작하지만 첫 호출 `5.685s`라 실시간 화면용 기본값으로 쓰지 않는다.

판단:
- 저장용 자동 라벨링은 `auto -> SAM2 -> rembg -> GrabCut -> ROI fallback` 순서로 정밀 bbox를 만든다.
- 실시간 세그 preview 기본 경로는 프레임 유지를 위해 기존 fast GrabCut 계열을 유지한다. SAM2 preview는 품질 확인용 단발 테스트에 가깝다.

### Non-blocking segmentation overlay (2026-06-10 16:02 KST)

사용자가 ROI 안에서 물건을 돌릴 때 `실시간 세그 보기`가 끊겨 위치 맞추기가 어려운 문제가 있었다.

원인:
- 기존 `실시간 세그 보기`는 `/api/segment_frame.jpg` 결과 JPEG를 실시간 화면 자체로 교체했다.
- 따라서 세그 계산이 `0.4~0.8s`만 걸려도 카메라 화면도 같은 속도로 떨어졌다.

조치:
- 원본 실시간 preview 루프는 계속 `/preview.jpg`로 유지한다.
- 세그멘테이션은 별도 `<img id="segmentOverlay">` 투명 PNG 레이어로 분리한다.
- 새 API: `/api/segment_overlay.png?...` 는 `640x480 RGBA` 투명 PNG에 mask/bbox만 그려 반환한다.
- 브라우저도 raw live timer와 segment overlay timer를 분리했다.
- `실시간 세그 보기`를 꺼도 원본 live는 유지되고 overlay만 제거된다.

검증:
- `py_compile` PASS.
- T1 8090 status fresh: `ok=true`, `age_sec=0.007`, `count=142989`.
- `/api/segment_overlay.png?...engine=auto`: `0.761s`, `640x480 RGBA PNG`, `14KB`.
- `/preview.jpg`: `0.597s`, `240x180 JPEG`, `5.1KB`.
- Browser 최신 탭: `http://127.0.0.1:8766/?v=overlay-seg-20260610-1602`.
- 오래된 중복 탭 1개 닫아서 live 요청 중복을 줄임.

### Mapped-only burst capture (2026-06-10 16:27 KST)

고정 ROI 라벨이 많이 섞이면 손/배경까지 학습될 수 있어, 자동연사 기본 정책을 “매핑 성공 컷만 저장”으로 바꿨다.

변경:
- UI 체크박스 추가: `매핑 성공한 사진만 저장` 기본 ON.
- `ROI 안 물체 bbox 자동 보정`이 켜져 있고 `/api/auto_label_roi` 결과가 `fallback=true`이면 해당 jpg/txt를 즉시 `/api/delete_item`으로 삭제한다.
- `촬영 장수`는 가능한 한 저장 성공 장수 기준으로 동작한다.
- 무한 반복 방지를 위해 mapped-only 모드에서 최대 시도 횟수는 `max(total + 20, total * 2.5)`로 제한한다.
- 진행 문구에 `bbox 보정`, `fallback`, `삭제`, `시도` 카운트를 같이 표시한다.

판단:
- 정확한 물체 학습이 목표면 fallback/ROI 컷은 학습 데이터로 남기지 않는 것이 안전하다.
- fallback이 자주 발생하면 ROI를 좁히거나 배경 대비/조명을 바꾸고, 실시간 세그 overlay에서 mask가 물체만 잡히는지 다시 확인한다.

검증:
- `py_compile` PASS.
- 서버 재시작 후 `http://127.0.0.1:8766/?v=mapped-only-20260610-1627` 로드.
- HTML에서 `mappedOnlyBox`, `매핑 성공한 사진만 저장` 확인.
- 오래된 중복 탭 1개 닫음.

### Burst live smoothness fix (2026-06-10 16:45 KST)

연사 시작 시 화면이 끊기는 문제가 있어, 원인을 `세그 오버레이 SAM2 요청`과 `저장용 SAM2 자동라벨 요청`이 동시에 도는 병목으로 판단했다.

조치:
- `showSegmentPreview()`에 `burstRunning` 가드를 추가해 연사 중 세그 오버레이 요청을 금지.
- `refreshStatus`, `setRoiMode`, `setLabelingMode` 경로에서도 연사 중 overlay 재시작을 차단.
- `startBurst()` 진입 시 `stopSegmentPreview()`를 호출하고 원본 `/preview.jpg` live만 유지.
- 진행 문구: `세그 오버레이는 일시정지하고 원본 실시간만 유지합니다.`

검증:
- `py_compile` PASS.
- HTML 반영 확인: `if (burstRunning) return`, `세그 오버레이는 일시정지`.
- T1 8090 status fresh: `ok=true`, `age_sec=0.023`.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=burst-pause-seg-20260610-1645`.

### Item mask review button (2026-06-10 17:04 KST)

촬영 목록에서 `수정`을 누르면 YOLO detect 라벨 형식상 bbox 박스만 보이는 문제가 있었다. 이는 저장 라벨이 mask가 아니라 YOLO bbox `.txt`이기 때문이므로, 검수용 `마스크` 버튼을 별도로 추가했다.

변경:
- 촬영 목록 각 행에 `마스크` 링크 추가.
- 새 API: `/api/item_mask_image?split=...&stem=...&engine=auto`.
- 저장된 bbox를 ROI로 다시 SAM2/rembg/GrabCut mask를 계산한다.
- 검수 이미지는 배경을 어둡게 낮추고, mask로 잡힌 부분만 원본 밝기로 보여준다.
- `수정`은 기존처럼 bbox 편집, `마스크`는 배경 제거 검수로 역할 분리.

검증:
- `py_compile` PASS.
- 최신 train item `학습대상_20260610_165705_0099` 검수 이미지 생성 PASS: `640x480 JPEG`, `34KB`, `1.313s`.
- 확인 이미지: `/tmp/urhynix-item-mask-review.jpg`.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=item-mask-review-20260610-1704`.

### Arrow-key review/delete mode (2026-06-10 17:10 KST)

촬영 목록을 하나씩 눌러 새 탭으로 확인하는 흐름이 느려, 앱 안 검수 모드를 추가했다.

변경:
- 촬영 목록 패널에 `검수 시작`, `← 이전`, `현재 삭제`, `다음 →` 버튼 추가.
- 각 행의 `마스크` 링크는 새 탭 대신 앱 stage에 검수 이미지를 표시한다.
- 검수 모드에서 `←/→` 키로 이전/다음 이동.
- `Delete` 또는 `Backspace`로 현재 사진과 라벨 파일 삭제.
- `Esc` 또는 `실시간 다시 보기`로 검수 모드 종료.
- 삭제 후 남은 목록에서 같은 위치의 다음 사진을 계속 표시한다.

검증:
- `py_compile` PASS.
- HTML 반영 확인: `reviewStart`, `reviewPrev`, `reviewDelete`, `ArrowRight`, `reviewMode`.
- `/api/item_mask_image` smoke PASS: `640x480 JPEG`, `1.379s`.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=review-mode-20260610-1710`.

### Mask review files export (2026-06-10 17:23 KST)

API로 즉석 생성하던 마스크 검수 이미지를 폴더에서 직접 볼 수 있도록 일괄 내보내기 기능을 추가했다.

변경:
- 촬영 목록 패널에 `마스크 파일 생성` 버튼 추가.
- 새 API: `/api/export_mask_reviews`.
- 출력 폴더: `datasets/custom_object/review_masks/{train,val}`.
- 파일명: `<stem>_mask.jpg`.
- 원본 데이터셋 `images/`, `labels/`는 변경하지 않는 검수용 파생 파일이다.

검증:
- `py_compile` PASS.
- 전체 export PASS: `149`장 생성, errors `0`.
- 출력 루트: `/Users/family/jason/URHYNIX/datasets/custom_object/review_masks`.
- 샘플 확인: `/Users/family/jason/URHYNIX/datasets/custom_object/review_masks/train/학습대상_20260610_172145_0176_mask.jpg`.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=mask-export-20260610-1723`.

### Review in-frame delete button + D shortcut (2026-06-10 17:40 KST)

검수 중 시선을 촬영 목록 패널로 옮기지 않고 현재 사진을 바로 제거할 수 있도록 stage 안 삭제 UI를 추가했다.

변경:
- 검수 모드에서 이미지 오른쪽 아래에 `D 삭제` 버튼 표시.
- `D 삭제` 버튼은 기존 `/api/delete_item` 경로를 사용해 현재 JPG와 TXT를 같이 삭제한다.
- 검수 모드에서 `D` 키는 현재 사진 삭제 확인창을 열고, 검수 모드가 아닐 때만 기존 `D 탐지 보기 전환`으로 동작한다.
- 검수 종료, 실시간 복귀, 라벨 수정 진입 시 stage 안 삭제 버튼을 숨긴다.

검증:
- `py_compile` PASS.
- 8766 서버 재시작 후 HTML 반영 확인: `reviewDeleteOverlay`, `D 삭제`, `D/Delete 현재 사진 삭제`.
- 브라우저 검수 모드에서 `D 삭제` 버튼 표시 확인.
- 브라우저 `D` 키 입력 시 현재 검수 사진 삭제 confirm 표시 확인.
- 데이터셋 개수 유지 확인: train `99/99`, val `50/50`.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=review-delete-d-20260610-1740`.

### Review visibility/cache fix (2026-06-10 17:52 KST)

검수 시작 후 이미지가 표시되지 않는 것처럼 보이는 문제를 확인했다.

원인:
- 검수 이미지가 실제로는 로드됐지만, 사용자가 촬영 목록 위치까지 스크롤한 상태라 stage가 화면 위로 밀려 있었다.
- 검수 이미지 URL이 `engine=auto`로 SAM2를 다시 호출해 첫 표시가 느리거나 서버가 잠깐 막힐 수 있었다.

변경:
- `showReviewAt()`에서 검수 진입 시 `window.scrollTo({top: 0})`로 stage를 즉시 화면 안에 표시한다.
- 검수 화면과 `마스크` 링크는 `engine=cache`를 사용한다.
- `/api/item_mask_image?engine=cache`는 `datasets/custom_object/review_masks`의 기존 검수 이미지를 우선 서빙하고, 없거나 오래된 경우 빠른 bbox 검수 이미지로 표시한다.
- 라벨 수정 저장 또는 사진 삭제 시 해당 `review_masks` 캐시 파일도 삭제한다.

검증:
- `py_compile` PASS.
- cache 검수 이미지 API 응답: `0.014s`, `640x480 JPEG`.
- 브라우저에서 일부러 `scrollY=450` 상태로 만든 뒤 `검수 시작` 클릭: `scrollY=0`, `검수 1/110`, 이미지 `640x480`, `D 삭제` 표시.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=review-visible-fix-20260610-1752`.

### Hard-negative background capture (2026-06-10 18:06 KST)

배경을 물건으로 오탐하는 최신 `best.pt`를 정제하기 위해, 오탐 순간을 빈 라벨 데이터로 저장하는 기능을 추가했다.

변경:
- 탐지 패널에 `N 오탐 배경 저장` 버튼 추가.
- 키보드 `N`으로 현재 프레임을 hard negative로 저장.
- 새 API: `/api/save_negative_frame`.
- 저장 파일명: `negative_<class>_<timestamp>_<index>.jpg`.
- 같은 이름의 빈 `.txt` 라벨 파일을 생성해 YOLO background sample로 학습에 포함한다.
- 데이터셋 통계에 `배경 학습`, `배경 검증` 카운터 추가.
- 촬영 목록에서 negative 샘플은 `라벨 없음` 대신 `배경 학습`으로 표시.
- `라벨 없음 선택`은 의도적 negative 샘플을 제외해 실수 삭제를 줄인다.

검증:
- `py_compile` PASS.
- `/api/save_negative_frame` smoke PASS: JPG + 빈 TXT 생성 확인.
- smoke로 만든 `negative_학습대상_20260610_180558_0069`는 `/api/delete_item`으로 즉시 삭제해 데이터셋 오염 없음.
- 브라우저 새 탭에서 `N 오탐 배경 저장` 버튼 표시 확인.
- 이전 검수 confirm이 쌓인 탭은 닫고 clean 탭 사용.
- 최신 브라우저 탭: `http://127.0.0.1:8766/?v=hard-negative-20260610-1806-clean`.

## 박제된 자산 (이번 세션)

| 종류 | 자산 | 사용 시점 |
|------|------|----------|
| 새 스킬 | `.claude/skills/robot-ip-detect-fallback/SKILL.md` | mDNS 깨졌을 때 |
| 새 스킬 | `.claude/skills/robot-camera-stream-diag/SKILL.md` | 영상 끊김 시 6대축 진단 |
| 새 스킬 | `.claude/skills/urhynix-yolo-capture-train/SKILL.md` | 맞춤 YOLO 캡처/ROI 연사/마스크 bbox 보정/학습/탐지 |
| 스킬 보강 | `.claude/skills/robot-camera-bringup/SKILL.md` (§C ssh -fn / §D foxglove / §E compressed + 함정 #19) | 매 세션 첫 5분 |
| 메모리 | `~/.claude/projects/-Users-family-jason-URHYNIX/memory/project_robot_ip_dynamic.md` | 다음 세션 자동 로드 |
| 코드 | `test/detect_realsense.py` (env: `FRAMES` `HEADLESS` `SAVE_LAST` `T1_IP` `T1_PORT` `T1_TOPIC`) | Mac MPS RealSense YOLO |
| 하네스 | `/Users/family/jason/jason-agent-harness-template/harnesses/robot-yolo-capture-train.md` | 다음 프로젝트/세션에서 동일 패턴 재사용 |
| 문서 | `test/CLAUDE.md` Y5 진입 한 줄 | |

## 다음 트랙 후보

1. **젠지(Pi Camera)도 동시 추론** — 이중 카메라 YOLO. Mac 한 화면에 두 카메라 분할 추론.
2. **depth 추가** — `/camera/.../depth/image_rect_raw`를 받아 박스 중심 픽셀 거리 표시.
3. **Unity ControlRoom 통합** — Mac 추론 결과를 다시 ROS2 토픽 (`/yolo/detections`)으로 publish → Unity 패널이 sub.
4. **realsense 15Hz + depth off로 최적화** — 박물관 시연 안정성. compressed에 충분.

## 검증 사진

`test/realsense_yolo_result.jpg`:
- 좌상단 HUD: `FPS 26.0  device=mps`
- 박스 13개: person ×4, keyboard 0.90, cup 0.81, tv ×2, laptop 0.48, mouse 0.37
- 해상도: 640 × 480
- 시각: 주인님 책상 (Unity 화면 모니터 + 한국어 라벨 컵 + 검정 키보드)

## 한 줄

박물관 시연 비전 트랙의 Mac 절반 검증 끝. 라즈베리는 영상만 publish, Mac MPS가 YOLO 추론을 26fps로 처리하는 분업이 박물관 시연 본선 후보 구조로 굳어졌고, 끊김 원인(Wi-Fi 65Mbps 대역 초과)도 정량 진단 + compressed 전환으로 해소.
