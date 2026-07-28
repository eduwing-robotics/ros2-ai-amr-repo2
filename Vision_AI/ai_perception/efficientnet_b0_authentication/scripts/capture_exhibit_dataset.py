#!/usr/bin/env python3
"""Exhibit dataset capture for painting authenticity (Phase 1 — bacchus_and_ariadne MVP).

Captures RGB (+ optional depth median) into datasets/museum_auth_dataset/.
Does NOT train, infer, or touch YOLO nodes.

Dataset root (under robot_project):
  datasets/museum_auth_dataset/
    raw/genuine/<session>/          # full RGB frames
    raw/fake/<fake_id>/<session>/
    crops/genuine/                  # ROI crops (session in filename)
    crops/fake/<fake_id>/
    metadata/captures.jsonl         # one JSON object per shot
    metadata/<stem>.json            # per-shot copy

Pre:
  Robot:  ./scripts/launch_t1_realsense.sh
  Laptop: source ./scripts/camera_laptop_env.sh

Usage:
  # Live ROI preview (nudge with keys, save YAML with o/Enter)
  # Prefer a normal Ubuntu terminal if Cursor IDE terminal shows no window.
  python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py preview --roi 100 80 320 220

  # No GUI: save one annotated JPEG and open it in the file browser
  python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py snap --roi 100 80 320 220

  # Capture N frames
  python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py capture \\
    --label genuine --session session_01 --count 5 --interval 0.4 \\
    --roi 100 80 320 220

  # Or via wrapper (sources camera_laptop_env.sh):
  ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh preview
  ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh snap
  ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh capture --label genuine --session session_01 --count 5
"""
from __future__ import annotations

import argparse
import json
import os
import select
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# OpenCV Qt: Cursor/일부 터미널에서 창 안 뜨는 문제 완화 (view_yolo_cv.py 와 동일)
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import cv2
import numpy as np
import rclpy
import yaml
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from sensor_msgs.msg import CompressedImage, Image

# Match jpeg_camera_compressor_node (Wi-Fi JPEG). Wrong durability = no frames + frozen GUI.
CAMERA_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
    durability=DurabilityPolicy.VOLATILE,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "ai_perception" / "efficientnet_b0_authentication" / "datasets" / "museum_auth_dataset"
DEFAULT_ROI_YAML = REPO_ROOT / "ai_perception" / "efficientnet_b0_authentication" / "config" / "painting_auth_bacchus.yaml"
DEFAULT_EXHIBIT_ID = "bacchus_and_ariadne"

DEFAULT_COMPRESSED = os.environ.get(
    "T1_CAMERA_COMPRESSED",
    "/tb3_1/camera/color/image_raw/compressed",
)
DEFAULT_RAW = os.environ.get(
    "T1_CAMERA_RAW",
    "/tb3_1/camera/color/image_raw",
)
DEFAULT_DEPTH = "/tb3_1/camera/aligned_depth_to_color/image_raw"

VALID_LABELS = ("genuine", "fake_01", "fake_02", "fake_03", "fake_04")

# Wait this many distinct RGB frames before first save (reduce startup blur/identical frames).
STABLE_FRAME_COUNT = 3


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]


def _parse_roi(values: list[int] | None) -> tuple[int, int, int, int] | None:
    if values is None:
        return None
    if len(values) != 4:
        raise argparse.ArgumentTypeError("--roi needs exactly 4 ints: x1 y1 x2 y2")
    x1, y1, x2, y2 = (int(v) for v in values)
    return x1, y1, x2, y2


def load_roi_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def roi_from_config(cfg: dict[str, Any]) -> tuple[int, int, int, int] | None:
    roi = cfg.get("roi")
    if not isinstance(roi, dict):
        return None
    try:
        return int(roi["x1"]), int(roi["y1"]), int(roi["x2"]), int(roi["y2"])
    except (KeyError, TypeError, ValueError):
        return None


