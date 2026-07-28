#!/usr/bin/env python3
"""Quick unit checks for statue fragment merge / person conflict helpers."""

from __future__ import annotations

import sys
from pathlib import Path

# Prefer source tree over install when running from repo
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'museum_patrol_system'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from museum_patrol_nodes.detection_filters import (  # noqa: E402
    RawBox,
    DetectionFilter,
    FilterConfig,
    merge_fragmented_statues,
    merge_overlapping_same_class,
    resolve_person_conflicts,
)


def test_vertical_stack_nike_merge() -> None:
    """Nike-like upper wings + lower body → one union statue box."""
    upper = RawBox(cls='statue', conf=0.66, x1=40, y1=20, x2=220, y2=260)
    lower = RawBox(cls='statue', conf=0.80, x1=70, y1=180, x2=200, y2=480)
    fire = RawBox(cls='fire', conf=0.77, x1=400, y1=100, x2=520, y2=320)
    # Plain NMS at 0.55 would keep both (low IoU); fragment merge must collapse.
    after_nms = merge_overlapping_same_class(
        [upper, lower, fire], default_iou=0.45, iou_by_class={'statue': 0.55},
    )
    statues_nms = [b for b in after_nms if b.cls == 'statue']
    assert len(statues_nms) == 2, f'expected 2 after weak NMS, got {len(statues_nms)}'

    merged = merge_fragmented_statues(after_nms, soft_iou=0.15, union_merge=True)
    statues = [b for b in merged if b.cls == 'statue']
    assert len(statues) == 1, f'expected 1 statue after fragment merge, got {statues}'
    s = statues[0]
    assert s.conf == 0.80
    assert s.x1 == 40 and s.y1 == 20 and s.x2 == 220 and s.y2 == 480
    assert any(b.cls == 'fire' for b in merged)


def test_soft_iou_and_containment() -> None:
    outer = RawBox(cls='statue', conf=0.90, x1=10, y1=10, x2=200, y2=400)
    inner = RawBox(cls='statue', conf=0.55, x1=40, y1=80, x2=160, y2=300)
    merged = merge_fragmented_statues([outer, inner], soft_iou=0.15)
    assert len([b for b in merged if b.cls == 'statue']) == 1


def test_nms_boxes_pipeline() -> None:
    filt = DetectionFilter(FilterConfig(statue_nms_iou=0.25, statue_fragment_soft_iou=0.15))
    upper = RawBox(cls='statue', conf=0.66, x1=50, y1=30, x2=210, y2=250)
    lower = RawBox(cls='statue', conf=0.80, x1=80, y1=200, x2=190, y2=470)
    out = filt.nms_boxes([upper, lower])
    assert len(out) == 1
    assert out[0].conf == 0.80


def test_person_vs_statue_soft_drop() -> None:
    statue = RawBox(cls='statue', conf=0.70, x1=100, y1=50, x2=300, y2=400)
    person = RawBox(cls='person', conf=0.78, x1=120, y1=80, x2=280, y2=380)
    kept = resolve_person_conflicts(
        [statue, person],
        anchors=[statue],
        person_vs_statue_iou=0.20,
        person_vs_statue_soft_iou=0.05,
        person_vs_statue_pad=0.35,
    )
    assert all(b.cls != 'person' for b in kept)
    assert any(b.cls == 'statue' for b in kept)


def test_person_vs_weak_statue_padded_drop() -> None:
    """Weak finetune statue + nearby person → person dropped via pad overlap."""
    statue = RawBox(cls='statue', conf=0.12, x1=80, y1=40, x2=220, y2=360)
    # Person mostly beside statue but overlapping padded region
    person = RawBox(cls='person', conf=0.85, x1=210, y1=60, x2=350, y2=380)
    filt = DetectionFilter(
        FilterConfig(
            person_vs_statue_anchor_conf=0.08,
            person_vs_statue_soft_iou=0.015,
            person_vs_statue_pad=0.70,
        )
    )
    anchors = filt.conflict_anchors([statue, person])
    assert any(b.cls == 'statue' for b in anchors)
    kept = filt.resolve_hybrid_person([statue, person], anchors)
    assert all(b.cls != 'person' for b in kept)


def test_person_center_near_statue_drops() -> None:
    """Person center inside padded statue region → drop person (approach 5)."""
    statue = RawBox(cls='statue', conf=0.40, x1=100, y1=40, x2=240, y2=380)
    # Person box mostly outside but center still near statue
    person = RawBox(cls='person', conf=0.90, x1=220, y1=80, x2=360, y2=360)
    kept = resolve_person_conflicts(
        [statue, person],
        anchors=[statue],
        person_vs_statue_iou=0.10,
        person_vs_statue_soft_iou=0.015,
        person_cover_thr=0.15,
        person_vs_statue_pad=0.70,
    )
    assert all(b.cls != 'person' for b in kept)
    assert any(b.cls == 'statue' for b in kept)


