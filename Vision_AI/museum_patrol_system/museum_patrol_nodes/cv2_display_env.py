"""Configure Qt/OpenCV before cv2.imshow (blank window / QFontDatabase spam on Linux)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _cv2_package_dir() -> Path | None:
    try:
        import cv2  # noqa: WPS433 — intentional late probe
    except ImportError:
        return None
    return Path(cv2.__file__).resolve().parent


def ensure_qt_fonts() -> None:
    """opencv-python wheels expect cv2/qt/fonts; create symlink if missing."""
    cv2_dir = _cv2_package_dir()
    if cv2_dir is None:
        return
    fonts_dir = cv2_dir / 'qt' / 'fonts'
    if fonts_dir.is_dir() and any(fonts_dir.iterdir()):
        return
    fonts_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
        Path('/usr/share/fonts/TTF/DejaVuSans.ttf'),
        Path('/usr/share/fonts/dejavu/DejaVuSans.ttf'),
    ]
    for src in candidates:
        if src.is_file():
            link = fonts_dir / src.name
            if not link.exists():
                link.symlink_to(src)
            return


def configure_opencv_display() -> None:
    """Call before ``import cv2`` in GUI viewer scripts."""
    os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
    os.environ.setdefault('QT_LOGGING_RULES', 'qt.qpa.*=false')
    if 'QT_QPA_FONTDIR' in os.environ:
        if not Path(os.environ['QT_QPA_FONTDIR']).is_dir():
            os.environ.pop('QT_QPA_FONTDIR', None)


def patch_after_cv2_import() -> None:
    """Call immediately after ``import cv2``."""
    fontdir = os.environ.get('QT_QPA_FONTDIR', '')
    if fontdir and not Path(fontdir).is_dir():
        os.environ.pop('QT_QPA_FONTDIR', None)
    ensure_qt_fonts()
    if sys.platform.startswith('linux'):
        try:
            import cv2

            cv2.setUseOptimized(True)
        except Exception:
            pass
