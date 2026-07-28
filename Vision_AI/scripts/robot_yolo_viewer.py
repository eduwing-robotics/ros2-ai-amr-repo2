#!/usr/bin/env python3
"""로봇 카메라 1회 구독 + YOLO + 화면 (단일 프로세스 — Wi-Fi·끊김 최적)."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

from museum_patrol_nodes.cv2_display_env import configure_opencv_display, patch_after_cv2_import

configure_opencv_display()

import cv2
import numpy as np
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import String

try:
    import torch
    from ultralytics import YOLO
    from museum_patrol_nodes.detection_filters import DetectionFilter, FilterConfig, RawBox
    from museum_patrol_nodes.image_utils import (
        compressed_imgmsg_to_bgr,
        imgmsg_to_bgr,
        preprocess_for_inference,
        topic_is_compressed,
    )
    from museum_patrol_nodes.yolo_model_utils import (
        COMPANION_TARGET_NAMES,
        PERSON_ONLY_TARGET_NAMES,
        extract_target_boxes,
        load_companion_person_model,
        model_has_class,
        model_has_person,
        person_class_ids,
        target_class_ids,
    )
except ImportError:
    print('[ERROR] source scripts/camera_laptop_env.sh 후 실행', file=sys.stderr)
    raise

patch_after_cv2_import()

WAITING_BGR = (32, 32, 32)
WAITING_TEXT = (220, 220, 220)


TARGET = frozenset({'fire', 'smoke', 'person', 'statue'})
COLORS = {
    'fire': (0, 0, 255),
    'smoke': (128, 128, 128),
    'person': (255, 128, 0),
    'statue': (255, 0, 255),
}
LABELS = {
    'fire': 'FIRE',
    'smoke': 'SMOKE',
    'person': 'PERSON',
    'statue': 'STATUE',
}
OVERLAY_HOLD_SEC = 0.0  # no linger — clear boxes when detection gone
STATUS_DEBOUNCE_SEC = 2.0

COMPRESSED_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,  # drop oldest — never backlog JPEG on Wi-Fi
    durability=DurabilityPolicy.VOLATILE,
)

# Safe default: RealSense JPEG from tb3_1 launch (NOT image_detect)
DEFAULT_CAMERA_TOPIC = '/tb3_1/camera/color/image_raw/compressed'


def parse_args() -> argparse.Namespace:
    ws = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description='Robot camera + YOLO single-process viewer')
    p.add_argument('--camera-topic', default=os.environ.get(
        'CAMERA_TOPIC',
        os.environ.get(
            'T1_CAMERA_COMPRESSED',
            DEFAULT_CAMERA_TOPIC,
        ),
    ))
    p.add_argument('--model', type=Path, default=ws / 'models' / 'museum_fire_smoke.pt')
    p.add_argument('--person-model', default='yolov8n.pt',
                   help='COCO person companion (empty=off). With museum_finetune '
                        'main, auto-hybrid: main=fire/statue, companion=person')
    p.add_argument(
        '--force-person-companion',
        action='store_true',
        help='Always use --person-model for person even if main has person class',
    )
    p.add_argument('--smoke', action='store_true',
                   help='Enable smoke detection (default: off)')
    p.add_argument('--no-smoke', action='store_true',
                   help='Deprecated alias — smoke is already off by default')
    p.add_argument('--generic', action='store_true',
                   help='Show every class from the main model without fire/smoke filters')
    p.add_argument('--conf', type=float, default=0.38,
                   help='Fire filter threshold (painting FPs often <0.35)')
    p.add_argument('--smoke-conf', type=float, default=0.32)
    p.add_argument('--person-conf', type=float, default=0.30,
                   help='Person filter threshold (raw inference uses --model-conf)')
    p.add_argument('--statue-conf', type=float, default=0.58,
                   help='Statue filter threshold (higher = fewer wall/person FPs)')
    p.add_argument('--nms-iou', type=float, default=0.45,
                   help='Same-class NMS IoU for fire/person/smoke')
    p.add_argument('--statue-nms-iou', type=float, default=0.25,
                   help='Same-class NMS IoU for statue (lower=more aggressive merge)')
    p.add_argument('--statue-fragment-soft-iou', type=float, default=0.15,
                   help='Soft IoU for post-NMS statue fragment merge (vertical stack)')
    p.add_argument('--person-vs-statue-iou', type=float, default=0.10,
                   help='Drop person when IoU with statue >= this')
    p.add_argument('--person-vs-statue-soft-iou', type=float, default=0.015,
                   help='Weaker person↔statue IoU still drops person (nearby)')
    p.add_argument('--person-vs-statue-pad', type=float, default=0.70,
                   help='Pad ratio: person near statue (center/overlap) drops person')
    p.add_argument('--person-vs-statue-anchor-conf', type=float, default=0.08,
                   help='Weak finetune statue (>=this) can suppress person')
    p.add_argument('--person-vs-fire-iou', type=float, default=0.30,
                   help='Drop person when IoU with fire >= this')
    p.add_argument('--person-vs-fire-anchor-conf', type=float, default=0.22,
                   help='Weak fire (>=this) can suppress person even below --conf')
    p.add_argument('--person-in-frame-min-conf', type=float, default=0.78,
                   help='Min person conf when weak picture-frame cues present')
    p.add_argument('--person-confirm-frames', type=int, default=2,
                   help='Person must appear in N frames inside confirm window')
    p.add_argument('--min-person-area', type=float, default=0.012,
                   help='Min person box area / frame area')
    p.add_argument('--min-person-height', type=float, default=0.10,
                   help='Min person box height / frame height')
    p.add_argument('--max-person-top', type=float, default=0.55,
                   help='Reject if box top is below this frame-height ratio (legs-only)')
    p.add_argument('--min-person-skin', type=float, default=0.035,
                   help='Min skin-pixel ratio — statues usually fail this')
    p.add_argument('--min-person-conf-small', type=float, default=0.0,
                   help='0=off; else higher conf for small boxes')
    p.add_argument('--allow-statue-like', action='store_true',
                   help='Disable statue/picture rejection heuristics')
    p.add_argument(
        '--reject-sculptural-person',
        action=argparse.BooleanOptionalAction,
        default=True,
        help='Drop PERSON on solid 3D sculptures (grey/bronze casts); default ON',
    )
    p.add_argument(
        '--max-detect',
        action='store_true',
        help='Debug max-sensitivity for finetune: all classes, very low conf, '
             'no filters/companion (not for live demos)',
    )
    p.add_argument('--model-conf', type=float, default=0.12,
                   help='YOLO raw inference floor for fire+person (below class thresholds)')
    # 640: faster infer → less backlog/stutter; display thread stays decoupled
    p.add_argument('--imgsz', type=int, default=640)
    p.add_argument('--upscale-min-width', type=int, default=640)
    p.add_argument('--fire-confirm-frames', type=int, default=2,
                   help='Hits required in rolling window')
    p.add_argument('--smoke-confirm-frames', type=int, default=2)
    p.add_argument('--infer-fps', type=float, default=8.0,
                   help='Inference rate (lower = less CPU backlog; display stays live)')
    p.add_argument('--display-fps', type=float, default=15.0,
                   help='UI refresh rate (independent of infer; shows latest camera frame)')
    args = p.parse_args()
    if args.max_detect:
        # 파인튜닝 가중치 최대 감지 — 필터/ conf 바닥을 거의 해제
        args.generic = True
        args.allow_statue_like = True
        args.force_person_companion = False
        args.model_conf = min(args.model_conf, 0.05)
        args.conf = min(args.conf, 0.08)
        args.person_conf = min(args.person_conf, 0.08)
        args.statue_conf = min(args.statue_conf, 0.08)
        args.smoke_conf = min(args.smoke_conf, 0.08)
        args.fire_confirm_frames = 1
        args.smoke_confirm_frames = 1
        args.person_confirm_frames = 1
        args.min_person_area = 0.0
        args.min_person_height = 0.0
        args.max_person_top = 1.0
        args.min_person_skin = 0.0
        args.min_person_conf_small = 0.0
        # companion 끄고 메인 파인튜닝 모델의 fire/person/statue 전부 표시
        if not args.person_model or args.person_model == 'yolov8n.pt':
            args.person_model = ''
    return args


def draw_boxes(frame, boxes, detected: set[str]) -> None:
    for x1, y1, x2, y2, label, conf, color in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f'{label} {conf:.2f}'
        ty = y1 - 8 if y1 > 22 else min(y2 - 4, frame.shape[0] - 4)
        cv2.putText(frame, text, (x1, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    hud = (
        f'YOLO | {", ".join(sorted(detected)).upper()}'
        if detected
        else 'YOLO | monitoring (fire/person/statue)'
    )
    cv2.putText(frame, hud, (8, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 2, cv2.LINE_AA)


class RobotYoloViewer(Node):
    """카메라 토픽 1회만 구독 — 디코딩·Wi-Fi 부하 최소."""

    def __init__(
        self,
        camera_topic: str,
        model: YOLO,
        model_names: dict[int, str],
        person_model: YOLO | None,
        person_model_names: dict[int, str],
        person_model_conf: float,
        det_filter: DetectionFilter,
        model_conf: float,
        device: str,
        imgsz: int,
        upscale_min_width: int,
        infer_fps: float,
        generic: bool,
        enable_smoke: bool = False,
        companion_person_only: bool = False,
    ) -> None:
        super().__init__('robot_yolo_viewer')
        self._model = model
        self._model_names = model_names
        self._person_model = person_model
        self._person_model_names = person_model_names
        self._person_model_conf = person_model_conf
        self._generic = generic
        self._companion_wanted = (
            PERSON_ONLY_TARGET_NAMES if companion_person_only else COMPANION_TARGET_NAMES
        )
        if generic:
            self._main_classes = tuple(model_names.values())
        else:
            classes = ['fire']
            if enable_smoke:
                classes.append('smoke')
            # Hybrid: companion owns person; main still contributes statue (+ fire)
            if person_model is None and model_has_person(model_names):
                classes.append('person')
            if model_has_class(model_names, 'statue'):
                classes.append('statue')
            self._main_classes = tuple(classes)
        self._companion_class_ids = (
            target_class_ids(person_model_names, self._companion_wanted)
            if person_model
            else []
        )
        self._filter = det_filter
        self._base_filter_config = det_filter.config
        self._model_conf = model_conf
        self._device = device
        self._imgsz = imgsz
        self._upscale_min_width = upscale_min_width
        self._infer_period = 1.0 / max(infer_fps, 1.0)

        self._frame_lock = threading.Lock()
        self._overlay_lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._overlay = {'boxes': [], 'detected': set(), 'until': 0.0}
        self._last_status_time = 0.0
        self._rx_count = 0
        self._first_frame_logged = False
        self._stop = threading.Event()
        self._camera_topic = camera_topic

        self._status_pub = self.create_publisher(String, '/detect/status', 10)
        self.create_timer(5.0, self._rx_status_timer)
        if topic_is_compressed(camera_topic):
            self.create_subscription(
                CompressedImage, camera_topic, self._camera_compressed_cb, COMPRESSED_QOS
            )
            self.get_logger().info(f'Subscribe JPEG (once): {camera_topic}')
        else:
            self.create_subscription(Image, camera_topic, self._camera_cb, qos_profile_sensor_data)
            self.get_logger().info(f'Subscribe raw (once): {camera_topic}')

    def _camera_cb(self, msg: Image) -> None:
        try:
            frame = imgmsg_to_bgr(msg)
        except Exception as exc:
            self.get_logger().warn(f'decode failed: {exc}')
            return
        self._store_frame(frame)

    def _camera_compressed_cb(self, msg: CompressedImage) -> None:
        # Decode here but never block infer/display: only keep latest frame (depth=1 QoS).
        try:
            frame = compressed_imgmsg_to_bgr(msg)
        except Exception as exc:
            self.get_logger().warn(f'jpeg decode failed: {exc}')
            return
        self._store_frame(frame)

    def _store_frame(self, frame: np.ndarray) -> None:
        # Drop-oldest: overwrite pointer under lock; display/infer always take newest.
        self._rx_count += 1
        if not self._first_frame_logged:
            self._first_frame_logged = True
            h, w = frame.shape[:2]
            self.get_logger().info(f'First camera frame: {w}x{h} from {self._camera_topic}')
        with self._frame_lock:
            self._latest_frame = frame

    def _rx_status_timer(self) -> None:
        if self._rx_count == 0:
            self.get_logger().warn(
                f'No camera frames yet on {self._camera_topic} — '
                f'check ROS_DOMAIN_ID (robot=laptop), robot launch_t1_realsense.sh'
            )
        else:
            self.get_logger().info(f'Camera frames received: {self._rx_count}')

    def _publish_status(self, text: str) -> None:
        now = time.monotonic()
        if now - self._last_status_time < STATUS_DEBOUNCE_SEC:
            return
        self._last_status_time = now
        msg = String()
        msg.data = text
        self._status_pub.publish(msg)
        self.get_logger().warn(text)

    def _infer_upscale_width(self, frame_width: int) -> int:
        if frame_width <= 480:
            return max(self._upscale_min_width, 960)
        return self._upscale_min_width

    def _infer_loop(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            with self._frame_lock:
                img = self._latest_frame
            if img is None:
                time.sleep(0.05)
                continue

            # Snapshot for infer — display keeps using _latest_frame independently
            upscale_w = self._infer_upscale_width(img.shape[1])
            infer_img, scale = preprocess_for_inference(img, upscale_w)
            try:
                results = self._model(
                    infer_img,
                    imgsz=self._imgsz,
                    device=self._device,
                    conf=self._model_conf,
                    verbose=False,
                )
            except Exception as exc:
                self.get_logger().warn(f'inference: {exc}')
                continue

            raw_boxes: list[RawBox] = []
            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    cls = self._model_names.get(int(box.cls[0]), '?')
                    if cls not in self._main_classes:
                        continue
                    x1, y1, x2, y2 = (int(v / scale) for v in box.xyxy[0].tolist())
                    raw_boxes.append(
                        RawBox(cls=cls, conf=float(box.conf[0]), x1=x1, y1=y1, x2=x2, y2=y2)
                    )

            if self._person_model is not None:
                try:
                    companion_results = self._person_model(
                        infer_img,
                        imgsz=self._imgsz,
                        device=self._device,
                        conf=self._person_model_conf,
                        classes=self._companion_class_ids or None,
                        verbose=False,
                    )
                    raw_boxes.extend(
                        extract_target_boxes(
                            companion_results,
                            self._person_model_names,
                            scale,
                            self._companion_wanted,
                        )
                    )
                except Exception as exc:
                    self.get_logger().warn(f'companion inference: {exc}')
            if self._generic:
                filtered = self._filter.nms_boxes(raw_boxes)
                detected = {box.cls for box in filtered}
            else:
                self._filter.config = FilterConfig.adapt_for_resolution(
                    img.shape[1], self._base_filter_config
                )
                filtered, detected = self._filter.apply(img, raw_boxes)
            parsed = []
            for box in filtered:
                color = COLORS.get(box.cls, (0, 255, 0))
                parsed.append(
                    (box.x1, box.y1, box.x2, box.y2,
                     LABELS.get(box.cls, box.cls.upper()), box.conf, color)
                )

            with self._overlay_lock:
                # Always replace from latest inference — do not hold stale boxes
                self._overlay['boxes'] = parsed
                self._overlay['detected'] = detected
                self._overlay['until'] = time.monotonic() + OVERLAY_HOLD_SEC
                if parsed:
                    if 'fire' in detected or 'smoke' in detected:
                        self._publish_status('화재 발생!')
                    if 'person' in detected:
                        self._publish_status('사람 감지!')
                    if 'statue' in detected:
                        self._publish_status('전시물(동상) 감지!')

            elapsed = time.monotonic() - t0
            sleep_for = self._infer_period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def start_infer_thread(self) -> None:
        threading.Thread(target=self._infer_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def get_display_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            src = self._latest_frame
        if src is None:
            return self._waiting_frame()
        display = src.copy()
        with self._overlay_lock:
            boxes = list(self._overlay['boxes'])
            detected = set(self._overlay['detected'])
        draw_boxes(display, boxes, detected)
        return display

    def _waiting_frame(self) -> np.ndarray:
        frame = np.full((480, 854, 3), WAITING_BGR, dtype=np.uint8)
        lines = [
            'Waiting for robot camera...',
            f'topic: {self._camera_topic}',
            f'frames: {self._rx_count}',
            'robot: ./scripts/launch_t1_realsense.sh',
            'check: ros2 topic hz .../compressed',
        ]
        y = 80
        for line in lines:
            cv2.putText(
                frame, line, (24, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, WAITING_TEXT, 2, cv2.LINE_AA
            )
            y += 36
        return frame


def main() -> int:
    args = parse_args()
    if not args.model.is_file():
        print(f'[ERROR] Model not found: {args.model}', file=sys.stderr)
        return 1

    device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    model = YOLO(str(args.model))
    model_names = {idx: name.lower() for idx, name in model.names.items()}
    person_model = None
    person_model_names: dict[int, str] = {}
    # Hybrid when main is museum_finetune (has statue): keep yolov8n for person recall
    auto_hybrid = (
        bool(args.person_model)
        and not args.max_detect
        and model_has_class(model_names, 'statue')
        and model_has_person(model_names)
    )
    use_companion = bool(args.person_model) and (
        args.force_person_companion
        or auto_hybrid
        or not model_has_person(model_names)
    )
    companion_person_only = bool(
        use_companion and (auto_hybrid or args.force_person_companion)
    )
    if use_companion:
        loaded = load_companion_person_model(args.person_model)
        if loaded is not None:
            person_model, person_model_names = loaded
        else:
            use_companion = False
            companion_person_only = False
    companion_wanted = (
        PERSON_ONLY_TARGET_NAMES if companion_person_only else COMPANION_TARGET_NAMES
    )
    companion_ids = (
        target_class_ids(person_model_names, companion_wanted) if person_model else []
    )
    enable_smoke = bool(args.smoke)
    reject_roi = not args.allow_statue_like
    reject_sculptural = bool(args.reject_sculptural_person) and reject_roi
    det_filter = DetectionFilter(
        FilterConfig(
            fire_confidence=args.conf,
            smoke_confidence=args.smoke_conf if enable_smoke else 1.01,
            person_confidence=args.person_conf,
            statue_confidence=args.statue_conf,
            model_inference_confidence=args.model_conf,
            fire_confirm_frames=args.fire_confirm_frames,
            smoke_confirm_frames=args.smoke_confirm_frames if enable_smoke else 999,
            person_confirm_frames=args.person_confirm_frames,
            statue_confirm_frames=1,
            min_person_box_area_ratio=args.min_person_area,
            min_person_height_ratio=args.min_person_height,
            max_person_top_ratio=args.max_person_top,
            min_person_skin_ratio=args.min_person_skin,
            min_person_conf_if_small=args.min_person_conf_small,
            reject_statue_like=reject_roi,
            reject_picture_person=reject_roi,
            reject_sculpture_bust=reject_roi,
            reject_sculptural_person=reject_sculptural,
            reject_human_like_statue=reject_roi,
            nms_iou=args.nms_iou,
            statue_nms_iou=args.statue_nms_iou,
            statue_fragment_soft_iou=args.statue_fragment_soft_iou,
            reject_picture_statue=reject_roi,
            reject_flat_statue=reject_roi,
            person_vs_statue_iou=args.person_vs_statue_iou,
            person_vs_statue_soft_iou=args.person_vs_statue_soft_iou,
            person_vs_statue_pad=args.person_vs_statue_pad,
            person_vs_fire_iou=args.person_vs_fire_iou,
            person_vs_fire_anchor_conf=args.person_vs_fire_anchor_conf,
            person_vs_statue_anchor_conf=args.person_vs_statue_anchor_conf,
            person_in_frame_min_conf=args.person_in_frame_min_conf,
            class_flip_confirm_frames=2,
        )
    )
    model_conf = det_filter.model_conf_floor()
    if args.generic or args.max_detect:
        model_conf = float(args.model_conf)
    person_infer_conf = model_conf

    print(f'[INFO] Robot YOLO viewer — single subscribe, minimal lag')
    print(f'[INFO] Camera topic: {args.camera_topic}')
    print(f'[INFO] Model: {args.model}  device: {device}')
    if args.max_detect:
        print('[INFO] MAX-DETECT on — all classes, conf floor ~0.05, filters off')
    print(f'[INFO] Targets: fire' + ('+smoke' if enable_smoke else '') + '+person+statue')
    print(
        f'[INFO] DetectionFilter: '
        f'{"BYPASSED (generic/max-detect)" if (args.generic or args.max_detect) else "ON"} '
        f'| statue/picture/sculptural reject='
        f'{"on" if reject_roi else "off"}/'
        f'{"on" if reject_sculptural else "off"}'
    )
    print(
        f'[INFO] Conf floors: fire>={args.conf:.2f} person>={args.person_conf:.2f} '
        f'statue>={args.statue_conf:.2f}  frame_person>={args.person_in_frame_min_conf:.2f}  '
        f'NMS iou={args.nms_iou:.2f} '
        f'statue_nms={args.statue_nms_iou:.2f} frag_soft={args.statue_fragment_soft_iou:.2f} '
        f'person↔statue={args.person_vs_statue_iou:.2f}/'
        f'soft={args.person_vs_statue_soft_iou:.2f}/pad={args.person_vs_statue_pad:.2f} '
        f'statue_anchor>={args.person_vs_statue_anchor_conf:.2f} '
        f'person↔fire={args.person_vs_fire_iou:.2f} '
        f'sculptural_reject={"on" if reject_sculptural else "off"}'
    )
    if args.generic:
        print(f'[INFO] Generic classes: {list(model_names.values())}')
    if person_model is not None:
        mode = 'person-only hybrid' if companion_person_only else 'fire/person/statue'
        print(
            f'[INFO] Companion model: {args.person_model} ({mode}) '
            f'class_ids={companion_ids} names={list(person_model_names.values())} '
            f'(infer>={person_infer_conf:.2f})'
        )
        if companion_person_only:
            print('[INFO] Main: fire/statue from finetune; person from yolov8n')
    elif model_has_person(model_names):
        print(
            f'[INFO] Person/statue from main model '
            f'person_ids={person_class_ids(model_names)} '
            f'has_statue={model_has_class(model_names, "statue")}'
        )
    else:
        print('[WARN] Person companion model OFF — person will not detect '
              '(museum_fire_smoke.pt has fire/smoke only)')
    print(
        f'[INFO] infer {args.infer_fps}Hz imgsz={args.imgsz} '
        f'upscale>={args.upscale_min_width}px  display {args.display_fps}Hz'
    )

    dummy = np.zeros((240, 320, 3), dtype=np.uint8)
    model(dummy, imgsz=args.imgsz, device=device, conf=model_conf, verbose=False)
    if person_model is not None:
        person_model(
            dummy,
            imgsz=args.imgsz,
            device=device,
            conf=person_infer_conf,
            classes=companion_ids or None,
            verbose=False,
        )

    rclpy.init()
    node = RobotYoloViewer(
        args.camera_topic,
        model,
        model_names,
        person_model,
        person_model_names,
        person_infer_conf,
        det_filter,
        model_conf,
        device,
        args.imgsz,
        args.upscale_min_width,
        args.infer_fps,
        args.generic,
        enable_smoke=enable_smoke,
        companion_person_only=companion_person_only,
    )
    node.start_infer_thread()

    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(node)
    threading.Thread(target=executor.spin, daemon=True).start()

    win = 'Robot YOLO (Q=quit)'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win, 854, 480)
    period = 1.0 / max(args.display_fps, 1.0)

    try:
        while rclpy.ok():
            frame = node.get_display_frame()
            cv2.imshow(win, frame)
            if cv2.waitKey(1) & 0xFF in (ord('q'), ord('Q')):
                break
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
