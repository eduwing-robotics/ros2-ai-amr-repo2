#!/usr/bin/env python3
"""사투르누스 등 진품 사진 → '가품 프린트'용 변형 생성.

장면 내용(폭력)을 바꾸지 않고, 인쇄/스캔/색감 차이만 만듭니다.
EfficientNet 진품/가품 파일럿용.

예:
  python3 ai_perception/efficientnet_b0_authentication/scripts/make_print_fakes.py \\
    --src ~/Downloads/전시품/8\\ 사투르누스가\\ 아들을\\ 삼키는\\ 장면 \\
    --dst ~/datasets/authenticity/saturn/fake \\
    --per-image 8
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np


def _jitter_color(img: np.ndarray, rng: random.Random) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 0] = (hsv[:, :, 0] + rng.uniform(-8, 8)) % 180
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * rng.uniform(0.55, 1.35), 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * rng.uniform(0.75, 1.25), 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    # 약간의 화이트밸런스 틀어짐
    b, g, r = cv2.split(out.astype(np.float32))
    b *= rng.uniform(0.85, 1.15)
    g *= rng.uniform(0.85, 1.15)
    r *= rng.uniform(0.85, 1.15)
    return np.clip(cv2.merge([b, g, r]), 0, 255).astype(np.uint8)


def _low_res_print(img: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = img.shape[:2]
    scale = rng.uniform(0.25, 0.45)
    small = cv2.resize(img, (max(8, int(w * scale)), max(8, int(h * scale))), interpolation=cv2.INTER_AREA)
    back = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    # JPEG 열화
    q = rng.randint(25, 55)
    ok, buf = cv2.imencode(".jpg", back, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    if not ok:
        return back
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def _blur_soft(img: np.ndarray, rng: random.Random) -> np.ndarray:
    k = rng.choice([3, 5, 7])
    return cv2.GaussianBlur(img, (k, k), 0)


def _crop_zoom(img: np.ndarray, rng: random.Random) -> np.ndarray:
    h, w = img.shape[:2]
    m = rng.uniform(0.04, 0.12)
    x0, y0 = int(w * m), int(h * m)
    x1, y1 = int(w * (1 - m)), int(h * (1 - m))
    crop = img[y0:y1, x0:x1]
    return cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)


def _mirror(img: np.ndarray, _rng: random.Random) -> np.ndarray:
    return cv2.flip(img, 1)


def _paper_cast(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """다른 용지/조명처럼 전체 틴트."""
    tint = np.zeros_like(img, dtype=np.float32)
    mode = rng.choice(["warm", "cool", "greenish", "magenta"])
    if mode == "warm":
        tint[:] = (20, 40, 70)  # BGR
    elif mode == "cool":
        tint[:] = (70, 40, 20)
    elif mode == "greenish":
        tint[:] = (30, 55, 30)
    else:
        tint[:] = (55, 25, 55)
    alpha = rng.uniform(0.08, 0.22)
    out = img.astype(np.float32) * (1 - alpha) + tint * alpha
    return np.clip(out, 0, 255).astype(np.uint8)


TRANSFORMS = (
    ("color", _jitter_color),
    ("lowres", _low_res_print),
    ("blur", _blur_soft),
    ("crop", _crop_zoom),
    ("mirror", _mirror),
    ("tint", _paper_cast),
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--dst", required=True, type=Path)
    ap.add_argument("--per-image", type=int, default=6, help="원본 1장당 가품 변형 수")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    files = sorted(p for p in args.src.iterdir() if p.suffix.lower() in exts)
    if not files:
        print(f"[FAIL] no images in {args.src}")
        return 1

    args.dst.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    n = 0
    for src in files:
        img = cv2.imread(str(src))
        if img is None:
            continue
        # 변형을 섞어 적용 (1~3개 스택)
        for i in range(args.per_image):
            out = img.copy()
            names = []
            for name, fn in rng.sample(TRANSFORMS, k=rng.randint(1, 3)):
                out = fn(out, rng)
                names.append(name)
            tag = "-".join(names)
            path = args.dst / f"{src.stem}__fake_{i:02d}_{tag}.jpg"
            cv2.imwrite(str(path), out, [int(cv2.IMWRITE_JPEG_QUALITY), rng.randint(55, 85)])
            n += 1

    print(f"[OK] {len(files)} sources → {n} fakes in {args.dst}")
    print("다음: 가능하면 가품 프린트를 출력해 벽에 걸고 T1으로도 촬영하세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