def test_sculptural_grey_cast_rejects_person() -> None:
    """Dark grey matte sculpture ROI → sculptural reject; colorful person keeps."""
    import numpy as np

    filt = DetectionFilter(FilterConfig(reject_sculptural_person=True))
    # Synthetic sphinx-like cast: dark grey with shading, no skin/clothes color
    sculp = np.zeros((180, 140, 3), dtype=np.uint8)
    yy, xx = np.mgrid[0:180, 0:140]
    base = 55 + (xx * 0.35).astype(np.int32) + (yy * 0.12).astype(np.int32)
    base = np.clip(base, 30, 110)
    sculp[:, :, 0] = base
    sculp[:, :, 1] = base
    sculp[:, :, 2] = np.clip(base + 4, 0, 255)
    # Soft radial highlight (3D shading)
    cy, cx = 70, 70
    rr = ((yy - cy) ** 2 + (xx - cx) ** 2).astype(np.float32)
    highlight = np.clip(40 - rr / 80.0, 0, 40).astype(np.uint8)
    sculp = np.clip(sculp.astype(np.int16) + highlight[:, :, None], 0, 255).astype(np.uint8)
    # Wider lower body (animal silhouette cue)
    sculp[120:, :, :] = np.clip(sculp[120:, :, :].astype(np.int16) - 8, 20, 255).astype(
        np.uint8
    )
    frame_s = np.full((240, 320, 3), 210, dtype=np.uint8)
    frame_s[20:200, 90:230] = sculp
    # Light plinth under figure (sculpture cue)
    frame_s[200:220, 100:220] = 190
    box_s = RawBox(cls='person', conf=0.75, x1=90, y1=20, x2=230, y2=200)
    assert filt._is_sculptural_3d_person(frame_s, box_s), 'grey cast should reject'

    # Warm-lit dark cast: sparse HSV "skin" speckles + low RGB chroma (real sphinx)
    warm = sculp.copy()
    warm[12:28, 55:85] = (68, 82, 98)
    warm[18:24, 60:78] = (70, 86, 105)
    frame_w = np.full((240, 320, 3), 210, dtype=np.uint8)
    frame_w[20:200, 90:230] = warm
    frame_w[200:220, 100:220] = 190
    box_w = RawBox(cls='person', conf=0.75, x1=90, y1=20, x2=230, y2=200)
    assert filt._is_sculptural_3d_person(frame_w, box_w), 'warm dark sphinx should reject'
    assert not filt._passes_person(box_w, frame_w, frame_w.shape)

    # Colorful clothed person crop — should NOT reject
    person = np.zeros((180, 90, 3), dtype=np.uint8)
    # Skin face band
    person[:40, 25:65] = (90, 140, 200)
    # Red shirt + blue pants
    person[40:100, :] = (40, 40, 200)
    person[100:, :] = (180, 80, 40)
    frame_p = np.full((240, 320, 3), 180, dtype=np.uint8)
    frame_p[30:210, 110:200] = person
    box_p = RawBox(cls='person', conf=0.80, x1=110, y1=30, x2=200, y2=210)
    assert not filt._is_sculptural_3d_person(frame_p, box_p), 'color person should keep'
    assert filt._passes_person(box_p, frame_p, frame_p.shape)


