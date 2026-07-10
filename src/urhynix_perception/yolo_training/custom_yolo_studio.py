"""
custom_yolo_studio.py - RealSense capture, browser labeling, YOLO training.

Input: T1 web_video_server MJPEG stream.
Output: datasets/custom_object YOLO dataset + runs/custom_object/.../best.pt.
Run: /Users/family/jason/URHYNIX/test/.venv/bin/python scripts/yolo_training/custom_yolo_studio.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "datasets" / "custom_object"
DEFAULT_RUNS = ROOT / "runs" / "custom_object"
DEFAULT_SAM2_MODEL = ROOT / "sam2_t.pt"
DEFAULT_TOPIC = "/camera/camera/color/image_raw"
DEFAULT_COMPRESSED_TOPIC = "/camera/camera/color/image_raw/compressed"


def now_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in value).strip("_") or "item"


def yolo_line(box: dict[str, Any], width: int, height: int) -> str:
    x1, y1, x2, y2 = [float(box[k]) for k in ("x1", "y1", "x2", "y2")]
    x1, x2 = sorted((max(0.0, min(x1, width)), max(0.0, min(x2, width))))
    y1, y2 = sorted((max(0.0, min(y1, height)), max(0.0, min(y2, height))))
    cx = ((x1 + x2) / 2.0) / width
    cy = ((y1 + y2) / 2.0) / height
    bw = (x2 - x1) / width
    bh = (y2 - y1) / height
    cls = int(box.get("class_id", 0))
    return f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def box_from_yolo(line: str, width: int, height: int) -> dict[str, Any] | None:
    parts = line.split()
    if len(parts) != 5:
        return None
    cls, cx, cy, bw, bh = [float(p) for p in parts]
    x1 = (cx - bw / 2.0) * width
    y1 = (cy - bh / 2.0) * height
    x2 = (cx + bw / 2.0) * width
    y2 = (cy + bh / 2.0) * height
    return {"class_id": int(cls), "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def clamp_box(box: dict[str, Any], width: int, height: int) -> dict[str, Any]:
    x1, y1, x2, y2 = [float(box[k]) for k in ("x1", "y1", "x2", "y2")]
    x1, x2 = sorted((max(0.0, min(x1, width - 1)), max(0.0, min(x2, width))))
    y1, y2 = sorted((max(0.0, min(y1, height - 1)), max(0.0, min(y2, height))))
    return {"class_id": int(box.get("class_id", 0)), "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def int_roi(box: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int, int]:
    clamped = clamp_box(box, width, height)
    x1 = int(round(clamped["x1"]))
    y1 = int(round(clamped["y1"]))
    x2 = int(round(clamped["x2"]))
    y2 = int(round(clamped["y2"]))
    if x2 - x1 < 8 or y2 - y1 < 8:
        raise RuntimeError("ROI is too small for auto labeling")
    return x1, y1, x2, y2, int(clamped["class_id"])


@dataclass
class TrainState:
    running: bool = False
    done: bool = False
    returncode: int | None = None
    log: list[str] = field(default_factory=list)
    best_pt: str = ""


class StudioState:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.dataset = Path(args.dataset).resolve()
        self.runs = Path(args.runs).resolve()
        self.classes = [c.strip() for c in args.classes.split(",") if c.strip()]
        if not self.classes:
            self.classes = ["학습대상"]
        self.web_url = f"http://{args.t1_ip}:{args.port}/stream?topic={args.topic}&type=mjpeg"
        self.web_snapshot_url = f"http://{args.t1_ip}:{args.port}/snapshot?topic={args.topic}&type=jpeg"
        self.fast_url = f"http://{args.t1_ip}:{args.fast_port}/stream.mjpg"
        self.fast_snapshot_url = f"http://{args.t1_ip}:{args.fast_port}/snapshot.jpg"
        self.fast_preview_url = f"http://{args.t1_ip}:{args.fast_port}/preview.jpg"
        self.url = self.fast_url if args.prefer_fast_stream else self.web_url
        self.snapshot_url = self.fast_snapshot_url if args.prefer_fast_stream else self.web_snapshot_url
        self.cap_lock = threading.Lock()
        self.cap = None
        self.last_frame: Any | None = None
        self.last_frame_at = 0.0
        self.last_capture: dict[str, Any] | None = None
        self.stop_capture = False
        self.train = TrainState()
        self.detect_model = None
        self.detect_model_path = ""
        self.sam_model = None
        self.sam_model_path = ""
        self.sam_model_error = ""
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self._ensure_dirs()
        self.write_yaml()

    def _ensure_dirs(self) -> None:
        for split in ("train", "val"):
            (self.dataset / "images" / split).mkdir(parents=True, exist_ok=True)
            (self.dataset / "labels" / split).mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)

    def write_yaml(self) -> Path:
        data = [
            f"path: {self.dataset}",
            "train: images/train",
            "val: images/val",
            f"nc: {len(self.classes)}",
            "names:",
        ]
        data.extend(f"  {i}: {name}" for i, name in enumerate(self.classes))
        path = self.dataset / "data.yaml"
        path.write_text("\n".join(data) + "\n", encoding="utf-8")
        return path

    def read_frame(self) -> tuple[bool, Any | None]:
        with self.cap_lock:
            if self.last_frame is not None and time.time() - self.last_frame_at < 0.2:
                return True, self.last_frame.copy()
        for url, timeout in ((self.snapshot_url, 1.5), (self.web_snapshot_url, 4.0)):
            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    data = response.read()
                arr = cv2.imdecode(np.frombuffer(data, dtype="uint8"), cv2.IMREAD_COLOR)
                if arr is None:
                    continue
                with self.cap_lock:
                    self.last_frame = arr
                    self.last_frame_at = time.time()
                return True, arr.copy()
            except Exception:
                continue
        with self.cap_lock:
            if self.last_frame is not None:
                return True, self.last_frame.copy()
            return False, None

    def read_preview_frame(self) -> tuple[bool, Any | None]:
        try:
            with urllib.request.urlopen(self.fast_preview_url, timeout=1.0) as response:
                data = response.read()
            arr = cv2.imdecode(np.frombuffer(data, dtype="uint8"), cv2.IMREAD_COLOR)
            if arr is None:
                return False, None
            frame = cv2.resize(arr, (640, 480), interpolation=cv2.INTER_LINEAR)
            return True, frame
        except Exception:
            return self.read_frame()

    def _capture_loop(self) -> None:
        misses = 0
        while not self.stop_capture:
            if self.cap is None:
                time.sleep(0.5)
                continue
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(self.url)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                time.sleep(0.5)
                continue
            ok, frame = self.cap.read()
            if ok:
                with self.cap_lock:
                    self.last_frame = frame
                    self.last_frame_at = time.time()
                misses = 0
            else:
                misses += 1
                time.sleep(0.2)
                if misses >= 10:
                    self.cap.release()
                    self.cap = cv2.VideoCapture(self.url)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    misses = 0

    def capture(self) -> dict[str, Any]:
        ok, frame = self.read_frame()
        if not ok or frame is None:
            raise RuntimeError(f"stream frame unavailable: {self.url}")
        height, width = frame.shape[:2]
        train_count = len(list((self.dataset / "images" / "train").glob("*.jpg")))
        val_count = len(list((self.dataset / "images" / "val").glob("*.jpg")))
        split = "val" if (train_count + val_count + 1) % self.args.val_every == 0 else "train"
        stem = f"{safe_name(self.classes[0])}_{now_id()}_{train_count + val_count + 1:04d}"
        image_path = self.dataset / "images" / split / f"{stem}.jpg"
        label_path = self.dataset / "labels" / split / f"{stem}.txt"
        cv2.imwrite(str(image_path), frame)
        label_path.write_text("", encoding="utf-8")
        self.last_capture = {
            "split": split,
            "stem": stem,
            "image": str(image_path),
            "label": str(label_path),
            "width": width,
            "height": height,
        }
        return self.last_capture

    def save_negative_frame(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        ok, frame = self.read_preview_frame()
        if not ok or frame is None:
            raise RuntimeError("stream frame unavailable for negative sample")
        height, width = frame.shape[:2]
        train_count = len(list((self.dataset / "images" / "train").glob("*.jpg")))
        val_count = len(list((self.dataset / "images" / "val").glob("*.jpg")))
        requested_split = str(payload.get("split", "auto"))
        if requested_split in {"train", "val"}:
            split = requested_split
        else:
            split = "val" if (train_count + val_count + 1) % self.args.val_every == 0 else "train"
        stem = f"negative_{safe_name(self.classes[0])}_{now_id()}_{train_count + val_count + 1:04d}"
        image_path = self.dataset / "images" / split / f"{stem}.jpg"
        label_path = self.dataset / "labels" / split / f"{stem}.txt"
        cv2.imwrite(str(image_path), frame)
        label_path.write_text("", encoding="utf-8")
        return {
            "split": split,
            "stem": stem,
            "image": str(image_path),
            "label": str(label_path),
            "width": width,
            "height": height,
            "negative": True,
        }

    def save_labels(self, payload: dict[str, Any]) -> dict[str, Any]:
        capture = payload.get("capture") or self.last_capture
        if not capture:
            raise RuntimeError("capture an image first")
        width = int(capture["width"])
        height = int(capture["height"])
        boxes = payload.get("boxes", [])
        lines = []
        for box in boxes:
            if abs(float(box["x2"]) - float(box["x1"])) < 4 or abs(float(box["y2"]) - float(box["y1"])) < 4:
                continue
            lines.append(yolo_line(box, width, height))
        label_path = Path(capture["label"])
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        review_mask = self._review_mask_path(str(capture["split"]), str(capture["stem"]))
        if review_mask.exists():
            review_mask.unlink()
        return {"saved": len(lines), "label": str(label_path)}

    def auto_label_roi(self, payload: dict[str, Any]) -> dict[str, Any]:
        capture = payload.get("capture") or self.last_capture
        if not capture:
            raise RuntimeError("capture an image first")
        roi = payload.get("roi") or payload.get("box")
        if not roi:
            raise RuntimeError("ROI box is required")
        image = cv2.imread(str(capture["image"]))
        if image is None:
            raise RuntimeError(f"cannot read image: {capture['image']}")
        height, width = image.shape[:2]
        roi_box = clamp_box(roi, width, height)
        engine = str(payload.get("engine") or self.args.auto_label_engine)
        box, meta = self._mask_box_from_roi(image, roi_box, engine)
        saved = self.save_labels({"capture": capture, "boxes": [box]})
        return {
            **saved,
            "box": box,
            "roi": roi_box,
            "engine": meta["engine"],
            "fallback": meta["fallback"],
            "reason": meta["reason"],
            "mask_area_ratio": meta.get("mask_area_ratio"),
            "bbox_area_ratio": meta.get("bbox_area_ratio"),
        }

    def _mask_box_from_roi(
        self,
        image: np.ndarray,
        roi_box: dict[str, Any],
        engine: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        height, width = image.shape[:2]
        x1, y1, x2, y2, class_id = int_roi(roi_box, width, height)
        crop = image[y1:y2, x1:x2]
        attempts: list[tuple[str, str]] = []
        if engine == "auto":
            if self._sam2_weight_path() is not None:
                attempts.append(("sam2", "SAM2 unavailable or failed"))
            if importlib.util.find_spec("rembg") is not None:
                attempts.append(("rembg", "rembg unavailable or failed"))
            if not attempts:
                attempts.append(("grabcut", "grabcut failed"))
        elif engine == "rembg":
            attempts.append(("rembg", "rembg unavailable or failed"))
        elif engine == "sam2":
            attempts.append(("sam2", "SAM2 unavailable or failed"))
        elif engine == "grabcut":
            attempts.append(("grabcut", "grabcut failed"))
        if engine == "roi":
            attempts = []

        reasons = []
        for candidate, default_reason in attempts:
            try:
                mask = self._roi_mask(crop, candidate)
                box, meta = self._bbox_from_mask(mask, x1, y1, class_id, width, height, roi_box=roi_box)
                meta.update({"engine": candidate, "fallback": False, "reason": "ok"})
                return box, meta
            except Exception as exc:
                reasons.append(f"{candidate}: {exc or default_reason}")

        reason = "; ".join(reasons) if reasons else "roi fallback selected"
        return roi_box, {
            "engine": "roi",
            "fallback": True,
            "reason": reason,
            "mask_area_ratio": None,
            "bbox_area_ratio": None,
        }

    def segment_jpeg(self, roi: dict[str, Any], engine: str) -> bytes:
        ok, frame = self.read_preview_frame()
        if not ok or frame is None:
            raise RuntimeError("no frame")
        height, width = frame.shape[:2]
        roi_box = clamp_box(roi, width, height)
        x1, y1, x2, y2, class_id = int_roi(roi_box, width, height)
        crop = frame[y1:y2, x1:x2]
        attempts: list[str] = []
        if engine == "auto":
            if self._sam2_weight_path() is not None:
                attempts.append("sam2")
            if importlib.util.find_spec("rembg") is not None:
                attempts.append("rembg")
            if not attempts:
                attempts.append("grabcut")
        elif engine == "sam2":
            attempts.append("sam2")
        elif engine == "rembg":
            attempts.append("rembg")
        elif engine == "grabcut":
            attempts.append("grabcut")

        mask: np.ndarray | None = None
        box = roi_box
        label = "ROI fallback"
        fallback = True
        reasons = []
        for candidate in attempts:
            try:
                if candidate == "grabcut":
                    candidate_mask = self._grabcut_mask(crop, iterations=2, max_side=220)
                else:
                    candidate_mask = self._roi_mask(crop, candidate)
                candidate_box, meta = self._bbox_from_mask(candidate_mask, x1, y1, class_id, width, height, roi_box=roi_box)
                mask = candidate_mask
                box = candidate_box
                label = f"{candidate} mask {meta.get('mask_area_ratio')}"
                fallback = False
                break
            except Exception as exc:
                reasons.append(f"{candidate}: {exc}")
        if fallback and reasons:
            label = "fallback: " + reasons[-1][:52]

        annotated = frame.copy()
        if mask is not None:
            color = np.zeros_like(crop)
            color[:] = (0, 170, 120)
            blended = cv2.addWeighted(crop, 0.55, color, 0.45, 0)
            target = annotated[y1:y2, x1:x2]
            target[mask > 0] = blended[mask > 0]
        else:
            overlay = annotated.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 255), -1)
            annotated = cv2.addWeighted(annotated, 0.86, overlay, 0.14, 0)

        bx1, by1, bx2, by2 = [int(round(box[k])) for k in ("x1", "y1", "x2", "y2")]
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 180, 255), 2)
        cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (20, 220, 120), 3 if not fallback else 2)
        cv2.rectangle(annotated, (8, 8), (min(width - 8, 360), 58), (0, 0, 0), -1)
        cv2.putText(annotated, "Live segmentation preview", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, label, (14, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 255, 220), 1, cv2.LINE_AA)
        ok2, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        if not ok2:
            raise RuntimeError("jpeg encode failed")
        return bytes(buf)

    def segment_overlay_png(self, roi: dict[str, Any], engine: str) -> bytes:
        ok, frame = self.read_preview_frame()
        if not ok or frame is None:
            raise RuntimeError("no frame")
        height, width = frame.shape[:2]
        roi_box = clamp_box(roi, width, height)
        x1, y1, x2, y2, class_id = int_roi(roi_box, width, height)
        crop = frame[y1:y2, x1:x2]
        attempts: list[str] = []
        if engine == "auto":
            if self._sam2_weight_path() is not None:
                attempts.append("sam2")
            if importlib.util.find_spec("rembg") is not None:
                attempts.append("rembg")
            if not attempts:
                attempts.append("grabcut")
        elif engine == "sam2":
            attempts.append("sam2")
        elif engine == "rembg":
            attempts.append("rembg")
        elif engine == "grabcut":
            attempts.append("grabcut")

        mask: np.ndarray | None = None
        box = roi_box
        label = "ROI"
        fallback = True
        reasons = []
        for candidate in attempts:
            try:
                if candidate == "grabcut":
                    candidate_mask = self._grabcut_mask(crop, iterations=1, max_side=180)
                else:
                    candidate_mask = self._roi_mask(crop, candidate)
                candidate_box, meta = self._bbox_from_mask(candidate_mask, x1, y1, class_id, width, height, roi_box=roi_box)
                mask = candidate_mask
                box = candidate_box
                label = f"{candidate} {meta.get('mask_area_ratio')}"
                fallback = False
                break
            except Exception as exc:
                reasons.append(f"{candidate}: {exc}")
        if fallback and reasons:
            label = "fallback"

        overlay = np.zeros((height, width, 4), dtype=np.uint8)
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0, 145), -1)
        if mask is not None:
            target = overlay[y1:y2, x1:x2]
            target[mask > 0] = (0, 0, 0, 0)
            edge = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
            target[edge > 0] = (20, 220, 120, 235)
        else:
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 255, 28), -1)

        bx1, by1, bx2, by2 = [int(round(box[k])) for k in ("x1", "y1", "x2", "y2")]
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 255, 210), 2)
        cv2.rectangle(overlay, (bx1, by1), (bx2, by2), (20, 220, 120, 235), 3 if not fallback else 2)
        cv2.rectangle(overlay, (8, height - 38), (min(width - 8, 290), height - 8), (0, 0, 0, 150), -1)
        cv2.putText(overlay, f"seg overlay: {label}", (14, height - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255, 230), 1, cv2.LINE_AA)
        ok2, buf = cv2.imencode(".png", overlay)
        if not ok2:
            raise RuntimeError("png encode failed")
        return bytes(buf)

    def _roi_mask(self, crop: np.ndarray, engine: str) -> np.ndarray:
        if engine == "sam2":
            return self._sam2_mask(crop)
        if engine == "rembg":
            return self._rembg_mask(crop)
        if engine == "grabcut":
            return self._grabcut_mask(crop)
        raise RuntimeError(f"unknown auto-label engine: {engine}")

    def _sam2_weight_path(self) -> Path | None:
        raw = str(getattr(self.args, "sam2_model", "") or DEFAULT_SAM2_MODEL)
        candidates = [Path(raw).expanduser()]
        if not candidates[0].is_absolute():
            candidates[0] = ROOT / candidates[0]
        for name in ("sam2_t.pt", "sam2_s.pt", "sam2_b.pt"):
            candidate = ROOT / name
            if candidate not in candidates:
                candidates.append(candidate)
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        return None

    def _get_sam2_model(self):
        if self.sam_model is not None:
            return self.sam_model
        weight_path = self._sam2_weight_path()
        if weight_path is None:
            self.sam_model_error = "sam2_t.pt not found"
            raise RuntimeError(self.sam_model_error)
        try:
            from ultralytics import SAM

            self.sam_model = SAM(str(weight_path))
            self.sam_model_path = str(weight_path)
            self.sam_model_error = ""
            return self.sam_model
        except Exception as exc:
            self.sam_model_error = str(exc)
            raise RuntimeError(f"SAM2 load failed: {exc}") from exc

    def _sam2_mask(self, crop: np.ndarray) -> np.ndarray:
        height, width = crop.shape[:2]
        if width < 16 or height < 16:
            raise RuntimeError("crop too small")
        model = self._get_sam2_model()
        pad = max(1, int(min(width, height) * 0.02))
        prompt_box = [[float(pad), float(pad), float(width - pad), float(height - pad)]]
        results = model(crop, bboxes=prompt_box, device=self.device, imgsz=512, verbose=False)
        if not results or results[0].masks is None or len(results[0].masks.data) == 0:
            raise RuntimeError("SAM2 produced no mask")
        data = results[0].masks.data[0].detach().cpu().numpy()
        mask = (data > 0.5).astype("uint8") * 255
        if mask.shape[:2] != (height, width):
            mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
        return mask

    def _rembg_mask(self, crop: np.ndarray) -> np.ndarray:
        try:
            from rembg import remove
        except Exception as exc:
            raise RuntimeError("rembg is not installed") from exc
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        mask = remove(rgb, only_mask=True)
        arr = np.array(mask)
        if arr.ndim == 3:
            if arr.shape[2] == 4:
                arr = arr[:, :, 3]
            else:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return (arr > 10).astype("uint8") * 255

    def _grabcut_mask(self, crop: np.ndarray, iterations: int = 4, max_side: int = 0) -> np.ndarray:
        height, width = crop.shape[:2]
        if width < 16 or height < 16:
            raise RuntimeError("crop too small")
        work = crop
        scale = 1.0
        if max_side and max(width, height) > max_side:
            scale = max_side / float(max(width, height))
            work = cv2.resize(crop, (max(16, int(width * scale)), max(16, int(height * scale))), interpolation=cv2.INTER_AREA)
        work_h, work_w = work.shape[:2]
        pad = max(2, int(min(width, height) * 0.04))
        work_pad = max(2, int(pad * scale))
        rect = (work_pad, work_pad, max(1, work_w - work_pad * 2), max(1, work_h - work_pad * 2))
        mask = np.zeros((work_h, work_w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)
        cv2.grabCut(work, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)
        foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype("uint8")
        kernel = np.ones((3, 3), np.uint8)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel, iterations=1)
        foreground = cv2.morphologyEx(foreground, cv2.MORPH_CLOSE, kernel, iterations=2)
        if foreground.shape[:2] != (height, width):
            foreground = cv2.resize(foreground, (width, height), interpolation=cv2.INTER_NEAREST)
        return foreground

    def _bbox_from_mask(
        self,
        mask: np.ndarray,
        offset_x: int,
        offset_y: int,
        class_id: int,
        full_width: int,
        full_height: int,
        roi_box: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        height, width = mask.shape[:2]
        roi_area = float(width * height)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype("uint8"), 8)
        if num_labels <= 1:
            raise RuntimeError("no foreground mask")
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        x = int(stats[largest, cv2.CC_STAT_LEFT])
        y = int(stats[largest, cv2.CC_STAT_TOP])
        w = int(stats[largest, cv2.CC_STAT_WIDTH])
        h = int(stats[largest, cv2.CC_STAT_HEIGHT])
        area = float(stats[largest, cv2.CC_STAT_AREA])
        mask_area_ratio = area / roi_area
        bbox_area_ratio = float(w * h) / roi_area
        if area < max(64.0, roi_area * 0.01):
            raise RuntimeError(f"mask too small ({mask_area_ratio:.3f})")
        max_mask_ratio = float(getattr(self.args, "max_mask_area", 0.72))
        max_bbox_ratio = float(getattr(self.args, "max_mask_bbox_area", 0.78))
        if mask_area_ratio > max_mask_ratio:
            raise RuntimeError(f"mask too broad ({mask_area_ratio:.3f})")
        if bbox_area_ratio > max_bbox_ratio:
            raise RuntimeError(f"bbox too broad ({bbox_area_ratio:.3f})")
        if bbox_area_ratio < float(getattr(self.args, "min_mask_bbox_area", 0.08)):
            raise RuntimeError(f"bbox too small ({bbox_area_ratio:.3f})")
        if w / float(width) < float(getattr(self.args, "min_mask_bbox_width", 0.12)):
            raise RuntimeError(f"bbox too narrow ({w / float(width):.3f})")
        if h / float(height) < float(getattr(self.args, "min_mask_bbox_height", 0.18)):
            raise RuntimeError(f"bbox too short ({h / float(height):.3f})")
        pad = max(3, int(min(w, h) * 0.06))
        box = {
            "class_id": class_id,
            "x1": offset_x + x - pad,
            "y1": offset_y + y - pad,
            "x2": offset_x + x + w + pad,
            "y2": offset_y + y + h + pad,
        }
        return clamp_box(box, full_width, full_height), {
            "mask_area_ratio": round(mask_area_ratio, 4),
            "bbox_area_ratio": round(bbox_area_ratio, 4),
        }

    def _capture_for(self, split: str, stem: str) -> dict[str, Any]:
        if split not in {"train", "val"}:
            raise RuntimeError("invalid split")
        image_path = self.dataset / "images" / split / f"{stem}.jpg"
        label_path = self.dataset / "labels" / split / f"{stem}.txt"
        if not image_path.exists():
            raise RuntimeError(f"image not found: {image_path}")
        image = cv2.imread(str(image_path))
        if image is None:
            raise RuntimeError(f"cannot read image: {image_path}")
        height, width = image.shape[:2]
        return {
            "split": split,
            "stem": stem,
            "image": str(image_path),
            "label": str(label_path),
            "width": width,
            "height": height,
        }

    def list_items(self) -> dict[str, Any]:
        items = []
        for split in ("train", "val"):
            for image_path in sorted((self.dataset / "images" / split).glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True):
                label_path = self.dataset / "labels" / split / f"{image_path.stem}.txt"
                label_text = label_path.read_text(encoding="utf-8").strip() if label_path.exists() else ""
                items.append({
                    "split": split,
                    "stem": image_path.stem,
                    "name": image_path.name,
                    "image": str(image_path),
                    "label": str(label_path),
                    "labeled": bool(label_text),
                    "negative": image_path.stem.startswith("negative_") and not bool(label_text),
                    "box_count": len([line for line in label_text.splitlines() if line.strip()]),
                    "mtime": image_path.stat().st_mtime,
                })
        return {"items": items}

    def load_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        capture = self._capture_for(str(payload["split"]), str(payload["stem"]))
        label_path = Path(capture["label"])
        boxes = []
        if label_path.exists():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                box = box_from_yolo(line.strip(), int(capture["width"]), int(capture["height"]))
                if box:
                    boxes.append(box)
        self.last_capture = capture
        return {"capture": capture, "boxes": boxes}

    def _review_mask_path(self, split: str, stem: str) -> Path:
        return self.dataset / "review_masks" / split / f"{stem}_mask.jpg"

    def item_mask_jpeg(self, split: str, stem: str, engine: str = "auto") -> bytes:
        capture = self._capture_for(split, stem)
        image_path = Path(capture["image"])
        label_path = Path(capture["label"])
        cache_path = self._review_mask_path(split, stem)
        if engine in {"auto", "cache", "fast"} and cache_path.exists():
            deps = [image_path]
            if label_path.exists():
                deps.append(label_path)
            if cache_path.stat().st_mtime >= max(path.stat().st_mtime for path in deps):
                return cache_path.read_bytes()
        image = cv2.imread(str(capture["image"]))
        if image is None:
            raise RuntimeError(f"cannot read image: {capture['image']}")
        height, width = image.shape[:2]
        boxes = []
        if label_path.exists():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                box = box_from_yolo(line.strip(), width, height)
                if box:
                    boxes.append(box)

        review = (image * 0.16).astype("uint8")
        if not boxes:
            cv2.putText(review, "no label", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (0, 220, 255), 2, cv2.LINE_AA)
        for idx, box in enumerate(boxes):
            roi_box = clamp_box(box, width, height)
            x1, y1, x2, y2, class_id = int_roi(roi_box, width, height)
            crop = image[y1:y2, x1:x2]
            attempts: list[str] = []
            if engine == "auto":
                if self._sam2_weight_path() is not None:
                    attempts.append("sam2")
                if importlib.util.find_spec("rembg") is not None:
                    attempts.append("rembg")
                if not attempts:
                    attempts.append("grabcut")
            elif engine in {"sam2", "rembg", "grabcut"}:
                attempts.append(engine)

            mask = None
            label = "bbox review" if not attempts else "mask failed"
            for candidate in attempts:
                try:
                    candidate_mask = self._roi_mask(crop, candidate)
                    _, meta = self._bbox_from_mask(candidate_mask, x1, y1, class_id, width, height, roi_box=roi_box)
                    mask = candidate_mask
                    label = f"{candidate} {meta.get('mask_area_ratio')}"
                    break
                except Exception as exc:
                    label = f"failed: {str(exc)[:28]}"

            if mask is not None:
                target = review[y1:y2, x1:x2]
                target[mask > 0] = crop[mask > 0]
                edge = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
                target[edge > 0] = (20, 220, 120)
            cv2.rectangle(review, (x1, y1), (x2, y2), (0, 220, 255) if mask is None else (20, 220, 120), 2)
            cv2.putText(review, label, (max(8, x1), max(24, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        ok, buf = cv2.imencode(".jpg", review, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        if not ok:
            raise RuntimeError("jpeg encode failed")
        return bytes(buf)

    def export_mask_reviews(self, engine: str = "auto") -> dict[str, Any]:
        out_root = self.dataset / "review_masks"
        exported = []
        errors = []
        for split in ("train", "val"):
            (out_root / split).mkdir(parents=True, exist_ok=True)
            for image_path in sorted((self.dataset / "images" / split).glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True):
                try:
                    data = self.item_mask_jpeg(split, image_path.stem, engine)
                    out_path = out_root / split / f"{image_path.stem}_mask.jpg"
                    out_path.write_bytes(data)
                    exported.append(str(out_path))
                except Exception as exc:
                    errors.append({"split": split, "stem": image_path.stem, "error": str(exc)})
        return {"dir": str(out_root), "exported": len(exported), "files": exported, "errors": errors}

    def delete_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        capture = self._capture_for(str(payload["split"]), str(payload["stem"]))
        image_path = Path(capture["image"])
        label_path = Path(capture["label"])
        review_mask_path = self._review_mask_path(str(payload["split"]), str(payload["stem"]))
        deleted = []
        for path in (image_path, label_path, review_mask_path):
            if path.exists():
                path.unlink()
                deleted.append(str(path))
        if self.last_capture and self.last_capture.get("image") == str(image_path):
            self.last_capture = None
        return {"deleted": deleted}

    def delete_items(self, payload: dict[str, Any]) -> dict[str, Any]:
        deleted = []
        errors = []
        for item in payload.get("items", []):
            try:
                out = self.delete_item(item)
                deleted.extend(out["deleted"])
            except Exception as exc:
                errors.append({"item": item, "error": str(exc)})
        return {"deleted": deleted, "deleted_files": len(deleted), "errors": errors}

    def stats(self) -> dict[str, Any]:
        out: dict[str, Any] = {"classes": self.classes, "dataset": str(self.dataset), "runs": str(self.runs)}
        for split in ("train", "val"):
            images = list((self.dataset / "images" / split).glob("*.jpg"))
            labels = [p for p in (self.dataset / "labels" / split).glob("*.txt") if p.read_text().strip()]
            negatives = [
                p for p in (self.dataset / "images" / split).glob("negative_*.jpg")
                if (self.dataset / "labels" / split / f"{p.stem}.txt").exists()
                and not (self.dataset / "labels" / split / f"{p.stem}.txt").read_text().strip()
            ]
            out[f"{split}_images"] = len(images)
            out[f"{split}_labeled"] = len(labels)
            out[f"{split}_negative"] = len(negatives)
        out["data_yaml"] = str(self.dataset / "data.yaml")
        out["stream_url"] = self.url
        out["snapshot_url"] = self.snapshot_url
        out["web_stream_url"] = self.web_url
        out["web_snapshot_url"] = self.web_snapshot_url
        out["fast_stream_url"] = self.fast_url
        out["fast_snapshot_url"] = self.fast_snapshot_url
        out["preview_url"] = self.fast_preview_url
        out["device"] = self.device
        latest_best = self.latest_best_pt()
        out["latest_best_pt"] = str(latest_best) if latest_best else ""
        out["auto_label"] = {
            "engine": self.args.auto_label_engine,
            "rembg_available": importlib.util.find_spec("rembg") is not None,
            "sam_available": self._sam2_weight_path() is not None,
            "sam_model": self.sam_model_path,
            "sam_error": self.sam_model_error,
        }
        out["frame_age_sec"] = round(time.time() - self.last_frame_at, 2) if self.last_frame_at else None
        out["train"] = {
            "running": self.train.running,
            "done": self.train.done,
            "returncode": self.train.returncode,
            "best_pt": self.train.best_pt,
            "log_tail": self.train.log[-80:],
        }
        out["detect_model"] = self.detect_model_path
        return out

    def latest_best_pt(self) -> Path | None:
        candidates = [p for p in self.runs.glob("*/weights/best.pt") if p.exists()]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def start_train(self, epochs: int, imgsz: int, model: str) -> dict[str, Any]:
        if self.train.running:
            return {"started": False, "reason": "training already running"}
        stats = self.stats()
        if stats["train_labeled"] < self.args.min_labeled or stats["val_labeled"] < 1:
            return {
                "started": False,
                "reason": f"학습 이미지 라벨 {self.args.min_labeled}장 이상, 검증 이미지 라벨 1장 이상이 필요합니다.",
            }
        self.write_yaml()
        self.train = TrainState(running=True, done=False, log=["[train] starting"])
        thread = threading.Thread(target=self._train_worker, args=(epochs, imgsz, model), daemon=True)
        thread.start()
        return {"started": True}

    def _train_worker(self, epochs: int, imgsz: int, model: str) -> None:
        yolo_bin = Path(sys.executable).parent / "yolo"
        if not yolo_bin.exists():
            yolo_bin = Path("yolo")
        run_name = f"{safe_name(self.classes[0])}_{now_id()}"
        cmd = [
            str(yolo_bin),
            "detect",
            "train",
            f"data={self.dataset / 'data.yaml'}",
            f"model={model}",
            f"epochs={epochs}",
            f"imgsz={imgsz}",
            f"project={self.runs}",
            f"name={run_name}",
            "exist_ok=True",
            f"device={self.device}",
        ]
        self.train.log.append("[cmd] " + " ".join(cmd))
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                self.train.log.append(line.rstrip())
                self.train.log = self.train.log[-500:]
            self.train.returncode = proc.wait()
        except Exception as exc:
            self.train.returncode = 1
            self.train.log.append(f"[error] {exc}")
        best = self.runs / run_name / "weights" / "best.pt"
        if best.exists():
            self.train.best_pt = str(best)
            self.load_detect_model(str(best))
        self.train.running = False
        self.train.done = True
        self.train.log.append(f"[done] returncode={self.train.returncode} best_pt={self.train.best_pt}")

    def load_detect_model(self, path: str) -> dict[str, Any]:
        from ultralytics import YOLO

        model_path = Path(path).expanduser()
        if not model_path.is_absolute():
            model_path = (ROOT / model_path).resolve()
        if not model_path.exists():
            raise RuntimeError(f"model not found: {model_path}")
        self.detect_model = YOLO(str(model_path))
        self.detect_model_path = str(model_path)
        return {"loaded": self.detect_model_path}

    def load_latest_detect_model(self) -> dict[str, Any]:
        latest = self.latest_best_pt()
        if latest is None:
            raise RuntimeError("latest best.pt not found")
        return self.load_detect_model(str(latest))

    def detect_jpeg(self) -> bytes:
        ok, frame = self.read_preview_frame()
        if not ok or frame is None:
            raise RuntimeError("no frame")
        if self.detect_model is None:
            annotated = frame.copy()
        else:
            results = self.detect_model(frame, device=self.device, verbose=False)
            annotated = results[0].plot().copy()
            cv2.putText(annotated, f"fast {Path(self.detect_model_path).name}", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        ok2, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok2:
            raise RuntimeError("jpeg encode failed")
        return bytes(buf)


HTML = r"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>URHYNIX 맞춤 YOLO 학습실</title>
  <style>
    :root { color-scheme: light; --bg:#f6f7f9; --ink:#111827; --muted:#6b7280; --line:#d9dee7; --accent:#0f766e; --warn:#b45309; }
    * { box-sizing:border-box; }
    body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--ink); }
    header { height:56px; display:flex; align-items:center; justify-content:space-between; padding:0 18px; border-bottom:1px solid var(--line); background:white; }
    h1 { font-size:17px; margin:0; font-weight:700; }
    main { display:grid; grid-template-columns:minmax(520px, 1fr) 360px; gap:14px; padding:14px; }
    section, aside { background:white; border:1px solid var(--line); border-radius:8px; }
    .stage { padding:12px; }
    .stageFrame { position:relative; width:100%; aspect-ratio:4/3; background:#111; border-radius:6px; overflow:hidden; }
    .live, canvas { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; display:block; }
    .live { z-index:1; }
    .segmentOverlay { position:absolute; inset:0; width:100%; height:100%; object-fit:contain; display:none; pointer-events:none; z-index:2; }
    canvas { z-index:3; }
    canvas { display:none; }
    .modeBadge { position:absolute; left:10px; top:10px; padding:5px 8px; border-radius:6px; background:rgba(17,24,39,.78); color:white; font-size:12px; font-weight:700; z-index:4; }
    .latencyBadge { position:absolute; right:10px; top:10px; padding:5px 8px; border-radius:6px; background:rgba(17,24,39,.78); color:white; font-size:12px; font-weight:700; z-index:4; }
    .reviewDeleteOverlay { position:absolute; right:12px; bottom:12px; z-index:5; display:none; min-width:86px; height:36px; border-color:#b91c1c; background:rgba(185,28,28,.92); color:white; box-shadow:0 8px 24px rgba(0,0,0,.22); }
    aside { padding:14px; display:flex; flex-direction:column; gap:12px; }
    button, input, select { height:34px; border:1px solid var(--line); border-radius:6px; background:white; padding:0 10px; font:inherit; }
    input[type="checkbox"] { height:auto; width:auto; padding:0; }
    button { cursor:pointer; font-weight:650; }
    button.primary { background:var(--accent); color:white; border-color:var(--accent); }
    button.warn { color:var(--warn); }
    button:disabled { opacity:.45; cursor:not-allowed; }
    .row { display:flex; gap:8px; align-items:center; }
    .row > * { flex:1; }
    .hint { color:var(--muted); font-size:12px; line-height:1.45; }
    .panelTitle { font-weight:750; font-size:13px; margin-bottom:6px; }
    .stats { display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:12px; }
    .stat { padding:8px; background:#f9fafb; border:1px solid #edf0f5; border-radius:6px; }
    .boxes { max-height:130px; overflow:auto; font-size:12px; border:1px solid var(--line); border-radius:6px; padding:6px; }
    .boxItem { display:flex; justify-content:space-between; gap:8px; padding:4px 0; border-bottom:1px solid #edf0f5; }
    .boxItem:last-child { border-bottom:0; }
    .progress { height:8px; border-radius:999px; background:#edf0f5; overflow:hidden; }
    .progress > div { height:100%; width:0%; background:var(--accent); transition:width .15s linear; }
    .itemList { max-height:190px; overflow:auto; border:1px solid var(--line); border-radius:6px; font-size:12px; }
    .item { min-height:38px; border-bottom:1px solid #edf0f5; display:grid; grid-template-columns:20px minmax(0, 1fr) 58px 58px; gap:8px; align-items:center; padding:6px 8px; }
    .item:last-child { border-bottom:0; }
    .item.selected { background:#ecfdf5; }
    .itemName { color:var(--ink); font-weight:650; text-decoration:none; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .itemName:hover { color:var(--accent); text-decoration:underline; }
    .itemEdit, .itemMask { height:28px; padding:0 6px; font-size:12px; }
    a.itemMask { display:flex; align-items:center; justify-content:center; border:1px solid var(--line); border-radius:6px; background:white; color:var(--ink); text-decoration:none; font-weight:650; }
    .badge { color:var(--muted); font-size:11px; white-space:nowrap; }
    .itemMeta { display:flex; gap:6px; margin-top:2px; }
    .stageTools { margin-top:10px; display:flex; gap:8px; }
    .stageTools button { flex:1; }
    .checkRow { margin-top:8px; display:flex; align-items:center; gap:8px; min-height:28px; color:var(--ink); font-size:12px; font-weight:650; }
    pre { margin:0; white-space:pre-wrap; overflow:auto; max-height:210px; padding:10px; background:#111827; color:#e5e7eb; border-radius:6px; font-size:11px; }
    a { color:var(--accent); }
  </style>
</head>
<body>
  <header>
    <h1>URHYNIX 맞춤 YOLO 학습실</h1>
    <div class="hint">스페이스 촬영 · 드래그 박스 · Enter 라벨 저장 · T 학습 · D 탐지 보기 · N 오탐 배경 저장</div>
  </header>
  <main>
    <section class="stage">
      <div class="stageFrame">
        <img id="live" class="live" alt="실시간 카메라" />
        <img id="segmentOverlay" class="segmentOverlay" alt="세그멘테이션 오버레이" />
        <canvas id="canvas" width="640" height="480"></canvas>
        <div id="modeBadge" class="modeBadge">실시간</div>
        <div id="latencyBadge" class="latencyBadge">브라우저 --:--:--</div>
        <button id="reviewDeleteOverlay" class="reviewDeleteOverlay" title="현재 검수 사진 삭제">D 삭제</button>
      </div>
      <div class="stageTools">
        <button id="resumeLive">실시간 다시 보기</button>
        <button id="captureLarge" class="primary">스페이스 촬영</button>
      </div>
    </section>
    <aside>
      <div>
        <div class="panelTitle">촬영과 라벨링</div>
        <div class="row">
          <button id="capture" class="primary">스페이스 촬영</button>
          <button id="save">Enter 저장</button>
          <button id="undo" class="warn">되돌리기</button>
        </div>
        <div class="row" style="margin-top:8px">
          <select id="classSelect"></select>
          <button id="clear">박스 지우기</button>
        </div>
        <p class="hint">캡처 후 아래 캔버스에서 물건을 드래그하세요. 박스가 작으면 저장 때 자동 제외됩니다.</p>
      </div>

      <div>
        <div class="panelTitle">영역 자동 연사</div>
        <div class="row">
          <button id="roiPick">영역 지정</button>
          <button id="burstStart" class="primary">연사 시작</button>
          <button id="burstStop" class="warn">중지</button>
        </div>
        <div class="row" style="margin-top:8px">
          <input id="burstCount" type="number" min="1" max="500" value="100" title="촬영 장수" />
          <input id="burstInterval" type="number" min="100" step="50" value="300" title="촬영 간격 ms" />
        </div>
        <label class="checkRow"><input id="autoTightBox" type="checkbox" checked /> ROI 안 물체 bbox 자동 보정</label>
        <label class="checkRow"><input id="mappedOnlyBox" type="checkbox" checked /> 매핑 성공한 사진만 저장</label>
        <label class="checkRow"><input id="segmentPreview" type="checkbox" /> 실시간 세그 보기</label>
        <div class="progress" style="margin-top:8px"><div id="burstBar"></div></div>
        <p id="burstText" class="hint">실시간 화면 위에서 영역을 드래그한 뒤, 물건을 그 안에서 돌리며 연사하세요. 기본값은 마스크 bbox 성공 컷만 저장하고 fallback 컷은 삭제합니다.</p>
      </div>

      <div>
        <div class="panelTitle">데이터셋</div>
        <div id="stats" class="stats"></div>
      </div>

      <div>
        <div class="panelTitle">촬영 목록</div>
        <div class="row" style="margin-bottom:8px">
          <button id="refreshItems">새로고침</button>
          <button id="reviewStart" class="primary">검수 시작</button>
          <button id="deleteCurrent" class="warn">현재 사진 삭제</button>
        </div>
        <div class="row" style="margin-bottom:8px">
          <button id="exportMasks">마스크 파일 생성</button>
        </div>
        <div class="row" style="margin-bottom:8px">
          <button id="reviewPrev">← 이전</button>
          <button id="reviewDelete" class="warn">현재 삭제</button>
          <button id="reviewNext">다음 →</button>
        </div>
        <div class="row" style="margin-bottom:8px">
          <button id="selectAllItems">전체 선택</button>
          <button id="selectUnlabeledItems">라벨 없음 선택</button>
          <button id="deleteSelected" class="warn">선택 삭제</button>
        </div>
        <div id="itemList" class="itemList"></div>
        <p id="selectedInfo" class="hint">선택 0장</p>
        <p class="hint">파일명을 누르면 원본을 열고, 수정은 라벨 캔버스를 엽니다. 삭제하면 폴더의 사진과 라벨 파일이 같이 없어집니다.</p>
      </div>

      <div>
        <div class="panelTitle">라벨 박스</div>
        <div id="boxes" class="boxes"></div>
      </div>

      <div>
        <div class="panelTitle">학습</div>
        <div class="row">
          <input id="epochs" type="number" min="1" value="30" title="학습 반복 횟수" />
          <input id="imgsz" type="number" min="320" step="32" value="640" title="이미지 크기" />
        </div>
        <div class="row" style="margin-top:8px">
          <input id="baseModel" value="yolov8n.pt" title="기본 모델" />
          <button id="train" class="primary">T 학습 시작</button>
        </div>
      </div>

      <div>
        <div class="panelTitle">탐지</div>
        <div class="row">
          <button id="detect">D 탐지 보기 전환</button>
          <button id="loadBest">best.pt 불러오기</button>
        </div>
        <div class="row" style="margin-top:8px">
          <button id="saveNegative" class="warn">N 오탐 배경 저장</button>
        </div>
        <p id="modelPath" class="hint"></p>
      </div>

      <div>
        <div class="panelTitle">학습 로그</div>
        <pre id="log"></pre>
      </div>
    </aside>
  </main>
<script>
let statusData = {};
let captureData = null;
let capturedImage = null;
let boxes = [];
let drawing = null;
let roiBox = null;
let roiMode = false;
let burstRunning = false;
let burstShouldStop = false;
let detectMode = false;
let labelingMode = false;
let segmentationMode = false;
let items = [];
let selectedItems = new Set();
let reviewMode = false;
let reviewIndex = 0;
let liveTimer = null;
let livePollToken = 0;
let segmentTimer = null;
let segmentPollToken = 0;
let livePollDelayMs = 90;
let segmentPollDelayMs = 520;
let detectPollDelayMs = 80;

const live = document.getElementById('live');
const segmentOverlay = document.getElementById('segmentOverlay');
const canvas = document.getElementById('canvas');
const reviewDeleteOverlay = document.getElementById('reviewDeleteOverlay');
const ctx = canvas.getContext('2d');
const classSelect = document.getElementById('classSelect');

function setReviewDeleteVisible(visible) {
  reviewDeleteOverlay.style.display = visible ? 'block' : 'none';
}
const latencyBadge = document.getElementById('latencyBadge');
const segmentPreview = document.getElementById('segmentPreview');

function updateBrowserClock() {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  const ms = String(now.getMilliseconds()).padStart(3, '0');
  latencyBadge.textContent = `브라우저 ${hh}:${mm}:${ss}.${ms}`;
}
window.setInterval(updateBrowserClock, 100);
updateBrowserClock();

function clearLiveTimer() {
  if (liveTimer) {
    window.clearTimeout(liveTimer);
    liveTimer = null;
  }
}

function stopLivePreview() {
  livePollToken += 1;
  clearLiveTimer();
}

function clearSegmentTimer() {
  if (segmentTimer) {
    window.clearTimeout(segmentTimer);
    segmentTimer = null;
  }
}

function stopSegmentPreview() {
  segmentPollToken += 1;
  clearSegmentTimer();
  segmentOverlay.removeAttribute('src');
  segmentOverlay.dataset.streamKey = '';
  segmentOverlay.style.display = 'none';
}

function showRobotStream() {
  setReviewDeleteVisible(false);
  if (!statusData.preview_url) return;
  const streamKey = `preview:${statusData.preview_url}`;
  if (live.dataset.streamKey === streamKey) return;
  stopLivePreview();
  live.dataset.streamKey = streamKey;
  const token = livePollToken;
  const poll = () => {
    if (token !== livePollToken || labelingMode || detectMode) return;
    const start = performance.now();
    const img = new Image();
    img.onload = () => {
      if (token !== livePollToken || labelingMode || detectMode) return;
      live.src = img.src;
      const elapsed = performance.now() - start;
      liveTimer = window.setTimeout(poll, Math.max(20, livePollDelayMs - elapsed));
    };
    img.onerror = () => {
      if (token !== livePollToken || labelingMode || detectMode) return;
      liveTimer = window.setTimeout(poll, 400);
    };
    const sep = statusData.preview_url.includes('?') ? '&' : '?';
    img.src = statusData.preview_url + sep + 't=' + Date.now();
  };
  poll();
}

function segmentOverlayUrl() {
  const b = roiBox;
  const params = new URLSearchParams({
    x1: String(Math.min(b.x1, b.x2)),
    y1: String(Math.min(b.y1, b.y2)),
    x2: String(Math.max(b.x1, b.x2)),
    y2: String(Math.max(b.y1, b.y2)),
    class_id: String(Number(classSelect.value || b.class_id || 0)),
    engine: statusData.auto_label?.engine || 'auto',
    t: String(Date.now()),
  });
  return `/api/segment_overlay.png?${params.toString()}`;
}

function showSegmentPreview() {
  if (burstRunning) return;
  if (!roiBox) return;
  const streamKey = `segment:${Math.round(roiBox.x1)}:${Math.round(roiBox.y1)}:${Math.round(roiBox.x2)}:${Math.round(roiBox.y2)}`;
  if (segmentOverlay.dataset.streamKey === streamKey) return;
  stopSegmentPreview();
  segmentOverlay.dataset.streamKey = streamKey;
  segmentOverlay.style.display = 'block';
  const token = segmentPollToken;
  const poll = () => {
    if (token !== segmentPollToken || labelingMode || detectMode || !segmentationMode || !roiBox) return;
    const start = performance.now();
    const img = new Image();
    img.onload = () => {
      if (token !== segmentPollToken || labelingMode || detectMode || !segmentationMode) return;
      segmentOverlay.src = img.src;
      segmentOverlay.style.display = 'block';
      const elapsed = performance.now() - start;
      segmentTimer = window.setTimeout(poll, Math.max(80, segmentPollDelayMs - elapsed));
    };
    img.onerror = () => {
      if (token !== segmentPollToken || labelingMode || detectMode || !segmentationMode) return;
      segmentTimer = window.setTimeout(poll, 900);
    };
    img.src = segmentOverlayUrl();
  };
  poll();
}

function refreshDetectFrame() {
  if (labelingMode || !detectMode) return;
  live.src = '/api/detect_frame.jpg?t=' + Date.now();
}

function scheduleDetectFrame() {
  if (!detectMode) return;
  clearLiveTimer();
  if (!labelingMode && detectMode) {
    liveTimer = window.setTimeout(refreshDetectFrame, detectPollDelayMs);
  }
}

live.onload = scheduleDetectFrame;
live.onerror = () => {
  scheduleDetectFrame();
};

async function api(path, body=null) {
  const opts = body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {};
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(await res.text());
  return await res.json();
}

async function refreshStatus() {
  statusData = await api('/api/status');
  if (!labelingMode && !detectMode && !reviewMode) {
    showRobotStream();
    if (segmentationMode && roiBox && !burstRunning) showSegmentPreview();
  }
  classSelect.innerHTML = '';
  statusData.classes.forEach((name, i) => {
    const opt = document.createElement('option');
    opt.value = i; opt.textContent = `${i}: ${name}`;
    classSelect.appendChild(opt);
  });
  document.getElementById('stats').innerHTML = `
    <div class="stat">학습 사진<br><b>${statusData.train_images}</b></div>
    <div class="stat">학습 라벨<br><b>${statusData.train_labeled}</b></div>
    <div class="stat">검증 사진<br><b>${statusData.val_images}</b></div>
    <div class="stat">검증 라벨<br><b>${statusData.val_labeled}</b></div>
    <div class="stat">배경 학습<br><b>${statusData.train_negative || 0}</b></div>
    <div class="stat">배경 검증<br><b>${statusData.val_negative || 0}</b></div>
    <div class="stat">연산 장치<br><b>${statusData.device}</b></div>
    <div class="stat">클래스<br><b>${statusData.classes.join(', ')}</b></div>
    <div class="stat">자동 보정<br><b>${autoLabelText()}</b></div>`;
  document.getElementById('modelPath').textContent = statusData.detect_model || statusData.train.best_pt || (statusData.latest_best_pt ? `최신 best.pt 대기: ${statusData.latest_best_pt}` : '아직 맞춤 모델이 없습니다.');
  document.getElementById('log').textContent = (statusData.train.log_tail || []).join('\n');
}
setInterval(refreshStatus, 2000);
refreshStatus();

function esc(value) {
  return String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}

function autoLabelText() {
  const state = statusData.auto_label || {};
  if (state.rembg_available) return `${state.engine} / rembg`;
  if (state.sam_available) return `${state.engine} / SAM`;
  return `${state.engine} / GrabCut`;
}

async function refreshItems() {
  const data = await api('/api/items');
  items = data.items || [];
  renderItems();
}

function renderItems() {
  const current = captureData ? `${captureData.split}/${captureData.stem}` : '';
  selectedItems = new Set([...selectedItems].filter(key => items.some(item => `${item.split}/${item.stem}` === key)));
  document.getElementById('itemList').innerHTML = items.map(item => {
    const key = `${item.split}/${item.stem}`;
    const selected = key === current ? ' selected' : '';
    const splitName = item.split === 'train' ? '학습' : '검증';
    const label = item.negative ? '배경 학습' : (item.labeled ? `라벨 ${item.box_count}` : '라벨 없음');
    const imageUrl = `/api/item_image?split=${encodeURIComponent(item.split)}&stem=${encodeURIComponent(item.stem)}`;
    const maskUrl = `/api/item_mask_image?split=${encodeURIComponent(item.split)}&stem=${encodeURIComponent(item.stem)}&engine=cache`;
    return `<div class="item${selected}" data-split="${esc(item.split)}" data-stem="${esc(item.stem)}">
      <input class="itemCheck" type="checkbox" data-key="${esc(key)}" ${selectedItems.has(key) ? 'checked' : ''} />
      <div>
        <a class="itemName" href="${imageUrl}" target="_blank" rel="noopener">${esc(item.name)}</a>
        <div class="itemMeta"><span class="badge">${splitName}</span><span class="badge">${label}</span></div>
      </div>
      <a class="itemMask" href="${maskUrl}" data-key="${esc(key)}" target="_blank" rel="noopener">마스크</a>
      <button class="itemEdit" data-split="${esc(item.split)}" data-stem="${esc(item.stem)}">수정</button>
    </div>`;
  }).join('') || '<div class="hint" style="padding:8px">아직 촬영한 사진이 없습니다.</div>';
  document.querySelectorAll('.itemEdit').forEach(btn => {
    btn.onclick = () => loadItem(btn.dataset.split, btn.dataset.stem);
  });
  document.querySelectorAll('.itemMask').forEach(link => {
    link.onclick = (evt) => {
      evt.preventDefault();
      const idx = items.findIndex(item => `${item.split}/${item.stem}` === link.dataset.key);
      showReviewAt(idx >= 0 ? idx : 0);
    };
  });
  document.querySelectorAll('.itemCheck').forEach(input => {
    input.onchange = () => {
      if (input.checked) selectedItems.add(input.dataset.key);
      else selectedItems.delete(input.dataset.key);
      updateSelectedInfo();
    };
  });
  updateSelectedInfo();
}

function updateSelectedInfo() {
  const count = selectedItems.size;
  const deleteBtn = document.getElementById('deleteSelected');
  deleteBtn.disabled = count === 0;
  document.getElementById('selectedInfo').textContent = `선택 ${count}장`;
}

function reviewItemUrl(item) {
  return `/api/item_mask_image?split=${encodeURIComponent(item.split)}&stem=${encodeURIComponent(item.stem)}&engine=cache&t=${Date.now()}`;
}

async function showReviewAt(index) {
  if (!items.length) {
    alert('검수할 사진이 없습니다.');
    return;
  }
  reviewMode = true;
  detectMode = false;
  labelingMode = false;
  stopLivePreview();
  stopSegmentPreview();
  reviewIndex = Math.max(0, Math.min(items.length - 1, index));
  const item = items[reviewIndex];
  captureData = {split:item.split, stem:item.stem};
  live.style.display = 'block';
  canvas.style.display = 'none';
  canvas.style.pointerEvents = 'none';
  live.dataset.streamKey = `review:${item.split}:${item.stem}`;
  live.src = reviewItemUrl(item);
  window.scrollTo({top: 0, behavior: 'auto'});
  setReviewDeleteVisible(true);
  document.getElementById('modeBadge').textContent = `검수 ${reviewIndex + 1}/${items.length}`;
  document.getElementById('burstText').textContent = `${item.name} · ←/→ 이동 · D/Delete 현재 사진 삭제`;
  renderItems();
}

function startReview() {
  const currentKey = captureData ? `${captureData.split}/${captureData.stem}` : '';
  const idx = Math.max(0, items.findIndex(item => `${item.split}/${item.stem}` === currentKey));
  showReviewAt(idx);
}

function reviewMove(delta) {
  if (!reviewMode) return;
  showReviewAt(reviewIndex + delta);
}

async function reviewDeleteCurrent() {
  if (!reviewMode || !items[reviewIndex]) return;
  const item = items[reviewIndex];
  if (!confirm(`현재 검수 사진을 삭제할까요?\n${item.name}`)) return;
  await api('/api/delete_item', {split:item.split, stem:item.stem});
  selectedItems.delete(`${item.split}/${item.stem}`);
  await refreshStatus();
  await refreshItems();
  if (!items.length) {
    reviewMode = false;
    setReviewDeleteVisible(false);
    live.dataset.streamKey = '';
    showRobotStream();
    document.getElementById('modeBadge').textContent = '실시간';
    return;
  }
  showReviewAt(Math.min(reviewIndex, items.length - 1));
}

function selectAllItems() {
  if (selectedItems.size === items.length) selectedItems.clear();
  else selectedItems = new Set(items.map(item => `${item.split}/${item.stem}`));
  renderItems();
}

function selectUnlabeledItems() {
  selectedItems = new Set(items.filter(item => !item.labeled && !item.negative).map(item => `${item.split}/${item.stem}`));
  renderItems();
}

async function deleteSelectedItems() {
  const selected = items.filter(item => selectedItems.has(`${item.split}/${item.stem}`));
  if (!selected.length) return alert('삭제할 사진을 선택하세요.');
  if (!confirm(`선택한 ${selected.length}장의 사진과 라벨 파일을 폴더에서 삭제할까요?`)) return;
  const payload = selected.map(item => ({split:item.split, stem:item.stem}));
  const out = await api('/api/delete_items', {items:payload});
  if (out.errors && out.errors.length) alert(`일부 삭제 실패: ${out.errors.length}건`);
  selectedItems.clear();
  captureData = null;
  capturedImage = null;
  boxes = [];
  drawCanvas();
  setLabelingMode(false);
  await refreshStatus();
  await refreshItems();
}

function drawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (capturedImage) ctx.drawImage(capturedImage, 0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 3;
  ctx.font = '16px system-ui';
  [...boxes, drawing].filter(Boolean).forEach((b, idx) => {
    const x = Math.min(b.x1, b.x2), y = Math.min(b.y1, b.y2);
    const w = Math.abs(b.x2 - b.x1), h = Math.abs(b.y2 - b.y1);
    ctx.strokeStyle = idx === boxes.length ? '#f59e0b' : '#14b8a6';
    ctx.fillStyle = ctx.strokeStyle;
    ctx.strokeRect(x, y, w, h);
    const label = statusData.classes?.[b.class_id] || '물체';
    ctx.fillText(label, x + 5, Math.max(18, y - 6));
  });
  document.getElementById('boxes').innerHTML = boxes.map((b, i) => {
    const label = statusData.classes?.[b.class_id] || '물체';
    return `<div class="boxItem"><span>${i+1}. ${label}</span><span>${Math.round(Math.abs(b.x2-b.x1))}x${Math.round(Math.abs(b.y2-b.y1))}</span></div>`;
  }).join('') || '<span class="hint">아직 박스가 없습니다.</span>';
}

function drawLiveOverlay() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const active = drawing || roiBox;
  if (!active) return;
  const x = Math.min(active.x1, active.x2), y = Math.min(active.y1, active.y2);
  const w = Math.abs(active.x2 - active.x1), h = Math.abs(active.y2 - active.y1);
  ctx.save();
  ctx.fillStyle = 'rgba(15, 118, 110, 0.12)';
  ctx.strokeStyle = roiMode ? '#f59e0b' : '#14b8a6';
  ctx.lineWidth = 3;
  ctx.fillRect(x, y, w, h);
  ctx.strokeRect(x, y, w, h);
  ctx.font = '18px system-ui';
  ctx.fillStyle = ctx.strokeStyle;
  ctx.fillText('자동 라벨 영역', x + 6, Math.max(22, y - 8));
  ctx.restore();
}

function refreshLiveCanvasOverlay() {
  if (labelingMode) return;
  const show = roiMode || !!roiBox;
  canvas.style.display = show ? 'block' : 'none';
  canvas.style.pointerEvents = roiMode ? 'auto' : 'none';
  if (show) drawLiveOverlay();
}

function setRoiMode(on) {
  roiMode = on;
  if (on) {
    labelingMode = false;
    capturedImage = null;
    boxes = [];
    live.style.display = 'block';
    document.getElementById('modeBadge').textContent = '영역 지정';
    showRobotStream();
  } else if (!labelingMode && !detectMode) {
    document.getElementById('modeBadge').textContent = segmentationMode && roiBox ? '세그 보기' : '실시간';
    live.dataset.streamKey = '';
    showRobotStream();
    if (segmentationMode && roiBox && !burstRunning) showSegmentPreview();
  }
  refreshLiveCanvasOverlay();
}

function setLabelingMode(on) {
  labelingMode = on;
  if (on) reviewMode = false;
  if (on) setReviewDeleteVisible(false);
  if (on) {
    stopLivePreview();
    stopSegmentPreview();
  }
  else clearLiveTimer();
  canvas.style.display = on ? 'block' : 'none';
  canvas.style.pointerEvents = on ? 'auto' : 'none';
  live.style.display = on ? 'none' : 'block';
  document.getElementById('modeBadge').textContent = on ? '라벨 수정' : (detectMode ? '탐지 보기' : (segmentationMode && roiBox ? '세그 보기' : '실시간'));
  if (!on) {
    live.dataset.streamKey = '';
    if (detectMode) refreshDetectFrame();
    else {
      showRobotStream();
      if (segmentationMode && roiBox && !burstRunning) showSegmentPreview();
    }
    refreshLiveCanvasOverlay();
  }
}

function canvasPoint(evt) {
  const rect = canvas.getBoundingClientRect();
  return {x:(evt.clientX - rect.left) * canvas.width / rect.width, y:(evt.clientY - rect.top) * canvas.height / rect.height};
}

canvas.addEventListener('mousedown', (evt) => {
  if (roiMode) {
    const p = canvasPoint(evt);
    drawing = {x1:p.x, y1:p.y, x2:p.x, y2:p.y, class_id: Number(classSelect.value || 0)};
    drawLiveOverlay();
    return;
  }
  if (!capturedImage) return;
  const p = canvasPoint(evt);
  drawing = {x1:p.x, y1:p.y, x2:p.x, y2:p.y, class_id: Number(classSelect.value || 0)};
  drawCanvas();
});
canvas.addEventListener('mousemove', (evt) => {
  if (!drawing) return;
  const p = canvasPoint(evt);
  drawing.x2 = p.x; drawing.y2 = p.y;
  if (roiMode) {
    drawLiveOverlay();
    return;
  }
  drawCanvas();
});
canvas.addEventListener('mouseup', () => {
  if (!drawing) return;
  if (roiMode) {
    if (Math.abs(drawing.x2 - drawing.x1) >= 8 && Math.abs(drawing.y2 - drawing.y1) >= 8) {
      roiBox = drawing;
      document.getElementById('burstText').textContent = `영역 지정됨: ${Math.round(Math.abs(roiBox.x2-roiBox.x1))}x${Math.round(Math.abs(roiBox.y2-roiBox.y1))}. 물건을 영역 안에서 돌리며 연사 시작을 누르세요.`;
    }
    drawing = null;
    setRoiMode(false);
    refreshLiveCanvasOverlay();
    return;
  }
  if (Math.abs(drawing.x2 - drawing.x1) >= 4 && Math.abs(drawing.y2 - drawing.y1) >= 4) boxes.push(drawing);
  drawing = null;
  drawCanvas();
});

async function capture(openLabel=false) {
  captureData = await api('/api/capture', {});
  boxes = [];
  await refreshStatus();
  await refreshItems();
  if (openLabel) {
    capturedImage = new Image();
    capturedImage.onload = () => { setLabelingMode(true); drawCanvas(); };
    capturedImage.src = '/api/captured_image?t=' + Date.now();
    return;
  }
  capturedImage = null;
  drawCanvas();
  setLabelingMode(false);
  const badge = document.getElementById('modeBadge');
  badge.textContent = '촬영 저장';
  window.setTimeout(() => {
    if (!labelingMode && !detectMode) badge.textContent = '실시간';
  }, 700);
}

function sleep(ms) {
  return new Promise(resolve => window.setTimeout(resolve, ms));
}

function setBurstProgress(done, total, text) {
  const pct = total ? Math.round(done * 100 / total) : 0;
  document.getElementById('burstBar').style.width = `${pct}%`;
  document.getElementById('burstText').textContent = text;
}

async function startBurst() {
  if (burstRunning) return;
  if (!roiBox) {
    alert('먼저 영역 지정을 눌러 물건이 들어갈 영역을 드래그하세요.');
    setRoiMode(true);
    return;
  }
  const total = Math.max(1, Math.min(500, Number(document.getElementById('burstCount').value || 100)));
  const interval = Math.max(100, Number(document.getElementById('burstInterval').value || 300));
  const useAutoTight = document.getElementById('autoTightBox').checked;
  const mappedOnly = useAutoTight && document.getElementById('mappedOnlyBox').checked;
  const maxAttempts = mappedOnly ? Math.max(total + 20, Math.ceil(total * 2.5)) : total;
  burstRunning = true;
  burstShouldStop = false;
  document.getElementById('burstStart').disabled = true;
  document.getElementById('burstStop').disabled = false;
  setRoiMode(false);
  stopSegmentPreview();
  live.dataset.streamKey = '';
  showRobotStream();
  document.getElementById('modeBadge').textContent = '연사 중';
  setBurstProgress(0, total, `연사 준비 중... 세그 오버레이는 일시정지하고 원본 실시간만 유지합니다. 0/${total}`);
  let saved = 0;
  let tightened = 0;
  let fallback = 0;
  let discarded = 0;
  let attempts = 0;
  try {
    while (saved < total && attempts < maxAttempts) {
      if (burstShouldStop) break;
      attempts += 1;
      const cap = await api('/api/capture', {});
      const box = {...roiBox, class_id: Number(classSelect.value || 0)};
      const labelOut = useAutoTight
        ? await api('/api/auto_label_roi', {capture:cap, roi:box})
        : await api('/api/save_labels', {capture:cap, boxes:[box]});
      if (useAutoTight) {
        if (labelOut.fallback) {
          fallback += 1;
          if (mappedOnly) {
            await api('/api/delete_item', {split:cap.split, stem:cap.stem});
            discarded += 1;
            setBurstProgress(saved, total, `매핑 실패 컷 삭제 ${discarded} · 저장 ${saved}/${total} · 시도 ${attempts}/${maxAttempts}`);
            await sleep(interval);
            continue;
          }
        } else {
          tightened += 1;
        }
      }
      captureData = cap;
      saved += 1;
      const suffix = useAutoTight ? ` · bbox 보정 ${tightened} · fallback ${fallback} · 삭제 ${discarded}` : '';
      setBurstProgress(saved, total, `자동 촬영/라벨 저장 ${saved}/${total} · 시도 ${attempts}/${maxAttempts}${suffix}`);
      await sleep(interval);
    }
  } catch (err) {
    alert(`연사 중 오류: ${err.message || err}`);
  } finally {
    burstRunning = false;
    burstShouldStop = false;
    document.getElementById('burstStart').disabled = false;
    document.getElementById('burstStop').disabled = false;
    await refreshStatus();
    await refreshItems();
    setLabelingMode(false);
    if (segmentationMode && roiBox) showSegmentPreview();
    const suffix = useAutoTight ? ` · bbox 보정 ${tightened} · fallback ${fallback} · 삭제 ${discarded} · 시도 ${attempts}/${maxAttempts}` : '';
    const prefix = saved >= total ? '완료' : '중단';
    setBurstProgress(saved, total, `${prefix}: ${saved}/${total}장 저장 및 자동 라벨링${suffix}`);
  }
}

async function saveLabels() {
  if (!captureData) return alert('먼저 사진을 촬영하세요.');
  const out = await api('/api/save_labels', {capture:captureData, boxes});
  await refreshStatus();
  await refreshItems();
  alert(`라벨 박스 ${out.saved}개를 저장했습니다.`);
}

async function loadItem(split, stem) {
  const data = await api('/api/load_item', {split, stem});
  captureData = data.capture;
  boxes = data.boxes || [];
  capturedImage = new Image();
  capturedImage.onload = () => { setLabelingMode(true); drawCanvas(); };
  capturedImage.src = `/api/item_image?split=${encodeURIComponent(split)}&stem=${encodeURIComponent(stem)}&t=${Date.now()}`;
  renderItems();
}

async function deleteCurrent() {
  if (!captureData) return alert('삭제할 사진을 먼저 선택하세요.');
  if (!confirm('현재 사진과 라벨 파일을 폴더에서 삭제할까요?')) return;
  await api('/api/delete_item', {split:captureData.split, stem:captureData.stem});
  captureData = null;
  capturedImage = null;
  boxes = [];
  drawCanvas();
  setLabelingMode(false);
  await refreshStatus();
  await refreshItems();
}

async function startTrain() {
  const out = await api('/api/train', {epochs:Number(document.getElementById('epochs').value), imgsz:Number(document.getElementById('imgsz').value), model:document.getElementById('baseModel').value});
  if (!out.started) alert(out.reason);
  await refreshStatus();
}

async function loadBest() {
  await api('/api/load_latest_model', {});
  detectMode = true;
  await refreshStatus();
  live.dataset.streamKey = '';
  setLabelingMode(false);
}

async function saveNegative() {
  const btn = document.getElementById('saveNegative');
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = '저장 중...';
  try {
    const out = await api('/api/save_negative_frame', {split:'auto'});
    document.getElementById('burstText').textContent = `오탐 배경 저장: ${out.split === 'train' ? '학습' : '검증'} / ${out.stem}.jpg`;
    await refreshStatus();
    await refreshItems();
  } catch (err) {
    alert(`오탐 배경 저장 실패: ${err.message || err}`);
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

async function exportMasks() {
  const btn = document.getElementById('exportMasks');
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = '생성 중...';
  try {
    const out = await api('/api/export_mask_reviews', {engine:'auto'});
    alert(`마스크 검수 이미지 ${out.exported}장을 생성했습니다.\n${out.dir}`);
  } catch (err) {
    alert(`마스크 파일 생성 실패: ${err.message || err}`);
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

document.getElementById('capture').onclick = capture;
document.getElementById('captureLarge').onclick = capture;
document.getElementById('resumeLive').onclick = () => { reviewMode = false; live.dataset.streamKey = ''; setLabelingMode(false); };
document.getElementById('roiPick').onclick = () => setRoiMode(true);
segmentPreview.onchange = () => {
  segmentationMode = segmentPreview.checked;
  if (segmentationMode && !roiBox) {
    alert('먼저 영역 지정을 눌러 세그멘테이션을 볼 영역을 드래그하세요.');
    segmentPreview.checked = false;
    segmentationMode = false;
    setRoiMode(true);
    return;
  }
  live.dataset.streamKey = '';
  document.getElementById('modeBadge').textContent = segmentationMode ? '세그 보기' : '실시간';
  if (!segmentationMode) stopSegmentPreview();
  setLabelingMode(false);
};
document.getElementById('burstStart').onclick = startBurst;
document.getElementById('burstStop').onclick = () => {
  burstShouldStop = true;
  document.getElementById('burstText').textContent = '중지 요청됨... 현재 저장 중인 사진까지만 마무리합니다.';
};
document.getElementById('save').onclick = saveLabels;
document.getElementById('undo').onclick = () => { boxes.pop(); drawCanvas(); };
document.getElementById('clear').onclick = () => { boxes = []; drawCanvas(); };
document.getElementById('refreshItems').onclick = refreshItems;
document.getElementById('exportMasks').onclick = exportMasks;
document.getElementById('reviewStart').onclick = startReview;
document.getElementById('reviewPrev').onclick = () => reviewMove(-1);
document.getElementById('reviewNext').onclick = () => reviewMove(1);
document.getElementById('reviewDelete').onclick = reviewDeleteCurrent;
reviewDeleteOverlay.onclick = reviewDeleteCurrent;
document.getElementById('deleteCurrent').onclick = deleteCurrent;
document.getElementById('selectAllItems').onclick = selectAllItems;
document.getElementById('selectUnlabeledItems').onclick = selectUnlabeledItems;
document.getElementById('deleteSelected').onclick = deleteSelectedItems;
document.getElementById('train').onclick = startTrain;
document.getElementById('detect').onclick = () => { detectMode = !detectMode; setLabelingMode(false); };
document.getElementById('loadBest').onclick = loadBest;
document.getElementById('saveNegative').onclick = saveNegative;

window.addEventListener('keydown', (evt) => {
  if (evt.target.tagName === 'INPUT') return;
  if (reviewMode) {
    if (evt.key === 'ArrowLeft') { evt.preventDefault(); reviewMove(-1); return; }
    if (evt.key === 'ArrowRight') { evt.preventDefault(); reviewMove(1); return; }
    if (evt.key === 'Delete' || evt.key === 'Backspace') { evt.preventDefault(); reviewDeleteCurrent(); return; }
    if (evt.key.toLowerCase() === 'd') { evt.preventDefault(); reviewDeleteCurrent(); return; }
    if (evt.key === 'Escape') { evt.preventDefault(); reviewMode = false; setReviewDeleteVisible(false); live.dataset.streamKey = ''; showRobotStream(); document.getElementById('modeBadge').textContent = '실시간'; return; }
  }
  if (evt.code === 'Space') { evt.preventDefault(); capture(); }
  if (evt.code === 'Enter') { evt.preventDefault(); saveLabels(); }
  if (evt.key.toLowerCase() === 't') startTrain();
  if (evt.key.toLowerCase() === 'd') { detectMode = !detectMode; setLabelingMode(false); }
  if (evt.key.toLowerCase() === 'n') { evt.preventDefault(); saveNegative(); }
  if (evt.key.toLowerCase() === 'z') { boxes.pop(); drawCanvas(); }
});
refreshItems();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    state: StudioState

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[web] " + fmt % args + "\n")

    def _send(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        try:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            return

    def _json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send(json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8", status)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _proxy_live_mjpeg(self) -> None:
        upstream = urllib.request.urlopen(self.state.url, timeout=5)
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", upstream.headers.get("Content-Type", "multipart/x-mixed-replace"))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                chunk = upstream.read(32768)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        finally:
            upstream.close()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._send(HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif parsed.path == "/favicon.ico":
                self._send(b"", "image/x-icon")
            elif parsed.path == "/api/live.mjpg":
                self._proxy_live_mjpeg()
            elif parsed.path == "/api/status":
                self._json(self.state.stats())
            elif parsed.path == "/api/items":
                self._json(self.state.list_items())
            elif parsed.path == "/api/frame.jpg":
                ok, frame = self.state.read_frame()
                if not ok or frame is None:
                    raise RuntimeError("no frame")
                ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if not ok2:
                    raise RuntimeError("jpeg encode failed")
                self._send(bytes(buf), "image/jpeg")
            elif parsed.path == "/api/detect_frame.jpg":
                self._send(self.state.detect_jpeg(), "image/jpeg")
            elif parsed.path == "/api/segment_frame.jpg":
                query = parse_qs(parsed.query)
                roi = {
                    "x1": float(query.get("x1", ["0"])[0]),
                    "y1": float(query.get("y1", ["0"])[0]),
                    "x2": float(query.get("x2", ["0"])[0]),
                    "y2": float(query.get("y2", ["0"])[0]),
                    "class_id": int(float(query.get("class_id", ["0"])[0])),
                }
                engine = query.get("engine", [self.state.args.auto_label_engine])[0]
                self._send(self.state.segment_jpeg(roi, engine), "image/jpeg")
            elif parsed.path == "/api/segment_overlay.png":
                query = parse_qs(parsed.query)
                roi = {
                    "x1": float(query.get("x1", ["0"])[0]),
                    "y1": float(query.get("y1", ["0"])[0]),
                    "x2": float(query.get("x2", ["0"])[0]),
                    "y2": float(query.get("y2", ["0"])[0]),
                    "class_id": int(float(query.get("class_id", ["0"])[0])),
                }
                engine = query.get("engine", [self.state.args.auto_label_engine])[0]
                self._send(self.state.segment_overlay_png(roi, engine), "image/png")
            elif parsed.path == "/api/captured_image":
                if not self.state.last_capture:
                    raise RuntimeError("no captured image")
                data = Path(self.state.last_capture["image"]).read_bytes()
                self._send(data, "image/jpeg")
            elif parsed.path == "/api/item_image":
                query = parse_qs(parsed.query)
                capture = self.state._capture_for(query.get("split", [""])[0], query.get("stem", [""])[0])
                self._send(Path(capture["image"]).read_bytes(), "image/jpeg")
            elif parsed.path == "/api/item_mask_image":
                query = parse_qs(parsed.query)
                engine = query.get("engine", [self.state.args.auto_label_engine])[0]
                self._send(
                    self.state.item_mask_jpeg(query.get("split", [""])[0], query.get("stem", [""])[0], engine),
                    "image/jpeg",
                )
            else:
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            body = self._read_json()
            if parsed.path == "/api/capture":
                self._json(self.state.capture())
            elif parsed.path == "/api/save_negative_frame":
                self._json(self.state.save_negative_frame(body))
            elif parsed.path == "/api/save_labels":
                self._json(self.state.save_labels(body))
            elif parsed.path == "/api/auto_label_roi":
                self._json(self.state.auto_label_roi(body))
            elif parsed.path == "/api/load_item":
                self._json(self.state.load_item(body))
            elif parsed.path == "/api/delete_item":
                self._json(self.state.delete_item(body))
            elif parsed.path == "/api/delete_items":
                self._json(self.state.delete_items(body))
            elif parsed.path == "/api/export_mask_reviews":
                self._json(self.state.export_mask_reviews(str(body.get("engine", self.state.args.auto_label_engine))))
            elif parsed.path == "/api/train":
                self._json(self.state.start_train(int(body.get("epochs", 30)), int(body.get("imgsz", 640)), str(body.get("model", "yolov8n.pt"))))
            elif parsed.path == "/api/load_model":
                self._json(self.state.load_detect_model(str(body["path"])))
            elif parsed.path == "/api/load_latest_model":
                self._json(self.state.load_latest_detect_model())
            else:
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="URHYNIX RealSense custom YOLO labeling studio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=8766)
    parser.add_argument("--t1-ip", default=os.environ.get("T1_IP", "192.168.10.250"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("T1_PORT", "8080")))
    parser.add_argument("--fast-port", type=int, default=int(os.environ.get("T1_FAST_PORT", "8090")))
    parser.add_argument("--prefer-fast-stream", action=argparse.BooleanOptionalAction, default=os.environ.get("YOLO_PREFER_FAST_STREAM", "1") != "0")
    parser.add_argument("--topic", default=os.environ.get("T1_TOPIC", DEFAULT_TOPIC))
    parser.add_argument("--compressed-topic", default=os.environ.get("T1_COMPRESSED_TOPIC", DEFAULT_COMPRESSED_TOPIC))
    parser.add_argument("--classes", default=os.environ.get("YOLO_CLASSES", "학습대상"))
    parser.add_argument("--dataset", default=os.environ.get("YOLO_DATASET", str(DEFAULT_DATASET)))
    parser.add_argument("--runs", default=os.environ.get("YOLO_RUNS", str(DEFAULT_RUNS)))
    parser.add_argument("--val-every", type=int, default=int(os.environ.get("YOLO_VAL_EVERY", "5")))
    parser.add_argument("--min-labeled", type=int, default=int(os.environ.get("YOLO_MIN_LABELED", "5")))
    parser.add_argument("--live-fps", type=int, default=int(os.environ.get("YOLO_LIVE_FPS", "12")))
    parser.add_argument("--auto-label-engine", choices=("auto", "sam2", "rembg", "grabcut", "roi"), default=os.environ.get("YOLO_AUTO_LABEL_ENGINE", "auto"))
    parser.add_argument("--sam2-model", default=os.environ.get("YOLO_SAM2_MODEL", str(DEFAULT_SAM2_MODEL)))
    parser.add_argument("--min-mask-bbox-area", type=float, default=float(os.environ.get("YOLO_MIN_MASK_BBOX_AREA", "0.08")))
    parser.add_argument("--min-mask-bbox-width", type=float, default=float(os.environ.get("YOLO_MIN_MASK_BBOX_WIDTH", "0.12")))
    parser.add_argument("--min-mask-bbox-height", type=float, default=float(os.environ.get("YOLO_MIN_MASK_BBOX_HEIGHT", "0.18")))
    parser.add_argument("--max-mask-area", type=float, default=float(os.environ.get("YOLO_MAX_MASK_AREA", "0.72")))
    parser.add_argument("--max-mask-bbox-area", type=float, default=float(os.environ.get("YOLO_MAX_MASK_BBOX_AREA", "0.78")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = StudioState(args)
    Handler.state = state
    server = ThreadingHTTPServer((args.host, args.listen_port), Handler)
    print(f"[stream] {state.url}")
    print(f"[dataset] {state.dataset}")
    print(f"[classes] {state.classes}")
    print(f"[open] http://{args.host}:{args.listen_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[bye]")
    finally:
        state.stop_capture = True
        if state.cap is not None:
            state.cap.release()
        server.server_close()


if __name__ == "__main__":
    main()