def save_roi_yaml(
    path: Path,
    *,
    exhibit_id: str,
    roi: tuple[int, int, int, int],
    existing: dict[str, Any] | None = None,
) -> None:
    x1, y1, x2, y2 = roi
    data: dict[str, Any] = dict(existing or {})
    data["exhibit_id"] = exhibit_id
    data["roi"] = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    data.setdefault("reference_depth_m", None)
    data.setdefault("rgb_topic_compressed", DEFAULT_COMPRESSED)
    data.setdefault("rgb_topic_raw", DEFAULT_RAW)
    data.setdefault("depth_topic", DEFAULT_DEPTH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def validate_roi(roi: tuple[int, int, int, int], width: int, height: int) -> None:
    x1, y1, x2, y2 = roi
    if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
        raise ValueError(
            f"ROI {roi} outside image bounds {width}x{height} "
            f"(need 0 <= x1 < x2 <= {width}, 0 <= y1 < y2 <= {height})"
        )
    if x1 >= x2 or y1 >= y2:
        raise ValueError(f"ROI {roi} invalid: require x1 < x2 and y1 < y2")
    if (x2 - x1) < 8 or (y2 - y1) < 8:
        raise ValueError(f"ROI {roi} too small (min 8x8 px)")


def label_paths(label: str) -> tuple[str, Path, Path]:
    """Return (label_tag, raw_rel, crop_rel) under dataset root."""
    if label == "genuine":
        return "genuine", Path("genuine"), Path("genuine")
    if label.startswith("fake_"):
        return label, Path("fake") / label, Path("fake") / label
    raise ValueError(f"unsupported label {label!r}; expected one of {VALID_LABELS}")


def depth_median_m(depth: np.ndarray | None, roi: tuple[int, int, int, int]) -> float | None:
    if depth is None:
        return None
    x1, y1, x2, y2 = roi
    patch = depth[y1:y2, x1:x2]
    if patch.size == 0:
        return None
    # RealSense aligned depth: typically uint16 millimetres; 0 = invalid.
    valid = patch[patch > 0]
    if valid.size == 0:
        return None
    med = float(np.median(valid.astype(np.float64)))
    # Heuristic: values >> 20 are mm; small floats already metres.
    if med > 20.0:
        med /= 1000.0
    return round(med, 4)


class CameraBuffer(Node):
    """Latest RGB (+ optional depth) with thread-safe access."""

    def __init__(
        self,
        *,
        rgb_topic: str,
        compressed: bool,
        depth_topic: str | None,
        enable_depth: bool,
    ) -> None:
        super().__init__("capture_exhibit_dataset")
        self.bridge = CvBridge()
        self._lock = threading.Lock()
        self._bgr: np.ndarray | None = None
        self._depth: np.ndarray | None = None
        self._rgb_count = 0
        self._depth_count = 0
        self.rgb_topic = rgb_topic
        self.depth_topic = depth_topic if enable_depth else None
        self.depth_enabled = bool(enable_depth and depth_topic)

        qos = CAMERA_QOS
        if compressed:
            self.create_subscription(CompressedImage, rgb_topic, self._on_compressed, qos)
        else:
            self.create_subscription(Image, rgb_topic, self._on_raw, qos)

        if self.depth_enabled:
            self.create_subscription(Image, self.depth_topic, self._on_depth, qos_profile_sensor_data)
            self.get_logger().info(f"depth topic={self.depth_topic} (optional)")
        else:
            self.get_logger().info("depth disabled — depth_median_m will be null")

        self.get_logger().info(
            f"rgb topic={rgb_topic} compressed={compressed} qos=BEST_EFFORT/VOLATILE"
        )

    def _on_compressed(self, msg: CompressedImage) -> None:
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return
        with self._lock:
            self._bgr = bgr
            self._rgb_count += 1

    def _on_raw(self, msg: Image) -> None:
        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        with self._lock:
            self._bgr = bgr
            self._rgb_count += 1

    def _on_depth(self, msg: Image) -> None:
        try:
            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        except Exception as exc:  # noqa: BLE001 — keep RGB capture alive
            self.get_logger().warn(f"depth decode failed: {exc}")
            return
        with self._lock:
            self._depth = depth
            self._depth_count += 1

    def snapshot(self) -> tuple[np.ndarray | None, np.ndarray | None, int]:
        with self._lock:
            bgr = None if self._bgr is None else self._bgr.copy()
            depth = None if self._depth is None else self._depth.copy()
            return bgr, depth, self._rgb_count

    def wait_for_frame(
        self,
        timeout_s: float = 30.0,
        *,
        pump_gui: Any | None = None,
    ) -> np.ndarray:
        deadline = time.time() + timeout_s
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            # Keep OpenCV/Qt responsive while blocking for first frame.
            if callable(pump_gui):
                pump_gui()
            else:
                # Harmless if no window; prevents "Not Responding" when one exists.
                cv2.waitKey(1)
            bgr, _, count = self.snapshot()
            if bgr is not None and count >= 1:
                return bgr
        raise RuntimeError(
            f"no RGB frames on {self.rgb_topic} within {timeout_s:.0f}s — "
            "check camera_laptop_env.sh / launch_t1_realsense.sh "
            "(QoS must be BEST_EFFORT + VOLATILE for JPEG compressor)"
        )

    def wait_stable(
        self,
        n: int = STABLE_FRAME_COUNT,
        timeout_s: float = 30.0,
        *,
        pump_gui: Any | None = None,
    ) -> np.ndarray:
        deadline = time.time() + timeout_s
        target = None
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            if callable(pump_gui):
                pump_gui()
            else:
                cv2.waitKey(1)
            bgr, _, count = self.snapshot()
            if bgr is None:
                continue
            if target is None:
                target = count + max(n - 1, 0)
            if count >= target:
                return bgr
        raise RuntimeError(f"camera did not deliver {n} stable frames in time")


def _clamp_roi(roi: list[int], w: int, h: int) -> list[int]:
    x1, y1, x2, y2 = roi
    x1 = max(0, min(x1, w - 2))
    y1 = max(0, min(y1, h - 2))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))
    return [x1, y1, x2, y2]


