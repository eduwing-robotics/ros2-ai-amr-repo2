"""Robust sensor_msgs/Image → BGR conversion (RealSense rgb8 stride 지원)."""

from __future__ import annotations

import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import CompressedImage, Image

_BRIDGE = CvBridge()


def imgmsg_to_bgr(msg: Image) -> np.ndarray:
    """Decode Image message to BGR ndarray, respecting row step/padding."""
    enc = (msg.encoding or '').lower()
    expected = msg.height * msg.step
    if len(msg.data) < expected:
        raise ValueError(
            f'incomplete image buffer: got {len(msg.data)} bytes, need >={expected} '
            f'({msg.width}x{msg.height} step={msg.step} enc={enc})'
        )

    if enc == 'bgr8':
        row_bytes = msg.width * 3
        buf = np.frombuffer(msg.data, dtype=np.uint8)
        img = buf.reshape((msg.height, msg.step))[:, :row_bytes]
        return img.reshape((msg.height, msg.width, 3)).copy()

    if enc == 'rgb8':
        row_bytes = msg.width * 3
        buf = np.frombuffer(msg.data, dtype=np.uint8)
        rgb = buf.reshape((msg.height, msg.step))[:, :row_bytes]
        rgb = rgb.reshape((msg.height, msg.width, 3))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    if enc in ('mono8', '8uc1'):
        buf = np.frombuffer(msg.data, dtype=np.uint8)
        gray = buf.reshape((msg.height, msg.step))[:, :msg.width]
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    try:
        return _BRIDGE.imgmsg_to_cv2(msg, desired_encoding='bgr8')
    except CvBridgeError:
        return _BRIDGE.imgmsg_to_cv2(msg, desired_encoding='passthrough')


def upscale_for_inference(frame: np.ndarray, min_width: int = 640) -> tuple[np.ndarray, float]:
    """Upscale narrow Wi-Fi camera frames so YOLO sees training-scale detail."""
    h, w = frame.shape[:2]
    if w >= min_width:
        return frame, 1.0
    scale = min_width / w
    new_h = max(1, int(round(h * scale)))
    upscaled = cv2.resize(frame, (min_width, new_h), interpolation=cv2.INTER_CUBIC)
    return upscaled, scale


def preprocess_for_inference(
    frame: np.ndarray,
    min_width: int = 640,
    enhance_low_res: bool = True,
) -> tuple[np.ndarray, float]:
    """Sharpen + CLAHE for 424x240 streams, then upscale for YOLO."""
    work = frame
    if enhance_low_res and frame.shape[1] <= 480:
        blur = cv2.GaussianBlur(work, (0, 0), 1.0)
        work = cv2.addWeighted(work, 1.5, blur, -0.5, 0)
        lab = cv2.cvtColor(work, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        work = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    return upscale_for_inference(work, min_width)


def topic_is_compressed(topic: str) -> bool:
    return topic.rstrip('/').endswith('/compressed')


def compressed_topic_for(raw_topic: str) -> str:
    return f'{raw_topic.rstrip("/")}/compressed'


def compressed_imgmsg_to_bgr(msg: CompressedImage) -> np.ndarray:
    """Decode sensor_msgs/CompressedImage (jpeg) to BGR."""
    fmt = (msg.format or '').lower()
    if fmt and 'jpeg' not in fmt and 'jpg' not in fmt:
        raise ValueError(f'unsupported compressed format: {msg.format}')
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('cv2.imdecode failed for CompressedImage')
    return img


def bgr_to_compressed_imgmsg(
    frame: np.ndarray,
    header,
    jpeg_quality: int = 75,
) -> CompressedImage:
    ok, encoded = cv2.imencode(
        '.jpg',
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
    )
    if not ok:
        raise ValueError('cv2.imencode failed')
    msg = CompressedImage()
    msg.header = header
    msg.format = 'jpeg'
    msg.data = encoded.tobytes()
    return msg