def test_photo_standee_keeps_person() -> None:
    """Flat printed standee (skin + clothing + flat lighting) must KEEP as person."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_sculptural_person=True,
            reject_statue_like=True,
            person_confidence=0.25,
            person_confirm_frames=1,
            min_person_box_area_ratio=0.01,
            min_person_height_ratio=0.08,
        )
    )
    # Flat photo panel: skin face, colorful clothes, little 3D shading
    panel = np.zeros((200, 100, 3), dtype=np.uint8)
    panel[:45, 20:80] = (95, 145, 205)  # face skin
    panel[45:110, :] = (30, 50, 210)  # red shirt
    panel[110:, :] = (160, 90, 30)  # blue jeans
    # Mild print noise (photo texture), not cast shading
    noise = (np.random.default_rng(0).integers(0, 12, panel.shape, dtype=np.uint8))
    panel = np.clip(panel.astype(np.int16) + noise - 6, 0, 255).astype(np.uint8)
    frame = np.full((280, 360, 3), 170, dtype=np.uint8)
    # Cardboard-ish edge (thin dark border) — not a picture frame
    frame[30:234, 120:224] = (40, 45, 50)
    frame[34:234, 124:224] = panel
    box = RawBox(cls='person', conf=0.42, x1=124, y1=34, x2=224, y2=234)
    assert not filt._is_sculptural_3d_person(frame, box), 'standee must not be sculptural'
    assert not filt._is_statue_like_person(frame, box), 'standee must not be statue-like'
    assert filt._passes_person(box, frame, frame.shape), 'standee must pass as person'


def test_framed_painting_person_rejects() -> None:
    """Person box inside dark picture frame → reject (esp. low conf)."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_picture_person=True,
            person_confidence=0.25,
            person_in_frame_min_conf=0.78,
            min_person_box_area_ratio=0.01,
            min_person_height_ratio=0.08,
            reject_sculptural_person=False,
            reject_statue_like=False,
            reject_sculpture_bust=False,
        )
    )
    # Wall background + dark rectangular frame around a painted figure
    frame = np.full((300, 400, 3), 200, dtype=np.uint8)
    # Outer dark frame moulding
    frame[40:260, 80:320] = 25
    # Painting interior (warm canvas tones)
    frame[55:245, 95:305] = (70, 110, 150)
    # Soft painted "person" region (not photo skin saturation)
    frame[80:220, 140:240] = (85, 120, 160)
    # Glass glare streak near top of frame
    frame[56:64, 150:250] = 235

    box = RawBox(cls='person', conf=0.32, x1=140, y1=80, x2=240, y2=220)
    assert filt._is_inside_picture_frame(frame, box) or filt._has_weak_picture_frame(
        frame, box
    ), 'expected frame cues around painting person'
    assert not filt._passes_person(box, frame, frame.shape), 'framed painting person must drop'


def test_white_ornate_framed_painting_rejects() -> None:
    """Goya-like: dark painted figure in thick white ornate frame → drop PERSON."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_picture_person=True,
            person_confidence=0.25,
            person_in_frame_min_conf=0.78,
            min_person_box_area_ratio=0.01,
            min_person_height_ratio=0.08,
            reject_sculptural_person=False,
            reject_statue_like=False,
            reject_sculpture_bust=False,
        )
    )
    # Light wall + thick white ornate moulding + dark canvas figure
    frame = np.full((320, 400, 3), 210, dtype=np.uint8)
    # Outer white frame (ornate = high edge via checker noise on rim)
    frame[30:290, 70:330] = 235
    noise = np.random.default_rng(1).integers(0, 30, (260, 260), dtype=np.uint8)
    rim = frame[30:290, 70:330, 0]
    rim[:] = np.clip(rim.astype(np.int16) + (noise - 10), 200, 255).astype(np.uint8)
    frame[30:290, 70:330, 1] = frame[30:290, 70:330, 0]
    frame[30:290, 70:330, 2] = frame[30:290, 70:330, 0]
    # Dark painting interior (Saturn-like)
    frame[55:265, 95:305] = 35
    frame[80:240, 140:250] = 28  # darker figure blob
    # Person box = canvas interior only (as YOLO typically returns)
    box = RawBox(cls='person', conf=0.72, x1=140, y1=80, x2=250, y2=240)
    assert filt._is_inside_picture_frame(frame, box) or filt._has_white_framed_painting_combo(
        frame, box
    ) or filt._has_hard_frame_person_reject(frame, box), 'expected white ornate frame cues'
    assert not filt._passes_person(box, frame, frame.shape), 'white-framed painting must drop'


def test_high_conf_framed_painting_hard_rejects() -> None:
    """Even high-conf PERSON inside white frame + painted canvas must drop."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_picture_person=True,
            person_confidence=0.25,
            person_in_frame_min_conf=0.78,
            min_person_box_area_ratio=0.01,
            min_person_height_ratio=0.08,
            reject_sculptural_person=False,
            reject_statue_like=False,
            reject_sculpture_bust=False,
        )
    )
    frame = np.full((320, 400, 3), 210, dtype=np.uint8)
    frame[30:290, 70:330] = 235
    noise = np.random.default_rng(2).integers(0, 30, (260, 260), dtype=np.uint8)
    rim = frame[30:290, 70:330, 0]
    rim[:] = np.clip(rim.astype(np.int16) + (noise - 10), 200, 255).astype(np.uint8)
    frame[30:290, 70:330, 1] = frame[30:290, 70:330, 0]
    frame[30:290, 70:330, 2] = frame[30:290, 70:330, 0]
    frame[55:265, 95:305] = 40
    frame[90:230, 150:245] = 30
    box = RawBox(cls='person', conf=0.92, x1=150, y1=90, x2=245, y2=230)
    assert not filt._passes_person(box, frame, frame.shape), 'high-conf framed person must hard-drop'