def _nudge_roi(roi: list[int], key: int, w: int, h: int, step: int = 8) -> list[int]:
    """Adjust ROI from a keycode. Supports WASD and OpenCV/Qt arrow keycodes."""
    x1, y1, x2, y2 = roi
    rw, rh = x2 - x1, y2 - y1
    # Normalize Qt/OpenCV extended arrow codes to 81..84 range used by highgui.
    key_low = key & 0xFF
    arrows = {
        81: "left",
        82: "up",
        83: "right",
        84: "down",
        2: "left",
        0: "up",
        3: "right",
        1: "down",
    }
    # Common waitKeyEx values on Linux Qt builds
    if key in (2424832, 65361):
        arrows_hit = "left"
    elif key in (2490368, 65362):
        arrows_hit = "up"
    elif key in (2555904, 65363):
        arrows_hit = "right"
    elif key in (2621440, 65364):
        arrows_hit = "down"
    else:
        arrows_hit = arrows.get(key_low)

    # Move (WASD + arrows). Note: 's' moves down; save is 'o' / Enter.
    if key_low in (ord("a"), ord("A")) or arrows_hit == "left":
        x1 -= step
        x2 -= step
    elif key_low in (ord("d"), ord("D")) or arrows_hit == "right":
        x1 += step
        x2 += step
    elif key_low in (ord("w"), ord("W")) or arrows_hit == "up":
        y1 -= step
        y2 -= step
    elif key_low in (ord("s"), ord("S")) or arrows_hit == "down":
        y1 += step
        y2 += step
    # Resize both axes
    elif key_low in (ord("+"), ord("=")):
        x1 -= step // 2
        y1 -= step // 2
        x2 += step // 2
        y2 += step // 2
    elif key_low in (ord("-"), ord("_")):
        if rw > step * 2 and rh > step * 2:
            x1 += step // 2
            y1 += step // 2
            x2 -= step // 2
            y2 -= step // 2
    # Width only
    elif key_low == ord("["):
        if rw > step:
            x2 -= step
    elif key_low == ord("]"):
        x2 += step
    # Height only
    elif key_low == ord(";"):
        if rh > step:
            y2 -= step
    elif key_low == ord("'"):
        y2 += step
    return _clamp_roi([x1, y1, x2, y2], w, h)


class _RoiMouse:
    """Drag inside box to move; drag outside to draw a new ROI; double-click to save."""

    def __init__(self, roi: list[int]) -> None:
        self.roi = roi
        self.mode: str | None = None  # "move" | "draw"
        self.origin = (0, 0)
        self.start_roi = list(roi)
        self.img_wh = (1280, 720)
        self.save_requested = False
        self._last_click_t = 0.0

    def set_image_size(self, w: int, h: int) -> None:
        self.img_wh = (w, h)

    def on_mouse(self, event: int, x: int, y: int, flags: int, _param: Any) -> None:
        w, h = self.img_wh
        x = max(0, min(int(x), w - 1))
        y = max(0, min(int(y), h - 1))
        x1, y1, x2, y2 = self.roi

        if event == cv2.EVENT_LBUTTONDBLCLK:
            self.save_requested = True
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            now = time.time()
            # Fallback double-click if DBLCLK not delivered by some Qt builds
            if now - self._last_click_t < 0.35:
                self.save_requested = True
                self._last_click_t = 0.0
                return
            self._last_click_t = now
            self.origin = (x, y)
            self.start_roi = list(self.roi)
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.mode = "move"
            else:
                self.mode = "draw"
                self.roi = [x, y, x + 1, y + 1]
        elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):
            if self.mode == "move":
                dx = x - self.origin[0]
                dy = y - self.origin[1]
                sx1, sy1, sx2, sy2 = self.start_roi
                self.roi = _clamp_roi([sx1 + dx, sy1 + dy, sx2 + dx, sy2 + dy], w, h)
            elif self.mode == "draw":
                ox, oy = self.origin
                self.roi = _clamp_roi(
                    [min(ox, x), min(oy, y), max(ox, x), max(oy, y)],
                    w,
                    h,
                )
        elif event == cv2.EVENT_LBUTTONUP:
            self.mode = None
            # Reject tiny accidental clicks
            if self.roi[2] - self.roi[0] < 8 or self.roi[3] - self.roi[1] < 8:
                self.roi = _clamp_roi(self.start_roi, w, h)


