"""Real-time fire/smoke and person detection using YOLO."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Dict, List, Optional, Set, Tuple

import cv2
import json
import rclpy
from cv_bridge import CvBridge, CvBridgeError
from museum_patrol_nodes.detection_filters import DetectionFilter, FilterConfig, RawBox
from museum_patrol_nodes.image_utils import (
    compressed_imgmsg_to_bgr,
    imgmsg_to_bgr,
    preprocess_for_inference,
    topic_is_compressed,
)
from museum_patrol_nodes.robot_topics import t1_color_raw
from museum_patrol_nodes.yolo_model_utils import (
    COMPANION_TARGET_NAMES,
    PERSON_ONLY_TARGET_NAMES,
    extract_target_boxes,
    load_companion_person_model,
    model_has_class,
    model_has_person,
    target_class_ids,
)
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image
from std_msgs.msg import Header, String

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

try:
    from ultralytics import YOLO
except ImportError as exc:
    raise ImportError(
        'ultralytics is required. Install with: pip install ultralytics'
    ) from exc


TARGET_CLASSES = frozenset({'fire', 'smoke', 'person', 'statue'})

CLASS_ALIASES = {
    'fire': 'fire',
    'flame': 'fire',
    '불꽃': 'fire',
    'smoke': 'smoke',
    '연기': 'smoke',
    'person': 'person',
    'people': 'person',
    'human': 'person',
    'statue': 'statue',
    '동상': 'statue',
}

CLASS_LABELS_DISPLAY = {
    'fire': 'FIRE',
    'smoke': 'SMOKE',
    'person': 'PERSON',
    'statue': 'STATUE',
}

CLASS_COLORS_BGR = {
    'fire': (0, 0, 255),
    'smoke': (128, 128, 128),
    'person': (255, 128, 0),
    'statue': (255, 0, 255),
}

STATUS_MESSAGES = {
    'fire': '화재 발생!',
    'smoke': '화재 발생!',
    'person': '사람 감지!',
    'statue': '전시물(동상) 감지!',
}

COMPRESSED_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.VOLATILE,
)


@dataclass(frozen=True)
class BoxOverlay:
    x1: int
    y1: int
    x2: int
    y2: int
    caption: str
    color: Tuple[int, int, int]


class YoloDetectorNode(Node):
    """Subscribe to camera images, run YOLO in a worker thread, publish at steady FPS."""

    def __init__(self) -> None:
        super().__init__('yolo_detector')

        self.declare_parameter('model_path', 'yolov8n.pt')
        self.declare_parameter('confidence_threshold', 0.25)
        self.declare_parameter('fire_confidence_threshold', 0.38)
        self.declare_parameter('smoke_confidence_threshold', 0.45)
        self.declare_parameter('person_confidence_threshold', 0.55)
        self.declare_parameter('fire_confirm_frames', 2)
        self.declare_parameter('smoke_confirm_frames', 3)
        self.declare_parameter('person_confirm_frames', 3)
        self.declare_parameter('min_person_box_area_ratio', 0.04)
        self.declare_parameter('min_person_height_ratio', 0.18)
        self.declare_parameter('person_model_path', 'yolov8n.pt')
        self.declare_parameter('force_person_companion', True)
        self.declare_parameter('statue_confidence_threshold', 0.55)
        self.declare_parameter('nms_iou', 0.45)
        self.declare_parameter('statue_nms_iou', 0.25)
        self.declare_parameter('statue_fragment_soft_iou', 0.15)
        self.declare_parameter('person_vs_statue_iou', 0.20)
        self.declare_parameter('person_vs_statue_soft_iou', 0.05)
        self.declare_parameter('person_vs_statue_pad', 0.35)
        self.declare_parameter('person_vs_statue_anchor_conf', 0.18)
        self.declare_parameter('person_vs_fire_iou', 0.30)
        self.declare_parameter('person_vs_fire_anchor_conf', 0.22)
        self.declare_parameter('reject_sculptural_person', True)
        self.declare_parameter('image_topic', t1_color_raw())
        self.declare_parameter('detect_image_topic', '/detect/image_raw')
        self.declare_parameter('status_topic', '/detect/status')
        self.declare_parameter('status_debounce_sec', 2.0)
        self.declare_parameter('detection_mode', 'museum')
        self.declare_parameter('inference_imgsz', 416)
        self.declare_parameter('inference_fps', 10.0)
        self.declare_parameter('publish_fps', 30.0)
        self.declare_parameter('model_inference_confidence', 0.12)
        self.declare_parameter('upscale_min_width', 640)
        self.declare_parameter('overlay_topic', '/detect/overlay')
        self.declare_parameter('publish_detect_image', False)

        model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.confidence_threshold = (
            self.get_parameter('confidence_threshold').get_parameter_value().double_value
        )
        fire_conf = self.get_parameter('fire_confidence_threshold').get_parameter_value().double_value
        smoke_conf = self.get_parameter('smoke_confidence_threshold').get_parameter_value().double_value
        person_conf = self.get_parameter('person_confidence_threshold').get_parameter_value().double_value
        statue_conf = self.get_parameter(
            'statue_confidence_threshold'
        ).get_parameter_value().double_value
        infer_conf = self.get_parameter('model_inference_confidence').get_parameter_value().double_value
        person_model_path = (
            self.get_parameter('person_model_path').get_parameter_value().string_value
        )
        force_person_companion = (
            self.get_parameter('force_person_companion').get_parameter_value().bool_value
        )
        nms_iou = self.get_parameter('nms_iou').get_parameter_value().double_value
        statue_nms_iou = self.get_parameter('statue_nms_iou').get_parameter_value().double_value
        statue_fragment_soft_iou = self.get_parameter(
            'statue_fragment_soft_iou'
        ).get_parameter_value().double_value
        person_vs_statue_iou = self.get_parameter(
            'person_vs_statue_iou'
        ).get_parameter_value().double_value
        person_vs_statue_soft_iou = self.get_parameter(
            'person_vs_statue_soft_iou'
        ).get_parameter_value().double_value
        person_vs_statue_pad = self.get_parameter(
            'person_vs_statue_pad'
        ).get_parameter_value().double_value
        person_vs_statue_anchor_conf = self.get_parameter(
            'person_vs_statue_anchor_conf'
        ).get_parameter_value().double_value
        person_vs_fire_iou = self.get_parameter(
            'person_vs_fire_iou'
        ).get_parameter_value().double_value
        person_vs_fire_anchor_conf = self.get_parameter(
            'person_vs_fire_anchor_conf'
        ).get_parameter_value().double_value
        reject_sculptural_person = self.get_parameter(
            'reject_sculptural_person'
        ).get_parameter_value().bool_value
        self._filter = DetectionFilter(
            FilterConfig(
                fire_confidence=fire_conf,
                smoke_confidence=smoke_conf,
                person_confidence=person_conf,
                statue_confidence=statue_conf,
                model_inference_confidence=infer_conf,
                fire_confirm_frames=int(
                    self.get_parameter('fire_confirm_frames').get_parameter_value().integer_value
                ),
                smoke_confirm_frames=int(
                    self.get_parameter('smoke_confirm_frames').get_parameter_value().integer_value
                ),
                person_confirm_frames=int(
                    self.get_parameter('person_confirm_frames').get_parameter_value().integer_value
                ),
                min_person_box_area_ratio=float(
                    self.get_parameter('min_person_box_area_ratio').get_parameter_value().double_value
                ),
                min_person_height_ratio=float(
                    self.get_parameter('min_person_height_ratio').get_parameter_value().double_value
                ),
                nms_iou=nms_iou,
                statue_nms_iou=statue_nms_iou,
                statue_fragment_soft_iou=statue_fragment_soft_iou,
                reject_sculptural_person=reject_sculptural_person,
                person_vs_statue_iou=person_vs_statue_iou,
                person_vs_statue_soft_iou=person_vs_statue_soft_iou,
                person_vs_statue_pad=person_vs_statue_pad,
                person_vs_fire_iou=person_vs_fire_iou,
                person_vs_fire_anchor_conf=person_vs_fire_anchor_conf,
                person_vs_statue_anchor_conf=person_vs_statue_anchor_conf,
            )
        )
        self._base_filter_config = self._filter.config
        model_conf = min(infer_conf, self.confidence_threshold)
        self._model_conf = model_conf
        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        detect_image_topic = (
            self.get_parameter('detect_image_topic').get_parameter_value().string_value
        )
        status_topic = self.get_parameter('status_topic').get_parameter_value().string_value
        self.status_debounce_sec = (
            self.get_parameter('status_debounce_sec').get_parameter_value().double_value
        )
        self.detection_mode = (
            self.get_parameter('detection_mode').get_parameter_value().string_value
        ).lower()
        self.inference_imgsz = int(
            self.get_parameter('inference_imgsz').get_parameter_value().integer_value
        )
        self.upscale_min_width = int(
            self.get_parameter('upscale_min_width').get_parameter_value().integer_value
        )
        self.inference_period = 1.0 / max(
            self.get_parameter('inference_fps').get_parameter_value().double_value,
            1.0,
        )
        publish_fps = max(
            self.get_parameter('publish_fps').get_parameter_value().double_value,
            1.0,
        )
        self.publish_detect_image = (
            self.get_parameter('publish_detect_image').get_parameter_value().bool_value
        )
        overlay_topic = (
            self.get_parameter('overlay_topic').get_parameter_value().string_value
        )

        self._device = 'cpu'
        if torch is not None and torch.cuda.is_available():
            self._device = 'cuda:0'

        self.get_logger().info(f'Loading YOLO model: {model_path}')
        self.model = YOLO(model_path)
        self.model_names = {idx: name.lower() for idx, name in self.model.names.items()}
        self._person_model = None
        self._person_model_names: Dict[int, str] = {}
        self._companion_class_ids: List[int] = []
        self._companion_wanted = COMPANION_TARGET_NAMES
        # Companion YOLO uses low inference floor; FilterConfig applies per-class conf
        self._person_model_conf = model_conf
        auto_hybrid = (
            force_person_companion
            and bool(person_model_path.strip())
            and model_has_class(self.model_names, 'statue')
            and model_has_person(self.model_names)
        )
        use_companion = bool(person_model_path.strip()) and (
            auto_hybrid or not model_has_person(self.model_names)
        )
        if use_companion:
            loaded = load_companion_person_model(person_model_path)
            if loaded is not None:
                self._person_model, self._person_model_names = loaded
                self._companion_wanted = (
                    PERSON_ONLY_TARGET_NAMES if auto_hybrid else COMPANION_TARGET_NAMES
                )
                self._companion_class_ids = target_class_ids(
                    self._person_model_names, self._companion_wanted
                )
                mode = 'person-only hybrid' if auto_hybrid else 'fire/person/statue'
                self.get_logger().info(
                    f'Companion model: {person_model_path} ({mode}) '
                    f'(infer>={self._person_model_conf:.2f}, filter>={person_conf:.2f}; '
                    f'class_ids={self._companion_class_ids} '
                    f'names={list(self._person_model_names.values())})'
                )
        elif model_has_person(self.model_names):
            self.get_logger().info('Main model already includes person class')
        self.get_logger().info(f'Model classes: {list(self.model.names.values())}')
        self.get_logger().info(f'Inference device: {self._device}')

        # GPU 워밍업 (첫 프레임 끊김 방지)
        if self._device != 'cpu':
            import numpy as np
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model(
                dummy,
                imgsz=self.inference_imgsz,
                device=self._device,
                conf=self._model_conf,
                verbose=False,
            )
            if self._person_model is not None:
                self._person_model(
                    dummy,
                    imgsz=self.inference_imgsz,
                    device=self._device,
                    conf=self._person_model_conf,
                    classes=self._companion_class_ids or None,
                    verbose=False,
                )

        self.bridge = CvBridge()
        self._last_status_time: Dict[str, float] = {}
        self._frame_queue: Queue[Tuple[object, Header]] = Queue(maxsize=1)
        self._preview_lock = threading.Lock()
        self._overlay_lock = threading.Lock()
        self._latest_frame = None
        self._latest_header: Optional[Header] = None
        self._overlay_boxes: List[BoxOverlay] = []
        self._overlay_detected: Set[str] = set()
        self._overlay_until = 0.0
        self._overlay_hold_sec = 0.0  # no linger — clear when detection gone
        self._pending_status: Set[str] = set()
        self._frames_received = 0
        self._last_rx_log = time.monotonic()
        self._worker_stop = threading.Event()
        self._worker = threading.Thread(target=self._inference_worker, daemon=True)
        self._worker.start()

        if topic_is_compressed(image_topic):
            self.image_sub = self.create_subscription(
                CompressedImage,
                image_topic,
                self.compressed_image_callback,
                COMPRESSED_QOS,
            )
        else:
            self.image_sub = self.create_subscription(
                Image,
                image_topic,
                self.image_callback,
                qos_profile_sensor_data,
            )
        self.image_pub = self.create_publisher(
            Image, detect_image_topic, qos_profile_sensor_data
        )
        self.overlay_pub = self.create_publisher(String, overlay_topic, 10)
        self.status_pub = self.create_publisher(String, status_topic, 10)
        if self.publish_detect_image:
            self.create_timer(1.0 / publish_fps, self._publish_timer_cb)

        mode = 'image+overlay' if self.publish_detect_image else 'overlay-only (robot viewer)'
        self.get_logger().info(
            f'YOLO detector ready — mode: {self.detection_mode}, output: {mode}, '
            f'inference: {self.inference_imgsz}px @ {1.0 / self.inference_period:.1f} Hz, '
            f'conf fire>={fire_conf:.2f} smoke>={smoke_conf:.2f} person>={person_conf:.2f}, '
            f'confirm fire={self._filter.config.fire_confirm_frames}f '
            f'smoke={self._filter.config.smoke_confirm_frames}f '
            f'person={self._filter.config.person_confirm_frames}f, '
            f'subscribe: {image_topic}, overlay: {overlay_topic}'
        )
        if self.publish_detect_image:
            self.get_logger().info(f'Annotated image: {detect_image_topic} @ {publish_fps:.1f} Hz')

    def _normalize_class(self, raw_name: str) -> str:
        name = raw_name.lower().strip()
        return CLASS_ALIASES.get(name, name)

    def _publish_status_if_needed(self, normalized_class: str) -> None:
        if normalized_class not in STATUS_MESSAGES:
            return

        now = time.monotonic()
        last = self._last_status_time.get(normalized_class, 0.0)
        if now - last < self.status_debounce_sec:
            return

        message = STATUS_MESSAGES[normalized_class]
        status_msg = String()
        status_msg.data = message
        self.status_pub.publish(status_msg)
        self._last_status_time[normalized_class] = now
        self.get_logger().warn(message)

    def _enqueue_frame(self, cv_image, header) -> None:
        self._frames_received += 1
        now = time.monotonic()
        if now - self._last_rx_log >= 5.0:
            self.get_logger().info(f'Camera frames received: {self._frames_received}')
            self._last_rx_log = now

        with self._preview_lock:
            if self.publish_detect_image:
                self._latest_frame = cv_image
                self._latest_header = header

        packet = (cv_image, header)
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except Empty:
                pass
        try:
            self._frame_queue.put_nowait(packet)
        except Exception:
            pass

    def image_callback(self, msg: Image) -> None:
        try:
            cv_image = imgmsg_to_bgr(msg)
        except Exception as exc:
            self.get_logger().error(
                f'image decode failed ({msg.encoding} {msg.width}x{msg.height} step={msg.step}): {exc}'
            )
            return
        self._enqueue_frame(cv_image, msg.header)

    def compressed_image_callback(self, msg: CompressedImage) -> None:
        try:
            cv_image = compressed_imgmsg_to_bgr(msg)
        except Exception as exc:
            self.get_logger().error(f'jpeg decode failed: {exc}')
            return
        self._enqueue_frame(cv_image, msg.header)

    def _extract_raw_boxes(self, results) -> List[RawBox]:
        # Hybrid: companion owns person; main still emits fire/smoke/statue
        main_classes = ['fire', 'smoke']
        if self._person_model is None and model_has_person(self.model_names):
            main_classes.append('person')
        if model_has_class(self.model_names, 'statue'):
            main_classes.append('statue')
        main_classes_t = tuple(main_classes)
        raw: List[RawBox] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0])
                raw_name = self.model_names.get(class_id, str(class_id))
                normalized = self._normalize_class(raw_name)
                if self.detection_mode != 'all' and normalized not in TARGET_CLASSES:
                    continue
                if normalized not in main_classes_t:
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                raw.append(
                    RawBox(
                        cls=normalized,
                        conf=float(box.conf[0]),
                        x1=x1,
                        y1=y1,
                        x2=x2,
                        y2=y2,
                    )
                )
        return raw

    def _to_overlay(self, box: RawBox) -> BoxOverlay:
        if box.cls in CLASS_COLORS_BGR:
            color = CLASS_COLORS_BGR[box.cls]
            label = CLASS_LABELS_DISPLAY[box.cls]
        else:
            color = (0, 255, 0)
            label = box.cls.upper()
        return BoxOverlay(
            box.x1,
            box.y1,
            box.x2,
            box.y2,
            f'{label} {box.conf:.2f}',
            color,
        )

    def _publish_overlay_msg(self, boxes: List[RawBox], detected: Set[str]) -> None:
        payload = {
            'detected': sorted(detected),
            'boxes': [
                {
                    'cls': box.cls,
                    'conf': round(box.conf, 3),
                    'xyxy': [box.x1, box.y1, box.x2, box.y2],
                }
                for box in boxes
            ],
        }
        msg = String()
        msg.data = json.dumps(payload)
        self.overlay_pub.publish(msg)

    def _flush_status(self, pending: Set[str]) -> None:
        if 'fire' in pending or 'smoke' in pending:
            self._publish_status_if_needed('fire')
        if 'person' in pending:
            self._publish_status_if_needed('person')

    def _parse_boxes_from_raw(
        self, cv_image, raw_boxes: List[RawBox]
    ) -> Tuple[List[RawBox], List[BoxOverlay], Set[str]]:
        self._filter.config = FilterConfig.adapt_for_resolution(
            cv_image.shape[1], self._base_filter_config
        )
        filtered, detected = self._filter.apply(cv_image, raw_boxes)
        overlays = [self._to_overlay(b) for b in filtered]
        return filtered, overlays, detected

    def _parse_boxes(self, cv_image, results) -> Tuple[List[RawBox], List[BoxOverlay], Set[str]]:
        raw_boxes = self._extract_raw_boxes(results)
        return self._parse_boxes_from_raw(cv_image, raw_boxes)

    def _draw_overlays(self, frame, boxes: List[BoxOverlay], detected: Set[str]) -> None:
        for box in boxes:
            cv2.rectangle(frame, (box.x1, box.y1), (box.x2, box.y2), box.color, 2)
            text_y = box.y1 - 8 if box.y1 > 22 else min(box.y2 - 4, frame.shape[0] - 4)
            cv2.putText(
                frame,
                box.caption,
                (box.x1, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                box.color,
                2,
                cv2.LINE_AA,
            )

        hud = (
            f'YOLO | {", ".join(sorted(detected)).upper()}'
            if detected
            else 'YOLO | monitoring (fire/smoke/person)'
        )
        cv2.putText(
            frame,
            hud,
            (8, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 220, 0),
            2,
            cv2.LINE_AA,
        )

    def _inference_worker(self) -> None:
        while not self._worker_stop.is_set():
            loop_start = time.monotonic()
            try:
                cv_image, _header = self._frame_queue.get(timeout=0.1)
            except Empty:
                continue

            while not self._frame_queue.empty():
                try:
                    cv_image, _header = self._frame_queue.get_nowait()
                except Empty:
                    break

            try:
                upscale_w = self.upscale_min_width
                if cv_image.shape[1] <= 480:
                    upscale_w = max(self.upscale_min_width, 960)
                infer_image, scale = preprocess_for_inference(cv_image, upscale_w)
                results = self.model(
                    infer_image,
                    imgsz=self.inference_imgsz,
                    device=self._device,
                    conf=self._model_conf,
                    verbose=False,
                )
                if scale != 1.0:
                    for result in results:
                        if result.boxes is None:
                            continue
                        result.boxes.xyxy /= scale
                raw_boxes = self._extract_raw_boxes(results)
                if self._person_model is not None:
                    companion_results = self._person_model(
                        infer_image,
                        imgsz=self.inference_imgsz,
                        device=self._device,
                        conf=self._person_model_conf,
                        classes=self._companion_class_ids or None,
                        verbose=False,
                    )
                    if scale != 1.0:
                        for result in companion_results:
                            if result.boxes is None:
                                continue
                            result.boxes.xyxy /= scale
                    raw_boxes.extend(
                        extract_target_boxes(
                            companion_results,
                            self._person_model_names,
                            wanted=self._companion_wanted,
                        )
                    )
                filtered, boxes, detected = self._parse_boxes_from_raw(cv_image, raw_boxes)
            except Exception as exc:
                self.get_logger().error(f'YOLO inference failed: {exc}')
                continue

            now = time.monotonic()
            pending: Set[str] = set()
            with self._overlay_lock:
                # Always replace from latest inference — do not hold stale boxes
                self._overlay_boxes = boxes
                self._overlay_detected = detected
                self._overlay_until = now + self._overlay_hold_sec
                if boxes and detected:
                    self._pending_status.update(detected)
                    self.get_logger().info(
                        f'Confirmed: {sorted(detected)} '
                        f'(fire>={self._filter.config.fire_confidence:.2f}, '
                        f'smoke>={self._filter.config.smoke_confidence:.2f}, '
                        f'person>={self._filter.config.person_confidence:.2f})'
                    )
                pending = set(self._pending_status)
                self._pending_status.clear()

            self._publish_overlay_msg(filtered, detected)
            self._flush_status(pending)

            elapsed = time.monotonic() - loop_start
            sleep_for = self.inference_period - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _publish_timer_cb(self) -> None:
        if not self.publish_detect_image:
            return
        with self._preview_lock:
            if self._latest_frame is None or self._latest_header is None:
                return
            frame = self._latest_frame.copy()
            header = self._latest_header

        with self._overlay_lock:
            boxes = list(self._overlay_boxes)
            detected = set(self._overlay_detected)

        self._draw_overlays(frame, boxes, detected)

        try:
            out_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            out_msg.header = header
            out_msg.header.stamp = self.get_clock().now().to_msg()
            self.image_pub.publish(out_msg)
        except CvBridgeError as exc:
            self.get_logger().error(f'Failed to publish annotated image: {exc}')
            return

    def destroy_node(self) -> None:
        self._worker_stop.set()
        if self._worker.is_alive():
            self._worker.join(timeout=2.0)
        super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = YoloDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