def test_adapt_preserves_high_person_conf() -> None:
    """Low-res adapt must NOT crush launcher --person-conf (Pi/RealSense FP control)."""
    base = FilterConfig(person_confidence=0.75, statue_confidence=0.50)
    adapted = FilterConfig.adapt_for_resolution(424, base)
    assert adapted.person_confidence == 0.75
    assert adapted.statue_confidence == 0.50
    assert adapted.person_in_frame_min_conf == base.person_in_frame_min_conf


def test_human_person_wins_over_statue() -> None:
    """Overlapping person+statue: human cues → keep person, drop statue."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_human_like_statue=True,
            person_wins_over_statue_when_human=True,
            person_confidence=0.25,
            statue_confidence=0.40,
            min_person_box_area_ratio=0.01,
            min_person_height_ratio=0.08,
            reject_sculptural_person=False,
            reject_statue_like=False,
            reject_sculpture_bust=False,
            reject_picture_person=False,
            person_confirm_frames=1,
            statue_confirm_frames=1,
        )
    )
    # Colorful clothed person crop
    frame = np.full((280, 360, 3), 170, dtype=np.uint8)
    person_roi = np.zeros((180, 90, 3), dtype=np.uint8)
    person_roi[:40, 25:65] = (90, 140, 200)  # skin
    person_roi[40:100, :] = (40, 40, 200)  # red shirt
    person_roi[100:, :] = (180, 80, 40)  # blue pants
    frame[40:220, 120:210] = person_roi
    person = RawBox(cls='person', conf=0.80, x1=120, y1=40, x2=210, y2=220)
    statue = RawBox(cls='statue', conf=0.70, x1=110, y1=30, x2=220, y2=230)
    assert filt._has_person_human_cues(frame, person)
    kept = filt.resolve_hybrid_person([person, statue], [statue], frame=frame)
    assert any(b.cls == 'person' for b in kept), 'human person must keep'
    assert all(b.cls != 'statue' for b in kept), 'overlapping statue must drop'


def test_statue_rejects_human_like_roi() -> None:
    """STATUE on skin+clothing ROI → reject via human-like filter."""
    import numpy as np

    filt = DetectionFilter(
        FilterConfig(
            reject_human_like_statue=True,
            statue_confidence=0.40,
            min_statue_box_area_ratio=0.01,
            reject_picture_statue=False,
            reject_flat_statue=False,
        )
    )
    frame = np.full((280, 360, 3), 170, dtype=np.uint8)
    person_roi = np.zeros((180, 90, 3), dtype=np.uint8)
    person_roi[:40, 25:65] = (90, 140, 200)
    person_roi[40:100, :] = (40, 40, 200)
    person_roi[100:, :] = (180, 80, 40)
    frame[40:220, 120:210] = person_roi
    box = RawBox(cls='statue', conf=0.72, x1=120, y1=40, x2=210, y2=220)
    assert not filt._passes_statue(box, frame, frame.shape)


def test_class_flip_gate_suppresses_one_frame() -> None:
    """After statue, a single person frame is suppressed; 2 consecutive passes."""
    filt = DetectionFilter(
        FilterConfig(
            class_flip_confirm_frames=2,
            person_confirm_frames=1,
            statue_confirm_frames=1,
        )
    )
    # Seed history with statue
    filt.confirm({'statue'})
    filt.confirm({'statue'})
    # First person after statue → blocked by flip gate
    c1 = filt.confirm({'person'})
    c1 = {c for c in c1 if filt._passes_class_flip_gate(c)}
    assert 'person' not in c1
    # Second consecutive person → allowed
    c2 = filt.confirm({'person'})
    c2 = {c for c in c2 if filt._passes_class_flip_gate(c)}
    assert 'person' in c2


def main() -> int:
    test_vertical_stack_nike_merge()
    test_soft_iou_and_containment()
    test_nms_boxes_pipeline()
    test_person_vs_statue_soft_drop()
    test_person_vs_weak_statue_padded_drop()
    test_person_center_near_statue_drops()
    test_sculptural_grey_cast_rejects_person()
    test_photo_standee_keeps_person()
    test_framed_painting_person_rejects()
    test_white_ornate_framed_painting_rejects()
    test_high_conf_framed_painting_hard_rejects()
    test_adapt_preserves_high_person_conf()
    test_human_person_wins_over_statue()
    test_statue_rejects_human_like_roi()
    test_class_flip_gate_suppresses_one_frame()
    print(
        'OK: merge/conflict + sculptural + standee + white-frame + hard-frame + '
        'adapt-conf + human↔statue + flip-gate'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