def _draw_roi_overlay(
    bgr: np.ndarray,
    roi: list[int],
    *,
    depth: np.ndarray | None = None,
    enable_depth: bool = False,
) -> np.ndarray:
    h, w = bgr.shape[:2]
    roi = _clamp_roi(roi, w, h)
    vis = bgr.copy()
    x1, y1, x2, y2 = roi
    cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
    dmed = depth_median_m(depth, (x1, y1, x2, y2))
    hud = f"ROI=[{x1},{y1},{x2},{y2}]  {w}x{h}"
    if dmed is not None:
        hud += f"  depth_med={dmed:.3f}m"
    elif enable_depth:
        hud += "  depth=n/a"
    cv2.putText(vis, hud, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 0), 2, cv2.LINE_AA)
    tip = "drag box | double-click=SAVE | q=quit (auto-save) | terminal: save"
    cv2.putText(vis, tip, (10, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1, cv2.LINE_AA)
    return vis


def _open_preview_window(win: str) -> None:
    """Create GUI window early so user sees something before first frame."""
    # Prefer a normal resizable window (Qt/GTK). Fail with a clear tip if headless.
    try:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 960, 540)
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            placeholder,
            "Waiting for camera...",
            (40, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 220, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.imshow(win, placeholder)
        cv2.waitKey(1)
    except cv2.error as exc:
        raise RuntimeError(
            "OpenCV GUI window failed. Cursor 터미널이 아니라 OS 터미널에서 실행하거나, "
            "GUI 없이 snap 모드를 쓰세요:\n"
            "  python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py snap --roi 100 80 320 220\n"
            f"detail: {exc}"
        ) from exc


def run_preview(args: argparse.Namespace) -> int:
    cfg_path = Path(args.roi_yaml).expanduser()
    cfg = load_roi_yaml(cfg_path)
    exhibit_id = args.exhibit_id or cfg.get("exhibit_id") or DEFAULT_EXHIBIT_ID

    roi_t = _parse_roi(args.roi) if args.roi else roi_from_config(cfg)
    if roi_t is None:
        roi_t = (180, 40, 1100, 680)
        print(f"[WARN] no ROI given; using placeholder {roi_t}", flush=True)

    rgb_topic, compressed = _resolve_rgb_topic(args)
    depth_topic = args.depth_topic
    enable_depth = bool(args.depth)

    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not display:
        print(
            "[FAIL] DISPLAY/WAYLAND_DISPLAY 없음 — GUI 창을 띄울 수 없습니다.\n"
            "  · Ubuntu 앱 터미널에서 다시 실행하거나\n"
            "  · GUI 없이: python3 ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py snap --roi ...",
            flush=True,
        )
        return 2
    print(f"[INFO] DISPLAY={display}", flush=True)

    rclpy.init()
    node = CameraBuffer(
        rgb_topic=rgb_topic,
        compressed=compressed,
        depth_topic=depth_topic,
        enable_depth=enable_depth,
    )
    win = "exhibit ROI preview (o=save q=quit)"
    roi = list(roi_t)
    mouse = _RoiMouse(roi)
    print(
        "Move: drag green box, or WASD / arrows | New box: drag outside box | "
        "+/- size | o/Enter save | q quit",
        flush=True,
    )
    print(f"ROI yaml: {cfg_path}", flush=True)
    print(f"[..] waiting for frames on {rgb_topic} ...", flush=True)
    try:
        _open_preview_window(win)
        cv2.setMouseCallback(win, mouse.on_mouse)

        # Pump GUI while waiting; show status text on the open window.
        deadline = time.time() + 30.0
        first = None
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.05)
            bgr, _, count = node.snapshot()
            if bgr is not None and count >= 1:
                first = bgr
                break
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(
                placeholder,
                "Waiting for camera...",
                (40, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 220, 0),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                placeholder,
                rgb_topic[:48],
                (20, 270),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (180, 180, 180),
                1,
                cv2.LINE_AA,
            )
            cv2.imshow(win, placeholder)
            if (cv2.waitKey(1) & 0xFF) in (ord("q"), ord("Q"), 27):
                return 0
        if first is None:
            raise RuntimeError(
                f"no RGB frames on {rgb_topic} within 30s "
                "(need BEST_EFFORT/VOLATILE match with jpeg_compressor)"
            )
        print("[OK] camera frame received — live preview running", flush=True)
        print(
            "========================================\n"
            " 저장 방법 (하나만 하면 됨):\n"
            "  1) 초록 창에서 박스 더블클릭\n"
            "  2) 터미널에  save  입력 후 Enter\n"
            "  3) 창에서 q (종료하면서 자동 저장)\n"
            "========================================",
            flush=True,
        )

        def _poll_stdin_cmd() -> str | None:
            if not sys.stdin.isatty():
                return None
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.0)
            except (ValueError, OSError):
                return None
            if not ready:
                return None
            line = sys.stdin.readline()
            if not line:
                return None
            return line.strip().lower()

        def _do_save(cur_roi: list[int], width: int, height: int) -> bool:
            nonlocal cfg
            x1, y1, x2, y2 = cur_roi
            try:
                validate_roi((x1, y1, x2, y2), width, height)
            except ValueError as exc:
                print(f"[FAIL] {exc}", flush=True)
                return False
            save_roi_yaml(cfg_path, exhibit_id=exhibit_id, roi=(x1, y1, x2, y2), existing=cfg)
            ds_roi = Path(args.dataset_root).expanduser() / "roi.yaml"
            save_roi_yaml(ds_roi, exhibit_id=exhibit_id, roi=(x1, y1, x2, y2), existing=cfg)
            print(f"[OK] saved ROI [{x1},{y1},{x2},{y2}] -> {cfg_path}", flush=True)
            print(f"[OK] saved ROI -> {ds_roi}", flush=True)
            cfg = load_roi_yaml(cfg_path)
            return True

        last_wh = (0, 0)
        try:
            while rclpy.ok():
                rclpy.spin_once(node, timeout_sec=0.02)
                bgr, depth, _ = node.snapshot()
                if bgr is None:
                    cv2.waitKey(1)
                    continue
                h, w = bgr.shape[:2]
                last_wh = (w, h)
                mouse.set_image_size(w, h)
                roi = _clamp_roi(mouse.roi, w, h)
                mouse.roi = roi
                vis = _draw_roi_overlay(bgr, roi, depth=depth, enable_depth=enable_depth)
                cv2.imshow(win, vis)

                if mouse.save_requested:
                    mouse.save_requested = False
                    _do_save(roi, w, h)

                token = _poll_stdin_cmd()
                if token:
                    if token in ("q", "quit", "exit"):
                        break
                    if token in ("p", "print"):
                        print(f"ROI x1 y1 x2 y2 = {' '.join(str(v) for v in roi)}", flush=True)
                    elif token in ("o", "save", "s"):
                        _do_save(roi, w, h)
                    else:
                        print(
                            f"[WARN] unknown command {token!r} — use: save | print | quit",
                            flush=True,
                        )

                key = cv2.waitKeyEx(1)
                if key < 0:
                    continue
                key_low = key & 0xFF
                if key_low in (ord("q"), ord("Q"), 27):
                    break
                if key_low in (ord("p"), ord("P")):
                    print(f"ROI x1 y1 x2 y2 = {' '.join(str(v) for v in roi)}", flush=True)
                    continue
                if key_low in (ord("o"), ord("O"), 13):
                    _do_save(roi, w, h)
                    continue
                if key_low in (
                    ord("a"),
                    ord("A"),
                    ord("d"),
                    ord("D"),
                    ord("w"),
                    ord("W"),
                    ord("s"),
                    ord("S"),
                    ord("+"),
                    ord("="),
                    ord("-"),
                    ord("_"),
                    ord("["),
                    ord("]"),
                    ord(";"),
                    ord("'"),
                ) or key in (
                    81,
                    82,
                    83,
                    84,
                    2424832,
                    2490368,
                    2555904,
                    2621440,
                    65361,
                    65362,
                    65363,
                    65364,
                ):
                    mouse.roi = _nudge_roi(roi, key, w, h)
        finally:
            # Always persist last ROI on exit so key-focus issues don't lose work.
            w, h = last_wh
            if w > 0 and h > 0:
                final = _clamp_roi(mouse.roi, w, h)
                print("[..] auto-saving ROI on exit ...", flush=True)
                _do_save(final, w, h)
    except KeyboardInterrupt:
        print("\n[INFO] interrupted", flush=True)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return 1
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(f"final ROI: {' '.join(str(v) for v in mouse.roi)}", flush=True)
    return 0


