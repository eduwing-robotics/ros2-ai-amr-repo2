#!/usr/bin/env python3
"""T1 RealSense 영상 녹화 + 프레임 저장 (노트북에서 실행).

사전:
  로봇:  ./scripts/launch_t1_realsense.sh
  노트북: source ./scripts/camera_laptop_env.sh

예:
  # 진품 프레임만 저장 (권장 — 데이터셋용)
  python3 scripts/t1_record_camera.py --out ~/datasets/authenticity/venus/real --mode frames --secs 60

  # mp4 녹화 후 나중에 프레임 분할
  python3 scripts/t1_record_camera.py --out ~/datasets/clips/venus_real.mp4 --mode video --secs 60

  # 녹화 + 프레임 동시
  python3 scripts/t1_record_camera.py --out ~/datasets/clips/venus_real --mode both --secs 60
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage, Image


DEFAULT_COMPRESSED = "/camera/color/image_detect/compressed"
DEFAULT_RAW = "/camera/color/image_raw"


class Recorder(Node):
    def __init__(
        self,
        topic: str,
        compressed: bool,
        out: Path,
        mode: str,
        fps_limit: float,
        max_secs: float,
        preview: bool = False,
    ) -> None:
        super().__init__("t1_record_camera")
        self.bridge = CvBridge()
        self.mode = mode
        self.fps_limit = max(fps_limit, 0.1)
        self.min_dt = 1.0 / self.fps_limit
        self.max_secs = max_secs
        self.preview = preview
        self.t0 = time.time()
        self.last_save = 0.0
        self.count = 0
        self.writer = None
        self.done = False
        self._win = "T1 record (Q/ESC=stop)" if preview else None

        if mode in ("frames", "both"):
            self.frames_dir = out if mode == "frames" else out.with_suffix("") / "frames"
            self.frames_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.frames_dir = None

        if mode in ("video", "both"):
            if mode == "video":
                self.video_path = out if out.suffix.lower() == ".mp4" else out.with_suffix(".mp4")
            else:
                self.video_path = out.with_suffix(".mp4") if out.suffix == "" else out.parent / f"{out.name}.mp4"
            self.video_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            self.video_path = None

        qos = qos_profile_sensor_data
        if compressed:
            self.create_subscription(CompressedImage, topic, self._on_compressed, qos)
        else:
            self.create_subscription(Image, topic, self._on_raw, qos)

        self.get_logger().info(
            f"recording topic={topic} mode={mode} fps_limit={self.fps_limit} secs={max_secs} out={out}"
        )

    def _maybe_finish(self) -> None:
        if self.max_secs > 0 and (time.time() - self.t0) >= self.max_secs:
            self.done = True

    def _handle_bgr(self, bgr: np.ndarray) -> None:
        now = time.time()
        # preview: show every frame; save only at fps_limit
        if self.preview and self._win:
            vis = bgr.copy()
            elapsed = now - self.t0
            remain = max(0.0, self.max_secs - elapsed) if self.max_secs > 0 else -1.0
            hud = f"saved={self.count}  t={elapsed:.1f}s"
            if remain >= 0:
                hud += f"  left={remain:.1f}s"
            cv2.putText(
                vis, hud, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2, cv2.LINE_AA
            )
            cv2.imshow(self._win, vis)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                self.done = True
                return

        if now - self.last_save < self.min_dt:
            return
        self.last_save = now
        self.count += 1

        if self.frames_dir is not None:
            path = self.frames_dir / f"frame_{self.count:06d}.jpg"
            cv2.imwrite(str(path), bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        if self.video_path is not None:
            if self.writer is None:
                h, w = bgr.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self.writer = cv2.VideoWriter(str(self.video_path), fourcc, self.fps_limit, (w, h))
                if not self.writer.isOpened():
                    self.get_logger().error(f"VideoWriter open failed: {self.video_path}")
                    self.done = True
                    return
            self.writer.write(bgr)

        if self.count % 30 == 0:
            self.get_logger().info(f"saved {self.count} frames ({now - self.t0:.1f}s)")

        self._maybe_finish()

    def _on_compressed(self, msg: CompressedImage) -> None:
        if self.done:
            return
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            return
        self._handle_bgr(bgr)

    def _on_raw(self, msg: Image) -> None:
        if self.done:
            return
        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        self._handle_bgr(bgr)

    def close(self) -> None:
        if self.writer is not None:
            self.writer.release()
            self.writer = None
        if self.preview:
            cv2.destroyAllWindows()


def main() -> int:
    p = argparse.ArgumentParser(description="Record T1 RealSense to frames/video")
    p.add_argument("--out", required=True, help="output dir or .mp4 path")
    p.add_argument("--mode", choices=("frames", "video", "both"), default="frames")
    p.add_argument("--topic", default=DEFAULT_COMPRESSED)
    p.add_argument("--raw", action="store_true", help="use raw Image topic instead of compressed")
    p.add_argument("--fps", type=float, default=5.0, help="save rate (dataset: 2~5 권장)")
    p.add_argument("--secs", type=float, default=0.0, help="0 = until Ctrl+C")
    p.add_argument(
        "--preview",
        action="store_true",
        help="live OpenCV window while recording (Q/ESC to stop)",
    )
    args = p.parse_args()

    topic = DEFAULT_RAW if args.raw else args.topic
    compressed = not args.raw

    rclpy.init()
    node = Recorder(
        topic=topic,
        compressed=compressed,
        out=Path(args.out).expanduser(),
        mode=args.mode,
        fps_limit=args.fps,
        max_secs=args.secs,
        preview=bool(args.preview),
    )
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.get_logger().info(f"done — total frames={node.count}")
        node.destroy_node()
        rclpy.shutdown()
    return 0 if node.count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
