#!/usr/bin/env python3
"""Serve a ROS2 CompressedImage topic as low-latency MJPEG and snapshots."""
from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage


class FrameStore:
    def __init__(self, stream_width: int, stream_quality: int, preview_fps: int) -> None:
        self.lock = threading.Lock()
        self.data: bytes | None = None
        self.preview: bytes | None = None
        self.stamp = 0.0
        self.preview_stamp = 0.0
        self.count = 0
        self.stream_width = stream_width
        self.stream_quality = stream_quality
        self.preview_interval = 1.0 / max(1, preview_fps)

    def update(self, data: bytes) -> None:
        now = time.time()
        preview = None
        if self.stream_width > 0 and now - self.preview_stamp >= self.preview_interval:
            arr = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
            if arr is not None:
                height, width = arr.shape[:2]
                if width > self.stream_width:
                    scale = self.stream_width / width
                    arr = cv2.resize(arr, (self.stream_width, max(1, int(height * scale))), interpolation=cv2.INTER_AREA)
                stamp_text = time.strftime("T1 %H:%M:%S", time.localtime(now)) + f".{int((now % 1) * 1000):03d}"
                age_text = f"#{self.count + 1}"
                cv2.rectangle(arr, (4, 4), (min(arr.shape[1] - 4, 168), 34), (0, 0, 0), -1)
                cv2.putText(arr, stamp_text, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(arr, age_text, (8, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 255, 180), 1, cv2.LINE_AA)
                ok, buf = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), self.stream_quality])
                if ok:
                    preview = bytes(buf)
        with self.lock:
            self.data = data
            if preview is not None:
                self.preview = preview
                self.preview_stamp = now
            elif self.preview is None:
                self.preview = data
                self.preview_stamp = now
            self.stamp = now
            self.count += 1

    def latest(self, *, preview: bool = False) -> tuple[bytes | None, float, int]:
        with self.lock:
            stamp = self.preview_stamp if preview else self.stamp
            return (self.preview if preview else self.data), stamp, self.count


class CompressedImageNode(Node):
    def __init__(self, topic: str, store: FrameStore) -> None:
        super().__init__("urhynix_compressed_mjpeg_server")
        self.store = store
        self.create_subscription(CompressedImage, topic, self._on_image, qos_profile_sensor_data)
        self.get_logger().info(f"serving compressed image topic: {topic}")

    def _on_image(self, msg: CompressedImage) -> None:
        self.store.update(bytes(msg.data))


def make_handler(store: FrameStore, max_fps: int) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            return

        def _json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path.startswith("/status"):
                data, stamp, count = store.latest()
                self._json({"ok": data is not None, "age_sec": round(time.time() - stamp, 3) if stamp else None, "count": count})
                return
            if self.path.startswith("/snapshot.jpg"):
                data, stamp, _ = store.latest()
                if data is None or time.time() - stamp > 3:
                    self._json({"error": "no fresh frame"}, HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path.startswith("/preview.jpg"):
                data, stamp, _ = store.latest(preview=True)
                if data is None or time.time() - stamp > 3:
                    self._json({"error": "no fresh frame"}, HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if not self.path.startswith("/stream.mjpg"):
                self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            interval = 1.0 / max(1, max_fps)
            try:
                while True:
                    data, stamp, count = store.latest(preview=True)
                    if data is None or time.time() - stamp > 3:
                        time.sleep(0.01)
                        continue
                    self.wfile.write(
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        + f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
                        + data
                        + b"\r\n"
                    )
                    self.wfile.flush()
                    time.sleep(interval)
            except (BrokenPipeError, ConnectionResetError):
                return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="/camera/camera/color/image_raw/compressed")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--max-fps", type=int, default=20)
    parser.add_argument("--stream-width", type=int, default=320)
    parser.add_argument("--stream-quality", type=int, default=55)
    parser.add_argument("--preview-fps", type=int, default=8)
    args = parser.parse_args()

    store = FrameStore(args.stream_width, args.stream_quality, args.preview_fps)
    rclpy.init()
    node = CompressedImageNode(args.topic, store)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store, args.max_fps))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[open] http://{args.host}:{args.port}/stream.mjpg", flush=True)
    try:
        rclpy.spin(node)
    finally:
        server.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