def run_set_roi(args: argparse.Namespace) -> int:
    """Save ROI from CLI without opening a window."""
    cfg_path = Path(args.roi_yaml).expanduser()
    cfg = load_roi_yaml(cfg_path)
    exhibit_id = args.exhibit_id or cfg.get("exhibit_id") or DEFAULT_EXHIBIT_ID
    roi_t = _parse_roi(args.roi)
    if roi_t is None:
        print("[FAIL] --roi x1 y1 x2 y2 required", flush=True)
        return 2
    x1, y1, x2, y2 = roi_t
    if x1 >= x2 or y1 >= y2:
        print("[FAIL] need x1 < x2 and y1 < y2", flush=True)
        return 2
    save_roi_yaml(cfg_path, exhibit_id=exhibit_id, roi=roi_t, existing=cfg)
    ds_roi = Path(args.dataset_root).expanduser() / "roi.yaml"
    save_roi_yaml(ds_roi, exhibit_id=exhibit_id, roi=roi_t, existing=cfg)
    print(f"[OK] saved ROI [{x1},{y1},{x2},{y2}] -> {cfg_path}", flush=True)
    return 0


def run_snap(args: argparse.Namespace) -> int:
    """Save one annotated JPEG (no GUI) so ROI can be checked in the file browser."""
    cfg_path = Path(args.roi_yaml).expanduser()
    cfg = load_roi_yaml(cfg_path)
    exhibit_id = args.exhibit_id or cfg.get("exhibit_id") or DEFAULT_EXHIBIT_ID
    roi_t = _parse_roi(args.roi) if args.roi else roi_from_config(cfg)
    if roi_t is None:
        roi_t = (100, 80, 320, 220)
        print(f"[WARN] no ROI given; using placeholder {roi_t}", flush=True)

    out = Path(args.out).expanduser() if args.out else (
        Path(args.dataset_root).expanduser() / "preview_snap.jpg"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    rgb_topic, compressed = _resolve_rgb_topic(args)
    rclpy.init()
    node = CameraBuffer(
        rgb_topic=rgb_topic,
        compressed=compressed,
        depth_topic=args.depth_topic,
        enable_depth=bool(args.depth),
    )
    try:
        print(f"[..] waiting for frame on {rgb_topic} ...", flush=True)
        bgr = node.wait_for_frame()
        h, w = bgr.shape[:2]
        roi = _clamp_roi(list(roi_t), w, h)
        try:
            validate_roi((roi[0], roi[1], roi[2], roi[3]), w, h)
        except ValueError as exc:
            print(f"[FAIL] {exc}", flush=True)
            return 1
        _, depth, _ = node.snapshot()
        vis = _draw_roi_overlay(bgr, roi, depth=depth, enable_depth=bool(args.depth))
        cv2.imwrite(str(out), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if args.save_roi:
            save_roi_yaml(
                cfg_path,
                exhibit_id=exhibit_id,
                roi=(roi[0], roi[1], roi[2], roi[3]),
                existing=cfg,
            )
            print(f"[OK] saved ROI -> {cfg_path}", flush=True)
        print(f"[OK] wrote {out}  size={w}x{h}  ROI={' '.join(str(v) for v in roi)}", flush=True)
        print("파일을 열어서 초록 박스가 그림에 맞는지 확인하세요.", flush=True)
        return 0
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _resolve_rgb_topic(args: argparse.Namespace) -> tuple[str, bool]:
    if args.raw:
        # --raw with default compressed topic → switch to raw Image topic
        topic = DEFAULT_RAW if args.topic == DEFAULT_COMPRESSED else args.topic
        return topic, False
    return args.topic, True


def _unique_stem(base_dir: Path, prefix: str) -> str:
    """Return a unique stem; never overwrite existing files."""
    stamp = _utc_stamp()
    for i in range(10_000):
        stem = f"{prefix}_{stamp}_{i:03d}"
        if not base_dir.exists() or not any(base_dir.glob(f"*{stem}*")):
            return stem
    raise RuntimeError("could not allocate unique filename")


def _save_one_shot(
    *,
    bgr: np.ndarray,
    depth: np.ndarray | None,
    roi_t: tuple[int, int, int, int],
    dataset_root: Path,
    raw_dir: Path,
    crop_dir: Path,
    meta_dir: Path,
    jsonl_path: Path,
    exhibit_id: str,
    label: str,
    session: str,
    rgb_topic: str,
    depth_topic: str | None,
    enable_depth: bool,
) -> str:
    """Write rgb+crop+metadata. Returns stem. Raises ValueError/RuntimeError on failure."""
    h, w = bgr.shape[:2]
    validate_roi(roi_t, w, h)
    x1, y1, x2, y2 = roi_t
    crop = bgr[y1:y2, x1:x2]
    if crop.size == 0:
        raise RuntimeError("empty crop")

    stem = _unique_stem(raw_dir, session)
    rgb_path = raw_dir / f"{stem}_rgb.jpg"
    crop_path = crop_dir / f"{stem}_crop.jpg"
    meta_path = meta_dir / f"{stem}.json"
    for p in (rgb_path, crop_path, meta_path):
        if p.exists():
            raise RuntimeError(f"refusing overwrite: {p}")

    ok1 = cv2.imwrite(str(rgb_path), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    ok2 = cv2.imwrite(str(crop_path), crop, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok1 or not ok2:
        raise RuntimeError(f"imwrite failed rgb={ok1} crop={ok2}")

    dmed = depth_median_m(depth, roi_t)
    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "exhibit_id": exhibit_id,
        "label": label,
        "session_id": session,
        "rgb_topic": rgb_topic,
        "depth_topic": depth_topic if enable_depth else None,
        "depth_median_m": dmed,
        "roi": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "image_resolution": {"width": w, "height": h},
        "paths": {
            "rgb": str(rgb_path.relative_to(dataset_root)),
            "crop": str(crop_path.relative_to(dataset_root)),
        },
        "stem": stem,
    }
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return stem


def run_capture(args: argparse.Namespace) -> int:
    if args.label not in VALID_LABELS:
        print(f"[FAIL] --label must be one of {VALID_LABELS}, got {args.label!r}")
        return 2

    cfg_path = Path(args.roi_yaml).expanduser()
    cfg = load_roi_yaml(cfg_path)
    exhibit_id = args.exhibit_id or cfg.get("exhibit_id") or DEFAULT_EXHIBIT_ID

    roi_t = _parse_roi(args.roi) if args.roi else roi_from_config(cfg)
    if roi_t is None:
        print(f"[FAIL] ROI required: pass --roi x1 y1 x2 y2 or save via preview to {cfg_path}")
        return 2

    dataset_root = Path(args.dataset_root).expanduser().resolve()
    _, raw_rel, crop_rel = label_paths(args.label)
    raw_dir = dataset_root / "raw" / raw_rel / args.session
    crop_dir = dataset_root / "crops" / crop_rel
    meta_dir = dataset_root / "metadata"
    for d in (raw_dir, crop_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)

    jsonl_path = meta_dir / "captures.jsonl"
    rgb_topic, compressed = _resolve_rgb_topic(args)
    enable_depth = bool(args.depth)
    live = bool(getattr(args, "live", False))

    rclpy.init()
    node = CameraBuffer(
        rgb_topic=rgb_topic,
        compressed=compressed,
        depth_topic=args.depth_topic,
        enable_depth=enable_depth,
    )
    saved = 0
    win = "capture live (SPACE/c=shot  q=quit)"
    try:
        print(f"[..] waiting for frames on {rgb_topic} ...", flush=True)
        node.wait_stable(STABLE_FRAME_COUNT)
        print(
            f"[OK] label={args.label} session={args.session} roi={roi_t} "
            f"target={args.count} live={live}",
            flush=True,
        )
        if live:
            print(
                "========================================\n"
                " 화면 보면서 찍기:\n"
                "  · 초록 창에서 SPACE 또는 c  → 1장 저장\n"
                "  · 터미널에 shoot 입력 후 Enter → 1장 저장\n"
                "  · q 또는 quit → 종료\n"
                "========================================",
                flush=True,
            )
            cv2.namedWindow(win, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(win, 960, 540)

        def _poll_cmd() -> str | None:
            if not sys.stdin.isatty():
                return None
            try:
                ready, _, _ = select.select([sys.stdin], [], [], 0.0)
            except (ValueError, OSError):
                return None
            if not ready:
                return None
            line = sys.stdin.readline()
            return line.strip().lower() if line else None

        last_save = 0.0
        while saved < args.count and rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.02)
            bgr, depth, _ = node.snapshot()
            if bgr is None:
                if live:
                    cv2.waitKey(1)
                continue

            take = False
            if live:
                vis = _draw_roi_overlay(bgr, list(roi_t), depth=depth, enable_depth=enable_depth)
                hud2 = f"shots {saved}/{args.count}  SPACE=capture  q=quit"
                cv2.putText(
                    vis, hud2, (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA
                )
                cv2.imshow(win, vis)
                key = cv2.waitKeyEx(1)
                key_low = key & 0xFF if key >= 0 else 255
                if key_low in (ord("q"), ord("Q"), 27):
                    break
                if key_low in (ord(" "), ord("c"), ord("C")):
                    take = True
                token = _poll_cmd()
                if token in ("q", "quit", "exit"):
                    break
                if token in ("shoot", "shot", "c", "capture", "o", "s"):
                    take = True
            else:
                now = time.time()
                if saved > 0 and (now - last_save) < args.interval:
                    continue
                take = True

            if not take:
                continue

            try:
                stem = _save_one_shot(
                    bgr=bgr,
                    depth=depth,
                    roi_t=roi_t,
                    dataset_root=dataset_root,
                    raw_dir=raw_dir,
                    crop_dir=crop_dir,
                    meta_dir=meta_dir,
                    jsonl_path=jsonl_path,
                    exhibit_id=exhibit_id,
                    label=args.label,
                    session=args.session,
                    rgb_topic=rgb_topic,
                    depth_topic=args.depth_topic,
                    enable_depth=enable_depth,
                )
            except (ValueError, RuntimeError) as exc:
                print(f"[FAIL] {exc}", flush=True)
                return 1

            saved += 1
            last_save = time.time()
            print(f"[{saved}/{args.count}] saved {stem}", flush=True)

            if not live and saved < args.count:
                t_end = last_save + args.interval
                while time.time() < t_end and rclpy.ok():
                    rclpy.spin_once(node, timeout_sec=0.05)
    except KeyboardInterrupt:
        print("\n[WARN] interrupted", flush=True)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return 1
    finally:
        if live:
            cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    print(f"[OK] saved {saved}/{args.count} under {dataset_root}", flush=True)
    return 0 if saved == args.count else 1


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help=f"dataset root (default: {DEFAULT_DATASET_ROOT})",
    )
    shared.add_argument(
        "--roi-yaml",
        default=str(DEFAULT_ROI_YAML),
        help=f"ROI / exhibit config YAML (default: {DEFAULT_ROI_YAML})",
    )
    shared.add_argument("--exhibit-id", default=None, help=f"default {DEFAULT_EXHIBIT_ID}")
    shared.add_argument(
        "--topic",
        default=DEFAULT_COMPRESSED,
        help="RGB topic (default: T1 compressed from env or tb3_1)",
    )
    shared.add_argument(
        "--raw",
        action="store_true",
        help="subscribe sensor_msgs/Image (raw) instead of CompressedImage",
    )
    shared.add_argument(
        "--depth",
        action="store_true",
        help="also subscribe depth topic for depth_median_m (off by default)",
    )
    shared.add_argument("--depth-topic", default=DEFAULT_DEPTH)

    p = argparse.ArgumentParser(
        description="Phase 1 exhibit dataset capture (painting authenticity)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    prev = sub.add_parser("preview", parents=[shared], help="live RGB + adjustable ROI")
    prev.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="initial ROI; else load from --roi-yaml",
    )
    prev.set_defaults(func=run_preview)

    setroi = sub.add_parser(
        "set-roi",
        parents=[shared],
        help="save ROI from CLI without opening a window",
    )
    setroi.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        required=True,
    )
    setroi.set_defaults(func=run_set_roi)

    snap = sub.add_parser(
        "snap",
        parents=[shared],
        help="save one annotated JPEG (no GUI) — use if preview window does not appear",
    )
    snap.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="ROI to draw; else load from --roi-yaml",
    )
    snap.add_argument(
        "--out",
        default=None,
        help="output JPEG path (default: datasets/museum_auth_dataset/preview_snap.jpg)",
    )
    snap.add_argument(
        "--save-roi",
        action="store_true",
        help="also write current ROI into --roi-yaml",
    )
    snap.set_defaults(func=run_snap)

    cap = sub.add_parser("capture", parents=[shared], help="save N RGB + crop + metadata")
    cap.add_argument(
        "--label",
        required=True,
        choices=VALID_LABELS,
        help="genuine | fake_01 | fake_02 | fake_03 | fake_04",
    )
    cap.add_argument("--session", required=True, help="e.g. session_01")
    cap.add_argument("--count", type=int, default=5)
    cap.add_argument("--interval", type=float, default=0.4, help="seconds between shots (non-live)")
    cap.add_argument(
        "--live",
        action="store_true",
        help="show live camera+ROI; press SPACE/c (or type shoot) to take each shot",
    )
    cap.add_argument(
        "--roi",
        nargs=4,
        type=int,
        metavar=("X1", "Y1", "X2", "Y2"),
        help="ROI; else load from --roi-yaml",
    )
    cap.set_defaults(func=run_capture)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "count", None) is not None and args.count < 1:
        print("[FAIL] --count must be >= 1")
        return 2
    if getattr(args, "interval", None) is not None and args.interval < 0:
        print("[FAIL] --interval must be >= 0")
        return 2
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
