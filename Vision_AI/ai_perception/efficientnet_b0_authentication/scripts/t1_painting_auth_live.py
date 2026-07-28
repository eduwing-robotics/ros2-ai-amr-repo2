#!/usr/bin/env python3
"""Live T1 painting authenticity test (RGB + ROI + EfficientNet).

Shows RealSense JPEG with ROI overlay and GENUINE / FAKE / RECHECK.

Pre:
  Robot:  ./scripts/launch_t1_realsense.sh
  Laptop: source ./scripts/camera_laptop_env.sh

Usage:
  python3 ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py
  python3 ai_perception/efficientnet_b0_authentication/scripts/t1_painting_auth_live.py --genuine-threshold 0.55 --fake-threshold 0.55

Keys (OpenCV window focused):
  q = quit
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import cv2
import numpy as np
import rclpy
import torch
import torch.nn as nn
import yaml
from PIL import Image
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from sensor_msgs.msg import CompressedImage
from torchvision import models, transforms

REPO = Path(__file__).resolve().parents[3]
DEFAULT_CKPT = REPO / "ai_perception" / "efficientnet_b0_authentication" / "models" / "bacchus_auth_effnet_b0.pt"
DEFAULT_ROI_YAML = REPO / "ai_perception" / "efficientnet_b0_authentication" / "config" / "painting_auth_bacchus.yaml"
DEFAULT_TOPIC = os.environ.get(
    "T1_CAMERA_COMPRESSED",
    "/tb3_1/camera/color/image_raw/compressed",
)
CLASS_NAMES = ("genuine", "fake")

CAMERA_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=5,
    durability=DurabilityPolicy.VOLATILE,
)


def load_roi(path: Path) -> tuple[int, int, int, int]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    roi = data.get("roi") or {}
    return int(roi["x1"]), int(roi["y1"]), int(roi["x2"]), int(roi["y2"])


def build_model(num_classes: int = 2) -> nn.Module:
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def load_checkpoint(path: Path, device: torch.device):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    classes = tuple(ckpt.get("classes", CLASS_NAMES))
    model = build_model(len(classes))
    model.load_state_dict(ckpt["state_dict"])
    model.to(device).eval()
    return model, classes


def build_transform() -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


class CameraBuffer(Node):
    def __init__(self, topic: str) -> None:
        super().__init__("t1_painting_auth_live")
        self._lock = threading.Lock()
        self._bgr: np.ndarray | None = None
        self.create_subscription(CompressedImage, topic, self._on_compressed, CAMERA_QOS)
        self.get_logger().info(f"rgb topic={topic}")

    def _on_compressed(self, msg: CompressedImage) -> None:
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return
        with self._lock:
            self._bgr = bgr

    def snapshot(self) -> np.ndarray | None:
        with self._lock:
            return None if self._bgr is None else self._bgr.copy()

    def wait_frame(self, timeout_s: float = 30.0) -> np.ndarray:
        deadline = time.time() + timeout_s
        while time.time() < deadline and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.05)
            cv2.waitKey(1)
            bgr = self.snapshot()
            if bgr is not None:
                return bgr
        raise RuntimeError("no camera frames — check launch_t1_realsense + camera_laptop_env")


def decide(
    p_g: float,
    p_f: float,
    *,
    mode: str,
    genuine_thr: float,
    fake_thr: float,
    margin: float,
) -> str:
    """Return GENUINE / FAKE / RECHECK."""
    if mode == "argmax_margin":
        # Prefer clear winner; RECHECK only when scores are close.
        if abs(p_g - p_f) < margin:
            return "RECHECK"
        return "GENUINE" if p_g >= p_f else "FAKE"
    # Absolute thresholds (stricter; more RECHECK on soft models)
    if p_g >= genuine_thr:
        return "GENUINE"
    if p_f >= fake_thr:
        return "FAKE"
    return "RECHECK"


@torch.no_grad()
def score_crop(
    model: nn.Module,
    crop_bgr: np.ndarray,
    transform: transforms.Compose,
    device: torch.device,
    classes: tuple[str, ...],
    genuine_thr: float,
    fake_thr: float,
    mode: str = "argmax_margin",
    margin: float = 0.08,
) -> tuple[str, float, float]:
    rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    pil = Image.fromarray(rgb)
    x = transform(pil).unsqueeze(0).to(device)
    probs = torch.softmax(model(x), dim=1)[0]
    idx = {c: i for i, c in enumerate(classes)}
    p_g = float(probs[idx["genuine"]].item())
    p_f = float(probs[idx["fake"]].item())
    pred = decide(
        p_g,
        p_f,
        mode=mode,
        genuine_thr=genuine_thr,
        fake_thr=fake_thr,
        margin=margin,
    )
    return pred, p_g, p_f


def main() -> int:
    p = argparse.ArgumentParser(description="Live painting authenticity viewer")
    p.add_argument("--checkpoint", type=Path, default=DEFAULT_CKPT)
    p.add_argument("--roi-yaml", type=Path, default=DEFAULT_ROI_YAML)
    p.add_argument("--topic", default=DEFAULT_TOPIC)
    p.add_argument("--genuine-threshold", type=float, default=0.55)
    p.add_argument("--fake-threshold", type=float, default=0.55)
    p.add_argument(
        "--mode",
        choices=("argmax_margin", "threshold"),
        default="argmax_margin",
        help="argmax_margin: pick clearer side unless |G-F|<margin (default, better for soft models)",
    )
    p.add_argument(
        "--margin",
        type=float,
        default=0.08,
        help="RECHECK if |genuine-fake| < margin (argmax_margin mode)",
    )
    p.add_argument("--every-n", type=int, default=3, help="run model every N frames")
    args = p.parse_args()

    ckpt = args.checkpoint.expanduser().resolve()
    if not ckpt.is_file():
        print(f"[FAIL] missing checkpoint: {ckpt}", flush=True)
        return 1
    roi_path = args.roi_yaml.expanduser()
    if not roi_path.is_file():
        print(f"[FAIL] missing ROI yaml: {roi_path}", flush=True)
        return 1

    x1, y1, x2, y2 = load_roi(roi_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, classes = load_checkpoint(ckpt, device)
    transform = build_transform()
    print(
        f"[INFO] device={device} ROI=[{x1},{y1},{x2},{y2}] "
        f"mode={args.mode} margin={args.margin} "
        f"thr genuine={args.genuine_threshold} fake={args.fake_threshold}",
        flush=True,
    )

    rclpy.init()
    node = CameraBuffer(args.topic)
    win = "painting auth live (q=quit)"
    pred, p_g, p_f = "WAITING", 0.0, 0.0
    frame_i = 0
    try:
        print("[..] waiting for camera ...", flush=True)
        node.wait_frame()
        print("[OK] live — put painting in green box", flush=True)
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(win, 960, 540)
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.02)
            bgr = node.snapshot()
            if bgr is None:
                cv2.waitKey(1)
                continue
            h, w = bgr.shape[:2]
            xx1, yy1 = max(0, x1), max(0, y1)
            xx2, yy2 = min(w, x2), min(h, y2)
            if xx2 - xx1 < 8 or yy2 - yy1 < 8:
                print("[FAIL] ROI out of bounds for current image", flush=True)
                return 1
            crop = bgr[yy1:yy2, xx1:xx2]
            frame_i += 1
            if frame_i % max(args.every_n, 1) == 0:
                pred, p_g, p_f = score_crop(
                    model,
                    crop,
                    transform,
                    device,
                    classes,
                    args.genuine_threshold,
                    args.fake_threshold,
                    mode=args.mode,
                    margin=args.margin,
                )

            vis = bgr.copy()
            color = {
                "GENUINE": (0, 220, 0),
                "FAKE": (0, 0, 255),
                "RECHECK": (0, 200, 255),
                "WAITING": (200, 200, 200),
            }.get(pred, (255, 255, 255))
            cv2.rectangle(vis, (xx1, yy1), (xx2, yy2), color, 2)
            hud = f"{pred}  G={p_g:.2f}  F={p_f:.2f}"
            cv2.putText(vis, hud, (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2, cv2.LINE_AA)
            cv2.imshow(win, vis)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
    except KeyboardInterrupt:
        pass
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", flush=True)
        return 1
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
