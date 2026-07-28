"""Post-filters for YOLO fire/smoke detections (reduce solid-color false positives)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Set, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class RawBox:
    cls: str
    conf: float
    x1: int
    y1: int
    x2: int
    y2: int


def box_iou(a: RawBox, b: RawBox) -> float:
    """Intersection-over-union for axis-aligned RawBox."""
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0, a.x2 - a.x1) * max(0, a.y2 - a.y1)
    area_b = max(0, b.x2 - b.x1) * max(0, b.y2 - b.y1)
    union = area_a + area_b - inter
    return float(inter / union) if union > 0 else 0.0


def merge_overlapping_same_class(
    boxes: List[RawBox],
    default_iou: float = 0.45,
    iou_by_class: Dict[str, float] | None = None,
) -> List[RawBox]:
    """Class-aware NMS — keep highest-conf box when same-class IoU >= threshold."""
    if not boxes:
        return []
    iou_map = iou_by_class or {}
    by_cls: Dict[str, List[RawBox]] = {}
    for box in boxes:
        by_cls.setdefault(box.cls, []).append(box)
    merged: List[RawBox] = []
    for cls, group in by_cls.items():
        thr = float(iou_map.get(cls, default_iou))
        ordered = sorted(group, key=lambda b: b.conf, reverse=True)
        kept: List[RawBox] = []
        for box in ordered:
            if any(box_iou(box, prev) >= thr for prev in kept):
                continue
            kept.append(box)
        merged.extend(kept)
    return merged


def _box_area(box: RawBox) -> int:
    return max(0, box.x2 - box.x1) * max(0, box.y2 - box.y1)


def _intersection_area(a: RawBox, b: RawBox) -> int:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    return max(0, ix2 - ix1) * max(0, iy2 - iy1)


def _person_covered_by(person: RawBox, anchor: RawBox) -> float:
    """Fraction of person box covered by anchor (containment)."""
    area = _box_area(person)
    if area <= 0:
        return 0.0
    return float(_intersection_area(person, anchor) / area)


def _center_inside(inner: RawBox, outer: RawBox) -> bool:
    cx = (inner.x1 + inner.x2) // 2
    cy = (inner.y1 + inner.y2) // 2
    return outer.x1 <= cx <= outer.x2 and outer.y1 <= cy <= outer.y2


def _x_overlap_ratio(a: RawBox, b: RawBox) -> float:
    """Intersection width / min(widths) — 1.0 when one fully overlaps the other in x."""
    ix1 = max(a.x1, b.x1)
    ix2 = min(a.x2, b.x2)
    iw = max(0, ix2 - ix1)
    if iw <= 0:
        return 0.0
    wa = max(1, a.x2 - a.x1)
    wb = max(1, b.x2 - b.x1)
    return float(iw / min(wa, wb))


def _vertically_stacked_fragments(
    a: RawBox, b: RawBox, x_overlap_thr: float = 0.4,
) -> bool:
    """Upper/lower split of one object (Nike wings + torso)."""
    if _x_overlap_ratio(a, b) < x_overlap_thr:
        return False
    top, bot = (a, b) if a.y1 <= b.y1 else (b, a)
    gap = bot.y1 - top.y2
    th = max(1, top.y2 - top.y1)
    bh = max(1, bot.y2 - bot.y1)
    # Allow modest gap or overlap; reject far-apart boxes
    if gap > 0.20 * min(th, bh):
        return False
    acx = 0.5 * (a.x1 + a.x2)
    bcx = 0.5 * (b.x1 + b.x2)
    avg_w = 0.5 * ((a.x2 - a.x1) + (b.x2 - b.x1))
    if abs(acx - bcx) > 0.40 * max(avg_w, 1.0):
        return False
    # Union height should meaningfully cover both (not side-by-side peers)
    union_h = max(a.y2, b.y2) - min(a.y1, b.y1)
    if union_h < 0.85 * (th + bh - max(0, -gap)):
        return False
    return True


def _statue_fragments_related(
    a: RawBox, b: RawBox, soft_iou: float = 0.15,
) -> bool:
    """True when two statue boxes are fragments of the same object."""
    if box_iou(a, b) >= soft_iou:
        return True
    if _center_inside(a, b) or _center_inside(b, a):
        return True
    if _person_covered_by(a, b) >= 0.45 or _person_covered_by(b, a) >= 0.45:
        return True
    if _vertically_stacked_fragments(a, b, x_overlap_thr=0.4):
        return True
    return False


def merge_fragmented_statues(
    boxes: List[RawBox],
    soft_iou: float = 0.15,
    union_merge: bool = True,
) -> List[RawBox]:
    """Collapse fragmented statue multi-boxes beyond plain IoU-NMS.

    Keeps highest-conf parent; optionally expands it to the union of fragments
    (Nike wings+body → one box).
    """
    if not boxes:
        return []
    statues = [b for b in boxes if b.cls == 'statue']
    others = [b for b in boxes if b.cls != 'statue']
    if len(statues) <= 1:
        return boxes

    ordered = sorted(statues, key=lambda b: b.conf, reverse=True)
    kept: List[RawBox] = []
    for box in ordered:
        absorbed = False
        for i, prev in enumerate(kept):
            if not _statue_fragments_related(box, prev, soft_iou=soft_iou):
                continue
            if union_merge:
                kept[i] = RawBox(
                    cls=prev.cls,
                    conf=prev.conf,
                    x1=min(prev.x1, box.x1),
                    y1=min(prev.y1, box.y1),
                    x2=max(prev.x2, box.x2),
                    y2=max(prev.y2, box.y2),
                )
            absorbed = True
            break
        if not absorbed:
            kept.append(box)
    return others + kept


def _padded_box(box: RawBox, pad_ratio: float) -> RawBox:
    """Expand box by pad_ratio of its width/height (coords may go negative)."""
    aw = max(1, box.x2 - box.x1)
    ah = max(1, box.y2 - box.y1)
    pad_x = int(aw * pad_ratio)
    pad_y = int(ah * pad_ratio)
    return RawBox(
        cls=box.cls,
        conf=box.conf,
        x1=box.x1 - pad_x,
        y1=box.y1 - pad_y,
        x2=box.x2 + pad_x,
        y2=box.y2 + pad_y,
    )


def _person_center_near(person: RawBox, anchor: RawBox, pad_ratio: float = 0.35) -> bool:
    """True if person center lies inside a padded anchor box."""
    padded = _padded_box(anchor, pad_ratio)
    cx = (person.x1 + person.x2) // 2
    cy = (person.y1 + person.y2) // 2
    return padded.x1 <= cx <= padded.x2 and padded.y1 <= cy <= padded.y2


def _overlaps_padded(person: RawBox, anchor: RawBox, pad_ratio: float) -> bool:
    """True if person intersects a padded anchor (any area > 0)."""
    return _intersection_area(person, _padded_box(anchor, pad_ratio)) > 0


def _person_statue_overlap(
    person: RawBox,
    statue: RawBox,
    person_vs_statue_iou: float,
    person_vs_statue_soft_iou: float,
    person_cover_thr: float,
    person_vs_statue_pad: float,
) -> bool:
    """True when person and statue should be treated as the same physical object.

    Aggressive: soft IoU, containment, padded overlap, OR person-center near any
    statue (center pad is at least as large as pad, often larger).
    """
    iou = box_iou(person, statue)
    if iou >= person_vs_statue_soft_iou or iou >= person_vs_statue_iou:
        return True
    if _person_covered_by(person, statue) >= person_cover_thr:
        return True
    if _person_covered_by(statue, person) >= person_cover_thr:
        return True
    # Approach 5: person center near any finetune statue → drop person
    center_pad = max(person_vs_statue_pad, 0.70)
    if _person_center_near(person, statue, pad_ratio=center_pad):
        return True
    if _person_center_near(statue, person, pad_ratio=person_vs_statue_pad):
        return True
    if _overlaps_padded(person, statue, pad_ratio=person_vs_statue_pad):
        return True
    return False


def resolve_person_conflicts(
    boxes: List[RawBox],
    anchors: List[RawBox] | None = None,
    person_vs_statue_iou: float = 0.10,
    person_vs_fire_iou: float = 0.30,
    person_vs_statue_soft_iou: float = 0.015,
    person_cover_thr: float = 0.15,
    person_vs_statue_pad: float = 0.70,
    human_persons: List[RawBox] | None = None,
) -> List[RawBox]:
    """Resolve person↔statue/fire overlaps (museum hybrid).

    Default: statue/fire win over companion COCO person (prefer statue FP over
    person FN on sculptures). Exception: when ``human_persons`` marks a person
    with skin/clothing/photo cues, that person wins and overlapping statues drop.
    ``anchors`` may include weak fire/statue used only for suppression.
    """
    if not boxes:
        return []
    pool = anchors if anchors is not None else boxes
    statues = [b for b in pool if b.cls == 'statue']
    fires = [b for b in pool if b.cls == 'fire']
    if not statues and not fires:
        return boxes

    human_ids = {id(b) for b in (human_persons or [])}
    drop_statue_ids: Set[int] = set()

    out: List[RawBox] = []
    for box in boxes:
        if box.cls == 'statue':
            # Deferred — may be dropped if a human-looking person overlaps
            continue
        if box.cls != 'person':
            out.append(box)
            continue
        person_is_human = id(box) in human_ids
        drop = False
        for st in statues:
            if not _person_statue_overlap(
                box,
                st,
                person_vs_statue_iou=person_vs_statue_iou,
                person_vs_statue_soft_iou=person_vs_statue_soft_iou,
                person_cover_thr=person_cover_thr,
                person_vs_statue_pad=person_vs_statue_pad,
            ):
                continue
            if person_is_human:
                # Real person / photo standee wins → suppress statue FP
                drop_statue_ids.add(id(st))
                continue
            drop = True
            break
        if drop:
            continue
        for fr in fires:
            if box_iou(box, fr) >= person_vs_fire_iou:
                drop = True
                break
            if _person_covered_by(box, fr) >= person_cover_thr:
                drop = True
                break
        if not drop:
            out.append(box)

    for box in boxes:
        if box.cls != 'statue':
            continue
        if id(box) in drop_statue_ids:
            continue
        out.append(box)
    return out


@dataclass
class FilterConfig:
    # museum_fire_smoke painting FPs often land ~0.20–0.30 — keep floor high
    fire_confidence: float = 0.38
    smoke_confidence: float = 0.32
    # COCO person companion — slightly lower for recall; statue-like ROI filters FPs
    person_confidence: float = 0.30
    # Finetune statue — higher floor to cut wall/painting/person FPs
    statue_confidence: float = 0.58
    model_inference_confidence: float = 0.12
    fire_confirm_frames: int = 2
    smoke_confirm_frames: int = 2
    person_confirm_frames: int = 2
    statue_confirm_frames: int = 1
    # person↔statue flip: require N consecutive frames of the new class (no linger)
    class_flip_confirm_frames: int = 2
    confirm_window: int = 5
    min_box_area_ratio: float = 0.0004
    # 원거리 사람(~1.5–2m)도 통과하도록 완화
    min_person_box_area_ratio: float = 0.012
    min_person_height_ratio: float = 0.10
    # 세로/가로 비율
    min_person_aspect: float = 0.9
    # 박스 상단이 이 비율보다 아래면 다리만 보인 것으로 제외
    max_person_top_ratio: float = 0.55
    # 전신 스탠드 포스터는 YOLO가 하체만 잡는 경우가 많음 → 세로로 길면 완화
    tall_person_min_aspect: float = 2.0
    tall_person_max_top_ratio: float = 0.72
    # 동상/그림 오탐 억제 (학습 모델 없이 휴리스틱만)
    reject_statue_like: bool = True
    # 액자(검정·금색·흰색 장식틀) 안 person/fire 모두 거부 — 테두리 없는 포스터는 제외
    reject_picture_person: bool = True
    reject_sculpture_bust: bool = True
    # 3D 입상/주물(스핑크스·니케 등) → PERSON 억제 (RGB 휴리스틱; depth 없음)
    # 사진 스탠디/패널은 skin·채도 분산으로 KEEP — 회색 무광 주물만 reject
    reject_sculptural_person: bool = True
    # Real people / photo standees mislabeled STATUE → reject via skin/clothes/chroma
    reject_human_like_statue: bool = True
    min_person_skin_ratio: float = 0.035
    # 작은 박스에 높은 conf 요구는 끔(원거리 실인물과 충돌) — 액자 휴리스틱이 담당
    min_person_conf_if_small: float = 0.0
    small_person_area_ratio: float = 0.10
    # 약한 액자 단서(흰/금/어두운 틀)일 때 person conf 바닥 — 액자 인물 억제
    # (hard reject는 painted interior + frame cues에서 별도 처리)
    person_in_frame_min_conf: float = 0.78
    reject_uniform_smoke: bool = True
    reject_cold_fire: bool = True
    # Class-aware NMS (post-YOLO); lower IoU = more aggressive same-class merge
    nms_iou: float = 0.45
    statue_nms_iou: float = 0.25
    # Extra pass after NMS: vertical-stack / containment / soft-IoU for statue
    statue_fragment_soft_iou: float = 0.15
    statue_fragment_union: bool = True
    min_statue_box_area_ratio: float = 0.008
    min_statue_aspect: float = 0.55
    max_statue_aspect: float = 4.5
    reject_picture_statue: bool = True
    reject_flat_statue: bool = True
    # Hybrid: companion person loses to statue/fire unless person has human cues
    # Aggressive: any soft/padded statue overlap drops person (sculpture path)
    person_vs_statue_iou: float = 0.10
    person_vs_statue_soft_iou: float = 0.015
    person_vs_statue_pad: float = 0.70
    person_cover_thr: float = 0.15
    person_vs_fire_iou: float = 0.30
    # Weak fire can still suppress person even if below display fire_confidence
    person_vs_fire_anchor_conf: float = 0.22
    # Weak finetune statue (below display statue_confidence) still suppresses person
    person_vs_statue_anchor_conf: float = 0.08
    # When person looks human, drop overlapping statue instead of person
    person_wins_over_statue_when_human: bool = True

    @classmethod
    def adapt_for_resolution(cls, width: int, base: FilterConfig) -> FilterConfig:
        """Loosen size/confirm for 424x240 Wi-Fi streams; keep fire floor high.

        Do NOT crush launcher --person-conf / --statue-conf (Pi/RealSense FP control).
        """
        if width > 480:
            return base
        return FilterConfig(
            # Do not drop below ~0.32 — painting fire FPs are common on Wi-Fi too
            fire_confidence=max(0.32, min(base.fire_confidence, 0.38)),
            smoke_confidence=base.smoke_confidence,
            # Preserve explicit person floor (was wrongly capped at 0.40)
            person_confidence=base.person_confidence,
            statue_confidence=base.statue_confidence,
            model_inference_confidence=base.model_inference_confidence,
            fire_confirm_frames=max(1, min(base.fire_confirm_frames, 2)),
            smoke_confirm_frames=max(1, min(base.smoke_confirm_frames, 2)),
            person_confirm_frames=max(1, min(base.person_confirm_frames, 2)),
            statue_confirm_frames=max(1, min(base.statue_confirm_frames, 2)),
            class_flip_confirm_frames=max(1, min(base.class_flip_confirm_frames, 2)),
            confirm_window=max(base.confirm_window, 6),
            min_box_area_ratio=min(base.min_box_area_ratio, 0.0003),
            min_person_box_area_ratio=min(base.min_person_box_area_ratio, 0.01),
            min_person_height_ratio=min(base.min_person_height_ratio, 0.08),
            min_person_aspect=base.min_person_aspect,
            max_person_top_ratio=base.max_person_top_ratio,
            tall_person_min_aspect=base.tall_person_min_aspect,
            tall_person_max_top_ratio=base.tall_person_max_top_ratio,
            reject_statue_like=base.reject_statue_like,
            reject_picture_person=base.reject_picture_person,
            reject_sculpture_bust=base.reject_sculpture_bust,
            reject_sculptural_person=base.reject_sculptural_person,
            reject_human_like_statue=base.reject_human_like_statue,
            min_person_skin_ratio=base.min_person_skin_ratio,
            min_person_conf_if_small=base.min_person_conf_if_small,
            small_person_area_ratio=base.small_person_area_ratio,
            person_in_frame_min_conf=base.person_in_frame_min_conf,
            reject_uniform_smoke=base.reject_uniform_smoke,
            reject_cold_fire=base.reject_cold_fire,
            nms_iou=base.nms_iou,
            statue_nms_iou=base.statue_nms_iou,
            statue_fragment_soft_iou=base.statue_fragment_soft_iou,
            statue_fragment_union=base.statue_fragment_union,
            min_statue_box_area_ratio=min(base.min_statue_box_area_ratio, 0.006),
            min_statue_aspect=base.min_statue_aspect,
            max_statue_aspect=base.max_statue_aspect,
            reject_picture_statue=base.reject_picture_statue,
            reject_flat_statue=base.reject_flat_statue,
            person_vs_statue_iou=base.person_vs_statue_iou,
            person_vs_statue_soft_iou=base.person_vs_statue_soft_iou,
            person_vs_statue_pad=base.person_vs_statue_pad,
            person_cover_thr=base.person_cover_thr,
            person_vs_fire_iou=base.person_vs_fire_iou,
            person_vs_fire_anchor_conf=base.person_vs_fire_anchor_conf,
            person_vs_statue_anchor_conf=base.person_vs_statue_anchor_conf,
            person_wins_over_statue_when_human=base.person_wins_over_statue_when_human,
        )


@dataclass
class DetectionFilter:
    """Per-class thresholds, ROI heuristics, and rolling temporal confirmation."""

    config: FilterConfig = field(default_factory=FilterConfig)
    _history: Deque[Set[str]] = field(default_factory=lambda: deque(maxlen=8))

    def model_conf_floor(self) -> float:
        """YOLO raw inference floor — separate from per-class display thresholds."""
        return self.config.model_inference_confidence

    def class_confidence(self, cls: str) -> float:
        if cls == 'fire':
            return self.config.fire_confidence
        if cls == 'smoke':
            return self.config.smoke_confidence
        if cls == 'person':
            return self.config.person_confidence
        if cls == 'statue':
            return self.config.statue_confidence
        return self.config.fire_confidence

    def confirm_hits_for(self, cls: str) -> int:
        if cls == 'smoke':
            return self.config.smoke_confirm_frames
        if cls == 'fire':
            return self.config.fire_confirm_frames
        if cls == 'person':
            return self.config.person_confirm_frames
        if cls == 'statue':
            return self.config.statue_confirm_frames
        return 1

    def _passes_confidence(self, box: RawBox) -> bool:
        return box.conf >= self.class_confidence(box.cls)

    def _passes_size(self, box: RawBox, frame_shape: Tuple[int, int, int]) -> bool:
        h, w = frame_shape[:2]
        area = max(0, box.x2 - box.x1) * max(0, box.y2 - box.y1)
        return area >= self.config.min_box_area_ratio * w * h

    def _passes_statue(
        self, box: RawBox, frame: np.ndarray, frame_shape: Tuple[int, int, int],
    ) -> bool:
        """Statue from finetune: higher conf + size/aspect + painting/flat/human rejects."""
        if box.conf < self.config.statue_confidence:
            return False
        h, w = frame_shape[:2]
        bw = max(0, box.x2 - box.x1)
        bh = max(0, box.y2 - box.y1)
        if bw <= 0 or bh <= 0:
            return False
        area_ratio = (bw * bh) / float(max(w * h, 1))
        if area_ratio < self.config.min_statue_box_area_ratio:
            return False
        aspect = bh / float(bw)
        if aspect < self.config.min_statue_aspect or aspect > self.config.max_statue_aspect:
            return False
        if self.config.reject_picture_statue and self._is_inside_picture_frame(frame, box):
            return False
        if self.config.reject_flat_statue and self._is_flat_wall_statue_fp(frame, box):
            return False
        if (
            self.config.reject_human_like_statue
            and self._is_human_like_statue_fp(frame, box)
        ):
            return False
        return True

    def _is_human_like_statue_fp(self, frame: np.ndarray, box: RawBox) -> bool:
        """Reject STATUE on real people / photo standees (skin, clothes, chroma)."""
        if self._has_person_human_cues(frame, box):
            return True
        # Slightly looser path for statue FP (prefer drop statue on people)
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 12 or roi.shape[1] < 10:
            return False
        skin_ratio = float(np.mean(self._skin_mask(roi)))
        face_h = max(1, roi.shape[0] // 3)
        face_skin = float(np.mean(self._skin_mask(roi[:face_h])))
        has_clothes = self._has_clothing_color_variation(roi)
        chroma = self._chroma_mean(roi)
        if has_clothes and chroma >= 8.0:
            return True
        if face_skin >= 0.025 and chroma >= 8.0:
            return True
        if skin_ratio >= 0.035 and chroma >= 9.0:
            return True
        return False

    def _has_person_human_cues(self, frame: np.ndarray, box: RawBox) -> bool:
        """Skin / clothing color / photo texture — real person or printed standee.

        Near-monochrome matte casts (Nike/sphinx) must NOT count as human, or they
        wrongly win over overlapping finetune statue labels.
        """
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 12 or roi.shape[1] < 10:
            return False
        skin_ratio = float(np.mean(self._skin_mask(roi)))
        face_h = max(1, roi.shape[0] // 3)
        face_skin = float(np.mean(self._skin_mask(roi[:face_h])))
        has_clothes = self._has_clothing_color_variation(roi)
        chroma = self._chroma_mean(roi)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        texture = float(np.std(gray))
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_std = float(np.std(hsv[:, :, 1].astype(np.float32)))

        # Grey/dark matte sculpture: never "human" (statue priority over PERSON FP)
        if chroma < 10.0 and not has_clothes:
            return False
        if chroma < 11.5 and skin_ratio < 0.035 and not has_clothes:
            return False

        if face_skin >= 0.035 and chroma >= 10.0:
            return True
        if skin_ratio >= 0.045 and chroma >= 10.5:
            return True
        if has_clothes and chroma >= 10.5:
            return True
        if has_clothes and skin_ratio >= 0.025 and chroma >= 9.0:
            return True
        # Photo / print texture with some skin or chroma (standee)
        if lap >= 160.0 and chroma >= 11.0 and (skin_ratio >= 0.020 or sat_std >= 28.0):
            return True
        if texture >= 42.0 and chroma >= 14.0 and skin_ratio >= 0.028:
            return True
        return False

    def _is_flat_wall_statue_fp(self, frame: np.ndarray, box: RawBox) -> bool:
        """Reject near-uniform wall / painting patches mistaken for statue."""
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 16 or roi.shape[1] < 16:
            return True
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        texture = float(np.std(gray))
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        chroma = self._chroma_mean(roi)
        # Real statues usually have some relief / edge energy; flat paint/wall does not
        if texture < 14.0 and lap < 45.0 and sat_mean < 40.0 and chroma < 12.0:
            return True
        # Large low-texture panel (wall fill) even with a bit more variance
        fh, fw = frame.shape[:2]
        area_ratio = (max(0, box.x2 - box.x1) * max(0, box.y2 - box.y1)) / float(
            max(fh * fw, 1)
        )
        if (
            area_ratio > 0.28
            and texture < 22.0
            and lap < 80.0
            and sat_mean < 48.0
            and chroma < 16.0
            and box.conf < 0.65
        ):
            return True
        return False

    def _passes_person(
        self, box: RawBox, frame: np.ndarray, frame_shape: Tuple[int, int, int],
    ) -> bool:
        if box.conf < self.config.person_confidence:
            return False
        h, w = frame_shape[:2]
        bw = max(0, box.x2 - box.x1)
        bh = max(0, box.y2 - box.y1)
        if bw <= 0 or bh <= 0:
            return False
        area = bw * bh
        area_ratio = area / float(max(w * h, 1))
        if area_ratio < self.config.min_person_box_area_ratio:
            return False
        if bh < self.config.min_person_height_ratio * h:
            return False
        aspect = bh / float(bw)
        if aspect < self.config.min_person_aspect:
            return False
        # 다리만: 박스가 화면 아래쪽에만 있음 (상단이 너무 낮음)
        # 스탠드 포스터는 하체만 잡히는 경우가 많아 세로로 긴 박스는 완화
        top_limit = self.config.max_person_top_ratio
        if aspect >= self.config.tall_person_min_aspect:
            top_limit = max(top_limit, self.config.tall_person_max_top_ratio)
        if box.y1 > top_limit * h:
            return False
        # 그림 속 작은 인물: conf가 매우 높지 않으면 제외 (0이면 비활성)
        if (
            self.config.min_person_conf_if_small > 0
            and area_ratio < self.config.small_person_area_ratio
            and box.conf < self.config.min_person_conf_if_small
        ):
            return False
        if self.config.reject_picture_person:
            if self._is_inside_picture_frame(frame, box):
                return False
            weak_frame = self._has_weak_picture_frame(frame, box)
            painted = self._has_painting_like_interior(frame, box)
            # Hard reject: any frame cue + painted canvas (white/ornate museum frames)
            if weak_frame and painted:
                return False
            # Hard reject: 2+ white/ornate sides on a wall hanging (even mid conf)
            if self._has_hard_frame_person_reject(frame, box):
                return False
            # Weak frame alone: raise conf floor (framed people often flash mid-conf)
            if weak_frame and box.conf < self.config.person_in_frame_min_conf:
                return False
        if self.config.reject_sculpture_bust and self._is_sculpture_bust(frame, box):
            return False
        if self.config.reject_statue_like and self._is_statue_like_person(frame, box):
            return False
        if (
            self.config.reject_sculptural_person
            and self._is_sculptural_3d_person(frame, box)
        ):
            return False
        return True

    def _skin_mask(self, roi: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hch, sch, vch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        return (
            ((hch <= 25) | (hch >= 160))
            & (sch >= 40)
            & (sch <= 180)
            & (vch >= 50)
            & (vch <= 255)
        )

    def _is_sculpture_bust(self, frame: np.ndarray, box: RawBox) -> bool:
        """사람 얼굴 + 동물/조각 몸통(스핑크스·흉상) 패턴 제외."""
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 24 or roi.shape[1] < 16:
            return False
        # Color clothing ⇒ real person / photo poster, not monochrome sculpture
        if self._has_clothing_color_variation(roi):
            return False
        mid = max(1, roi.shape[0] // 2)
        upper, lower = roi[:mid], roi[mid:]
        skin_u = float(np.mean(self._skin_mask(upper)))
        skin_l = float(np.mean(self._skin_mask(lower)))
        hsv_l = cv2.cvtColor(lower, cv2.COLOR_BGR2HSV)
        sat_l = float(np.mean(hsv_l[:, :, 1]))
        val_l = float(np.mean(hsv_l[:, :, 2]))
        chroma_l = self._chroma_mean(lower)
        lower_tex = float(np.std(cv2.cvtColor(lower, cv2.COLOR_BGR2GRAY)))
        extras = self._has_nonhuman_silhouette_extras(roi)
        pedestal = self._has_pedestal_under(frame, box)
        # Face + dark body alone is too broad (black jacket). Require sculpture cues.
        sculpture_body = (
            sat_l < 55
            and chroma_l < 16.0
            and lower_tex < 36.0
            and val_l < 120
            and (extras or pedestal)
        )
        # 위는 얼굴(피부), 아래는 어두운 조각/동물 몸
        if skin_u >= 0.04 and skin_l < 0.02 and sculpture_body and val_l < 110:
            return True
        # 스핑크스류: 얼굴 + 아래가 거의 단색 매트(동물 몸)
        if skin_u >= 0.03 and skin_l < 0.025 and sculpture_body:
            return True
        # 위·아래 톤이 크게 갈라진 흉상
        hsv_u = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
        val_u = float(np.mean(hsv_u[:, :, 2]))
        if (
            skin_u >= 0.05
            and skin_l < 0.015
            and abs(val_u - val_l) > 45
            and sculpture_body
        ):
            return True
        # 머리 없는 고전상: 상단도 피부 없고 단색 석재/브론즈
        sat_u = float(np.mean(hsv_u[:, :, 1]))
        chroma_u = self._chroma_mean(upper)
        if (
            skin_u < 0.02
            and skin_l < 0.02
            and sat_u < 45
            and sat_l < 45
            and chroma_u < 16.0
            and chroma_l < 16.0
            and pedestal
        ):
            return True
        # Solid dark/grey cast (sphinx): no skin, low chroma whole body
        if (
            skin_u < 0.03
            and skin_l < 0.03
            and sat_u < 52
            and sat_l < 52
            and chroma_u < 16.0
            and chroma_l < 16.0
            and val_l < 135
            and lower_tex < 42.0
            and (extras or pedestal or (val_l < 120 and sat_l < 40))
        ):
            return True
        return False

    def _is_inside_picture_frame(self, frame: np.ndarray, box: RawBox) -> bool:
        """액자(어두운·금색·흰색 장식 사각 테두리) 안의 그려진 인물/불꽃 제외.

        테두리 없는 스탠드 포스터는 보드 외곽선만 있어서 Canny 사각형에 오인되기
        쉬우므로, 어두운/금색/흰색 액자틀(림) 증거 위주로 판정한다.
        """
        if self._is_inside_dark_picture_frame(frame, box):
            return True
        if self._has_dark_frame_sides(frame, box):
            return True
        if self._is_inside_ornate_picture_frame(frame, box):
            return True
        if self._has_ornate_frame_sides(frame, box):
            return True
        # White / cream ornate museum frames (e.g. Goya print)
        if self._is_inside_white_picture_frame(frame, box):
            return True
        # White moulding alone is not enough (light walls look similar) —
        # require painting-like interior / wall-hanging combo
        if self._has_white_framed_painting_combo(frame, box):
            return True
        # 2면 어두운 틀 + 유리 반사 / 금색 한 면 → 액자 그림
        if self._has_framed_painting_combo(frame, box):
            return True
        return False

    def _has_weak_picture_frame(self, frame: np.ndarray, box: RawBox) -> bool:
        """부분 액자 단서(2면 테두리 또는 유리 반사) — 낮은 conf person 억제용."""
        dark = self._count_dark_frame_sides(frame, box)
        ornate = self._count_ornate_frame_sides(frame, box)
        white = self._count_white_frame_sides(frame, box)
        ornate_w = self._count_ornate_white_frame_sides(frame, box)
        painted = self._has_painting_like_interior(frame, box)
        hanging = self._looks_like_wall_hanging(frame, box)
        if dark >= 2 or ornate >= 2:
            return True
        # White / cream moulding (Pi camera often only catches 1–2 sides)
        if white >= 2:
            return True
        # Ornate white alone is noisy on gallery walls — pair with paint/hanging
        if ornate_w >= 2 and (painted or hanging):
            return True
        if white >= 1 and (painted or hanging or ornate_w >= 1):
            return True
        if ornate_w >= 1 and painted:
            return True
        if self._has_glass_glare(frame, box) and (dark >= 1 or ornate >= 1 or white >= 1):
            return True
        if self._has_glass_glare(frame, box) and painted:
            return True
        if white >= 1 and hanging and painted:
            return True
        return False

    def _has_hard_frame_person_reject(self, frame: np.ndarray, box: RawBox) -> bool:
        """White/ornate museum frame → drop PERSON regardless of conf.

        Prefer dropping framed painting people over rare standee FNs near frames.
        """
        dark = self._count_dark_frame_sides(frame, box)
        ornate = self._count_ornate_frame_sides(frame, box)
        white = self._count_white_frame_sides(frame, box)
        ornate_w = self._count_ornate_white_frame_sides(frame, box)
        painted = self._has_painting_like_interior(frame, box)
        hanging = self._looks_like_wall_hanging(frame, box)
        # 2+ true white sides on wall hanging — classic museum print
        if white >= 2 and hanging:
            return True
        if white >= 2 and painted:
            return True
        # Ornate white needs painted interior (gallery wall ≠ frame)
        if ornate_w >= 2 and painted:
            return True
        # Single thick white/ornate side + painted canvas + hanging
        if (white >= 1 or ornate_w >= 1) and painted and hanging:
            return True
        # Dark/gold 2+ sides + painted interior
        if (dark >= 2 or ornate >= 2) and painted:
            return True
        # Glass glare over a hanging painted figure
        if self._has_glass_glare(frame, box) and painted and (hanging or white >= 1 or dark >= 1):
            return True
        return False

    def _has_framed_painting_combo(self, frame: np.ndarray, box: RawBox) -> bool:
        """2+ 어두운 면 + (유리 반사 또는 금색 1면) → hard reject framed painting."""
        dark = self._count_dark_frame_sides(frame, box)
        ornate = self._count_ornate_frame_sides(frame, box)
        if dark >= 2 and (self._has_glass_glare(frame, box) or ornate >= 1):
            return True
        if ornate >= 2 and dark >= 1:
            return True
        return False

    def _has_white_framed_painting_combo(self, frame: np.ndarray, box: RawBox) -> bool:
        """White/cream ornate sides + painting-like canvas → hard reject (Goya case)."""
        white = self._count_white_frame_sides(frame, box)
        painted = self._has_painting_like_interior(frame, box)
        hanging = self._looks_like_wall_hanging(frame, box)
        ornate_w = self._count_ornate_white_frame_sides(frame, box)
        # Prefer painted interior — light walls + standees must not match
        if painted and white >= 1:
            return True
        if painted and ornate_w >= 1:
            return True
        if white >= 1 and ornate_w >= 1 and (painted or hanging):
            return True
        # Two white sides on a wall hanging even if paint cue is borderline
        if white >= 2 and hanging:
            return True
        # Ornate white alone needs painted canvas (avoid standee + gallery wall)
        if ornate_w >= 2 and hanging and painted:
            return True
        if white >= 2 and ornate_w >= 1:
            return True
        return False

    def _has_painting_like_interior(self, frame: np.ndarray, box: RawBox) -> bool:
        """Canvas content: dark/muted paint, little photo-skin, not a live person."""
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 16 or roi.shape[1] < 12:
            return False
        skin_ratio = float(np.mean(self._skin_mask(roi)))
        has_clothes = self._has_clothing_color_variation(roi)
        # Photo people / standees usually have measurable skin — keep those
        if skin_ratio >= 0.060:
            return False
        if has_clothes and skin_ratio >= 0.030:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        val_mean = float(np.mean(gray))
        chroma = self._chroma_mean(roi)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        # Dark painted figure (Saturn-like) or muted canvas
        dark_paint = val_mean < 110.0 and skin_ratio < 0.050
        muted_canvas = (
            val_mean < 145.0
            and skin_ratio < 0.045
            and chroma < 26.0
            and sat_mean < 80.0
        )
        # Warm/brown classical painting without photo clothing hues
        warm_paint = (
            not has_clothes
            and skin_ratio < 0.040
            and chroma < 22.0
            and sat_mean < 70.0
            and val_mean < 150.0
        )
        return bool(dark_paint or muted_canvas or warm_paint)

    def _looks_like_wall_hanging(self, frame: np.ndarray, box: RawBox) -> bool:
        """Painting hanging mid-wall — not a floor standee (tall + bottom near floor)."""
        h = frame.shape[0]
        bw = max(1, box.x2 - box.x1)
        bh = max(1, box.y2 - box.y1)
        aspect = bh / float(bw)
        # Standees are usually very tall and touch the lower frame
        if aspect >= 2.2 and box.y2 >= 0.88 * h:
            return False
        hanging = box.y2 < 0.92 * h and box.y1 > 0.02 * h
        painting_aspect = 0.55 <= aspect <= 2.1
        return bool(hanging and painting_aspect)

    def _has_glass_glare(self, frame: np.ndarray, box: RawBox) -> bool:
        """액자 유리 반사 — 작은 고휘도 specular blob (전체 과노출 제외)."""
        # Sample box + thin outer rim (glass often flashes near frame edge)
        h, w = frame.shape[:2]
        pad = max(4, int(0.04 * max(box.x2 - box.x1, box.y2 - box.y1)))
        x1 = max(0, box.x1 - pad)
        y1 = max(0, box.y1 - pad)
        x2 = min(w, box.x2 + pad)
        y2 = min(h, box.y2 + pad)
        region = frame[y1:y2, x1:x2]
        if region.size == 0 or region.shape[0] < 20 or region.shape[1] < 20:
            return False
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        bright = gray >= 225
        bright_frac = float(np.mean(bright))
        # Specular streak: small but present; whole overexposed face ≠ glass
        if bright_frac < 0.006 or bright_frac > 0.18:
            return False
        # Prefer upper half (museum lighting often hits glass from above)
        upper = bright[: max(1, bright.shape[0] // 2)]
        upper_frac = float(np.mean(upper))
        sat = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)[:, :, 1]
        # Glass glare is bright AND desaturated
        glare = bright & (sat < 55)
        glare_frac = float(np.mean(glare))
        if glare_frac >= 0.008 and upper_frac >= bright_frac * 0.45:
            return True
        # Thin elongated bright streak along a border
        t = max(2, min(region.shape[:2]) // 20)
        border = np.zeros_like(bright, dtype=bool)
        border[:t, :] = True
        border[-t:, :] = True
        border[:, :t] = True
        border[:, -t:] = True
        border_glare = float(np.mean(glare[border])) if border.any() else 0.0
        return border_glare >= 0.04 and glare_frac >= 0.005

    @staticmethod
    def _ornate_gold_mask(bgr: np.ndarray) -> np.ndarray:
        """Gold / brass / warm ornate frame pixels (HSV)."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        hch, sch, vch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        # Yellow–amber metal; also darker gilt / warm wood-gilt
        bright_gold = (hch >= 8) & (hch <= 42) & (sch >= 55) & (vch >= 90)
        deep_gilt = (hch >= 5) & (hch <= 35) & (sch >= 70) & (vch >= 55) & (vch < 90)
        return bright_gold | deep_gilt

    def _is_inside_dark_picture_frame(self, frame: np.ndarray, box: RawBox) -> bool:
        """어두운 사각 액자틀 — morph-gradient 외곽 + 원본 밝기 림 검사."""
        h, w = frame.shape[:2]
        pad = int(0.15 * max(h, w))
        x1 = max(0, box.x1 - pad)
        y1 = max(0, box.y1 - pad)
        x2 = min(w, box.x2 + pad)
        y2 = min(h, box.y2 + pad)
        region = frame[y1:y2, x1:x2]
        if region.size == 0 or region.shape[0] < 40 or region.shape[1] < 40:
            return False

        gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        dark = (gray < 60).astype(np.uint8) * 255
        # 채우지 않고 경계만 — 어두운 그림 속까지 메우면 림/속이 구분이 안 됨
        grad = cv2.morphologyEx(dark, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        grad = cv2.dilate(grad, np.ones((3, 3), np.uint8), iterations=1)
        contours, _ = cv2.findContours(grad, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        person_area = max(1, (box.x2 - box.x1) * (box.y2 - box.y1))
        pcx = 0.5 * (box.x1 + box.x2)
        pcy = 0.5 * (box.y1 + box.y2)

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < 1.2 * person_area:
                continue
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if rw < 40 or rh < 40:
                continue
            aspect = rw / float(rh)
            if aspect < 0.4 or aspect > 3.0:
                continue
            abs_x1, abs_y1 = x1 + rx, y1 + ry
            abs_x2, abs_y2 = abs_x1 + rw, abs_y1 + rh
            if not (abs_x1 <= pcx <= abs_x2 and abs_y1 <= pcy <= abs_y2):
                continue
            ix1 = max(box.x1, abs_x1)
            iy1 = max(box.y1, abs_y1)
            ix2 = min(box.x2, abs_x2)
            iy2 = min(box.y2, abs_y2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter / person_area < 0.70:
                continue
            frame_area = max(1, rw * rh)
            if person_area / frame_area > 0.80:
                continue
            # 원본 그레이도에서 테두리만 어두운지 (포스터 옷 덩어리와 구분)
            t = max(4, min(rw, rh) // 28)
            rim = np.zeros((h, w), dtype=np.uint8)
            rim[abs_y1:abs_y1 + t, abs_x1:abs_x2] = 1
            rim[abs_y2 - t:abs_y2, abs_x1:abs_x2] = 1
            rim[abs_y1:abs_y2, abs_x1:abs_x1 + t] = 1
            rim[abs_y1:abs_y2, abs_x2 - t:abs_x2] = 1
            rim_mask = rim.astype(bool)
            if not rim_mask.any():
                continue
            rim_dark = float(np.mean(gray_full[rim_mask] < 55))
            if rim_dark >= 0.28 and person_area / frame_area < 0.78:
                return True
        return False

    def _is_inside_ornate_picture_frame(self, frame: np.ndarray, box: RawBox) -> bool:
        """금색/장식 사각 액자틀 — gold morph-gradient + rim gold ratio."""
        h, w = frame.shape[:2]
        pad = int(0.18 * max(h, w))
        x1 = max(0, box.x1 - pad)
        y1 = max(0, box.y1 - pad)
        x2 = min(w, box.x2 + pad)
        y2 = min(h, box.y2 + pad)
        region = frame[y1:y2, x1:x2]
        if region.size == 0 or region.shape[0] < 40 or region.shape[1] < 40:
            return False

        gold = self._ornate_gold_mask(region).astype(np.uint8) * 255
        if float(np.mean(gold > 0)) < 0.02:
            return False
        grad = cv2.morphologyEx(gold, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
        grad = cv2.dilate(grad, np.ones((3, 3), np.uint8), iterations=2)
        contours, _ = cv2.findContours(grad, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        box_area = max(1, (box.x2 - box.x1) * (box.y2 - box.y1))
        pcx = 0.5 * (box.x1 + box.x2)
        pcy = 0.5 * (box.y1 + box.y2)

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < 1.15 * box_area:
                continue
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if rw < 40 or rh < 40:
                continue
            aspect = rw / float(rh)
            if aspect < 0.35 or aspect > 3.2:
                continue
            abs_x1, abs_y1 = x1 + rx, y1 + ry
            abs_x2, abs_y2 = abs_x1 + rw, abs_y1 + rh
            if not (abs_x1 <= pcx <= abs_x2 and abs_y1 <= pcy <= abs_y2):
                continue
            ix1 = max(box.x1, abs_x1)
            iy1 = max(box.y1, abs_y1)
            ix2 = min(box.x2, abs_x2)
            iy2 = min(box.y2, abs_y2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter / box_area < 0.65:
                continue
            frame_area = max(1, rw * rh)
            if box_area / frame_area > 0.82:
                continue
            t = max(5, min(rw, rh) // 22)
            rim = np.zeros((h, w), dtype=np.uint8)
            rim[abs_y1:abs_y1 + t, abs_x1:abs_x2] = 1
            rim[abs_y2 - t:abs_y2, abs_x1:abs_x2] = 1
            rim[abs_y1:abs_y2, abs_x1:abs_x1 + t] = 1
            rim[abs_y1:abs_y2, abs_x2 - t:abs_x2] = 1
            rim_mask = rim.astype(bool)
            if not rim_mask.any():
                continue
            # Sample only rim pixels via mask on full frame gold
            full_gold = self._ornate_gold_mask(frame)
            rim_gold = float(np.mean(full_gold[rim_mask]))
            if rim_gold >= 0.22 and box_area / frame_area < 0.78:
                return True
        return False

    def _count_dark_frame_sides(self, frame: np.ndarray, box: RawBox) -> int:
        """박스 바깥 4방향 중 어두운 액자 띠 개수."""
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        search = max(20, int(0.08 * max(h, w)))
        x1, y1, x2, y2 = box.x1, box.y1, box.x2, box.y2
        strips = {
            'left': (max(0, x1 - search), x1, y1, y2),
            'right': (x2, min(w, x2 + search), y1, y2),
            'top': (x1, x2, max(0, y1 - search), y1),
            'bottom': (x1, x2, y2, min(h, y2 + search)),
        }
        dark_sides = 0
        for side, (xs, xe, ys, ye) in strips.items():
            if xe <= xs or ye <= ys:
                continue
            strip = gray[ys:ye, xs:xe]
            if strip.size == 0:
                continue
            if side in ('left', 'right'):
                best = float(np.min(strip.mean(axis=0)))
            else:
                best = float(np.min(strip.mean(axis=1)))
            dark_frac = float(np.mean(strip < 55))
            # Slightly looser than before — catch thinner museum frames
            if best < 36.0 or (best < 50.0 and dark_frac >= 0.35):
                dark_sides += 1
        return dark_sides

    def _has_dark_frame_sides(self, frame: np.ndarray, box: RawBox) -> bool:
        """박스 바깥 4방향에 어두운 액자 띠가 있는지 (3면 이상)."""
        return self._count_dark_frame_sides(frame, box) >= 3

    def _count_ornate_frame_sides(self, frame: np.ndarray, box: RawBox) -> int:
        """박스 바깥 4방향 중 금색/장식 액자 띠 개수."""
        h, w = frame.shape[:2]
        search = max(22, int(0.10 * max(h, w)))
        x1, y1, x2, y2 = box.x1, box.y1, box.x2, box.y2
        strips = {
            'left': (max(0, x1 - search), x1, y1, y2),
            'right': (x2, min(w, x2 + search), y1, y2),
            'top': (x1, x2, max(0, y1 - search), y1),
            'bottom': (x1, x2, y2, min(h, y2 + search)),
        }
        ornate_sides = 0
        for side, (xs, xe, ys, ye) in strips.items():
            if xe <= xs or ye <= ys:
                continue
            strip = frame[ys:ye, xs:xe]
            if strip.size == 0 or strip.shape[0] < 2 or strip.shape[1] < 2:
                continue
            gold = self._ornate_gold_mask(strip)
            gold_frac = float(np.mean(gold))
            if side in ('left', 'right'):
                col_frac = gold.mean(axis=0) if gold.size else np.array([0.0])
                best_col = float(np.max(col_frac)) if col_frac.size else 0.0
            else:
                row_frac = gold.mean(axis=1) if gold.size else np.array([0.0])
                best_col = float(np.max(row_frac)) if row_frac.size else 0.0
            gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
            edge = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if gold_frac >= 0.16 or best_col >= 0.32:
                ornate_sides += 1
            elif gold_frac >= 0.08 and best_col >= 0.20 and edge > 160:
                ornate_sides += 1
        return ornate_sides

    def _has_ornate_frame_sides(self, frame: np.ndarray, box: RawBox) -> bool:
        """박스 바깥 4방향에 금색/장식 액자 띠 (3면 이상) — 포스터(무테)는 해당 없음."""
        return self._count_ornate_frame_sides(frame, box) >= 3

    @staticmethod
    def _white_ornate_mask(bgr: np.ndarray) -> np.ndarray:
        """White / cream / off-white ornate frame moulding (HSV)."""
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        sch, vch = hsv[:, :, 1], hsv[:, :, 2]
        # Bright white/cream moulding; allow slight warm cast (looser for Pi/Goya)
        bright_white = (vch >= 160) & (sch <= 70)
        cream = (vch >= 138) & (vch < 160) & (sch <= 58)
        return bright_white | cream

    def _count_white_frame_sides(self, frame: np.ndarray, box: RawBox) -> int:
        """박스 바깥 4방향 중 흰색/크림 액자 띠 개수."""
        h, w = frame.shape[:2]
        search = max(24, int(0.12 * max(h, w)))
        x1, y1, x2, y2 = box.x1, box.y1, box.x2, box.y2
        roi = self._roi(frame, box)
        if roi.size == 0:
            return 0
        interior_mean = float(np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)))
        strips = {
            'left': (max(0, x1 - search), x1, y1, y2),
            'right': (x2, min(w, x2 + search), y1, y2),
            'top': (x1, x2, max(0, y1 - search), y1),
            'bottom': (x1, x2, y2, min(h, y2 + search)),
        }
        white_sides = 0
        for side, (xs, xe, ys, ye) in strips.items():
            if xe <= xs or ye <= ys:
                continue
            strip = frame[ys:ye, xs:xe]
            if strip.size == 0 or strip.shape[0] < 2 or strip.shape[1] < 2:
                continue
            white = self._white_ornate_mask(strip)
            white_frac = float(np.mean(white))
            if side in ('left', 'right'):
                col_frac = white.mean(axis=0) if white.size else np.array([0.0])
                best_col = float(np.max(col_frac)) if col_frac.size else 0.0
            else:
                row_frac = white.mean(axis=1) if white.size else np.array([0.0])
                best_col = float(np.max(row_frac)) if row_frac.size else 0.0
            gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
            edge = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            strip_mean = float(np.mean(gray))
            # True white/cream moulding (not a light grey wall behind a standee)
            if strip_mean < 160.0:
                continue
            # Rim clearly brighter than canvas interior (lowered for brief flashes)
            if strip_mean < interior_mean + 18.0:
                continue
            # Require edge/texture so flat museum walls do not count as frames
            if edge < 40.0:
                continue
            # Thick white moulding OR ornate carved white (looser for Pi)
            if white_frac >= 0.16 or best_col >= 0.36:
                white_sides += 1
            elif white_frac >= 0.08 and best_col >= 0.24 and edge > 70:
                white_sides += 1
        return white_sides

    def _count_ornate_white_frame_sides(self, frame: np.ndarray, box: RawBox) -> int:
        """White moulding with carved/edge texture (ornate, not plain wall)."""
        h, w = frame.shape[:2]
        search = max(24, int(0.12 * max(h, w)))
        x1, y1, x2, y2 = box.x1, box.y1, box.x2, box.y2
        roi = self._roi(frame, box)
        if roi.size == 0:
            return 0
        interior_mean = float(np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)))
        strips = {
            'left': (max(0, x1 - search), x1, y1, y2),
            'right': (x2, min(w, x2 + search), y1, y2),
            'top': (x1, x2, max(0, y1 - search), y1),
            'bottom': (x1, x2, y2, min(h, y2 + search)),
        }
        ornate = 0
        for side, (xs, xe, ys, ye) in strips.items():
            if xe <= xs or ye <= ys:
                continue
            strip = frame[ys:ye, xs:xe]
            if strip.size == 0 or strip.shape[0] < 3 or strip.shape[1] < 3:
                continue
            white = self._white_ornate_mask(strip)
            white_frac = float(np.mean(white))
            gray = cv2.cvtColor(strip, cv2.COLOR_BGR2GRAY)
            edge = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            strip_mean = float(np.mean(gray))
            # Must look like bright moulding, not flat gallery wall next to a standee
            if strip_mean < 165.0 or strip_mean < interior_mean + 20.0:
                continue
            if white_frac >= 0.14 and edge > 100:
                ornate += 1
        return ornate

    def _has_white_frame_sides(self, frame: np.ndarray, box: RawBox) -> bool:
        """박스 바깥 흰색/크림 액자 띠 3면 이상."""
        return self._count_white_frame_sides(frame, box) >= 3

    def _is_inside_white_picture_frame(self, frame: np.ndarray, box: RawBox) -> bool:
        """흰색/크림 장식 사각 액자틀 — white morph-gradient + rim ratio."""
        h, w = frame.shape[:2]
        pad = int(0.18 * max(h, w))
        x1 = max(0, box.x1 - pad)
        y1 = max(0, box.y1 - pad)
        x2 = min(w, box.x2 + pad)
        y2 = min(h, box.y2 + pad)
        region = frame[y1:y2, x1:x2]
        if region.size == 0 or region.shape[0] < 40 or region.shape[1] < 40:
            return False

        white = self._white_ornate_mask(region).astype(np.uint8) * 255
        if float(np.mean(white > 0)) < 0.03:
            return False
        grad = cv2.morphologyEx(white, cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8))
        grad = cv2.dilate(grad, np.ones((3, 3), np.uint8), iterations=2)
        contours, _ = cv2.findContours(grad, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        box_area = max(1, (box.x2 - box.x1) * (box.y2 - box.y1))
        pcx = 0.5 * (box.x1 + box.x2)
        pcy = 0.5 * (box.y1 + box.y2)

        for cnt in contours:
            area = float(cv2.contourArea(cnt))
            if area < 1.15 * box_area:
                continue
            rx, ry, rw, rh = cv2.boundingRect(cnt)
            if rw < 40 or rh < 40:
                continue
            aspect = rw / float(rh)
            if aspect < 0.35 or aspect > 3.2:
                continue
            abs_x1, abs_y1 = x1 + rx, y1 + ry
            abs_x2, abs_y2 = abs_x1 + rw, abs_y1 + rh
            if not (abs_x1 <= pcx <= abs_x2 and abs_y1 <= pcy <= abs_y2):
                continue
            ix1 = max(box.x1, abs_x1)
            iy1 = max(box.y1, abs_y1)
            ix2 = min(box.x2, abs_x2)
            iy2 = min(box.y2, abs_y2)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            if inter / box_area < 0.65:
                continue
            frame_area = max(1, rw * rh)
            if box_area / frame_area > 0.82:
                continue
            t = max(5, min(rw, rh) // 22)
            rim = np.zeros((h, w), dtype=np.uint8)
            rim[abs_y1:abs_y1 + t, abs_x1:abs_x2] = 1
            rim[abs_y2 - t:abs_y2, abs_x1:abs_x2] = 1
            rim[abs_y1:abs_y2, abs_x1:abs_x1 + t] = 1
            rim[abs_y1:abs_y2, abs_x2 - t:abs_x2] = 1
            rim_mask = rim.astype(bool)
            if not rim_mask.any():
                continue
            full_white = self._white_ornate_mask(frame)
            rim_white = float(np.mean(full_white[rim_mask]))
            if rim_white >= 0.22 and box_area / frame_area < 0.80:
                # Prefer painted interior (avoid rejecting bright standee faces)
                if self._has_painting_like_interior(frame, box) or rim_white >= 0.35:
                    return True
        return False

    @staticmethod
    def _chroma_mean(bgr: np.ndarray) -> float:
        """Mean per-pixel channel spread — near 0 for monochrome/matte surfaces."""
        if bgr.size == 0:
            return 0.0
        b, g, r = cv2.split(bgr.astype(np.float32))
        return float(np.mean((np.abs(r - g) + np.abs(g - b) + np.abs(b - r)) / 3.0))

    def _has_clothing_color_variation(self, roi: np.ndarray) -> bool:
        """Color photo posters / real people usually have multi-hue clothing.

        Statues (bronze, painted matte, stone) are near-monochrome — lack this.
        """
        if roi.size == 0 or roi.shape[0] < 16:
            return False
        # Ignore head band; clothing lives mid/lower
        body = roi[roi.shape[0] // 4 :, :, :]
        if body.size == 0:
            return False
        hsv = cv2.cvtColor(body, cv2.COLOR_BGR2HSV)
        hch, sch, vch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        colorful = (sch >= 50) & (vch >= 45) & (vch <= 245)
        colorful_frac = float(np.mean(colorful))
        if colorful_frac < 0.08:
            return False
        hues = hch[colorful]
        # 18 bins of 10° — need ≥2 distinct clothing hue peaks
        hist = np.bincount((hues // 10).astype(np.int32), minlength=18)
        peak_floor = max(8, int(0.04 * hues.size))
        peaks = int(np.sum(hist >= peak_floor))
        sat_std = float(np.std(sch[colorful].astype(np.float32)))
        return peaks >= 2 or (peaks >= 1 and sat_std >= 35.0 and colorful_frac >= 0.15)

    def _has_pedestal_under(self, frame: np.ndarray, box: RawBox) -> bool:
        """Detect a short rectangular base/plinth immediately under the box."""
        h, w = frame.shape[:2]
        bw = max(1, box.x2 - box.x1)
        bh = max(1, box.y2 - box.y1)
        # Search a shallow band under the figure
        y0 = min(h, box.y2)
        y1 = min(h, box.y2 + max(8, int(0.18 * bh)))
        if y1 - y0 < 6:
            return False
        # Match figure width closely — wide pad pulls in bright wall and kills plinth stats
        pad_x = max(2, int(0.04 * bw))
        x0 = max(0, box.x1 - pad_x)
        x1 = min(w, box.x2 + pad_x)
        band = frame[y0:y1, x0:x1]
        if band.size == 0:
            return False

        gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
        sat = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)[:, :, 1]
        # Prefer the central columns (plinth under feet, not side wall)
        c0 = max(0, gray.shape[1] // 8)
        c1 = max(c0 + 1, gray.shape[1] - gray.shape[1] // 8)
        gray_c = gray[:, c0:c1]
        sat_c = sat[:, c0:c1]
        row_means = gray_c.mean(axis=1)
        col_means = gray_c.mean(axis=0)
        col_std = float(np.std(col_means))
        row_std = float(np.std(row_means))
        sat_mean = float(np.mean(sat_c))
        sobel_y = cv2.Sobel(gray_c, cv2.CV_32F, 0, 1, ksize=3)
        ledge = float(np.mean(np.abs(sobel_y[: max(2, gray_c.shape[0] // 3), :])))

        roi = self._roi(frame, box)
        if roi.size == 0:
            return False
        # Bottom 15% — plinth lip inside the box (avoid mixing torso+base)
        rb_full = roi[max(0, int(roi.shape[0] * 0.85)) :, :, :]
        mid_full = roi[roi.shape[0] // 2: max(roi.shape[0] // 2 + 1, int(roi.shape[0] * 0.75)), :, :]
        # Central columns only — side wall inside the box skews plinth stats
        def _center(bgr: np.ndarray) -> np.ndarray:
            if bgr.size == 0 or bgr.shape[1] < 8:
                return bgr
            c0 = bgr.shape[1] // 8
            c1 = max(c0 + 1, bgr.shape[1] - bgr.shape[1] // 8)
            return bgr[:, c0:c1]

        rb = _center(rb_full)
        mid = _center(mid_full)
        rb_gray = cv2.cvtColor(rb, cv2.COLOR_BGR2GRAY) if rb.size else None
        mid_gray = cv2.cvtColor(mid, cv2.COLOR_BGR2GRAY) if mid.size else None
        rb_mean = float(np.mean(rb_gray)) if rb_gray is not None else 0.0
        mid_mean = float(np.mean(mid_gray)) if mid_gray is not None else rb_mean
        rb_tex = float(np.std(rb_gray)) if rb_gray is not None else 0.0
        band_mean = float(np.mean(gray_c))
        band_tex = float(np.std(gray_c))

        # Require band to look like a plinth near the figure — not open bright floor
        # under dark pants (floor is much brighter / unrelated tone).
        mean_gap = abs(band_mean - rb_mean)
        tone_coupled = band_mean <= rb_mean + 40.0
        uniform_plinth = (
            sat_mean < 48
            and row_std < 14.0
            and col_std < 22.0
            and band_tex < 22.0
            and mean_gap >= 8.0
            and tone_coupled
        )
        ledge_plinth = (
            ledge > 18.0
            and sat_mean < 55
            and band_tex < 24.0
            and mean_gap >= 8.0
            and tone_coupled
        )
        # Museum white / light plinth under dark cast sculpture (sphinx base)
        bright_plinth = (
            rb_mean < 115
            and band_mean >= rb_mean + 28.0
            and sat_mean < 42
            and band_tex < 30.0
            and row_std < 20.0
            and col_std < 28.0
        )
        # Bottom of figure itself looks like a cut block (plinth inside box)
        # Must differ from mid-body tone so solid dark pants don't count.
        body_step = abs(rb_mean - mid_mean)
        bottom_flat = (
            rb.size > 0
            and float(np.mean(cv2.cvtColor(rb, cv2.COLOR_BGR2HSV)[:, :, 1])) < 42
            and rb_tex < 22.0
            and self._chroma_mean(rb) < 12.0
            and body_step >= 12.0
        )
        return bool(uniform_plinth or ledge_plinth or bright_plinth or bottom_flat)

    def _has_nonhuman_silhouette_extras(self, roi: np.ndarray) -> bool:
        """Wings / animal body / headless mass via dark-fg width profile."""
        if roi.size == 0 or roi.shape[0] < 24 or roi.shape[1] < 16:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Dark matte sculpture vs brighter museum wall
        thr = float(np.percentile(gray, 45))
        fg = gray < max(40.0, min(thr, 120.0))
        fg_frac = float(np.mean(fg))
        # Solid dark cast (sphinx): almost all ROI is the figure — still usable
        if fg_frac > 0.92:
            thr2 = float(np.percentile(gray, 70))
            fg = gray < max(50.0, min(thr2, 160.0))
            fg_frac = float(np.mean(fg))
        if fg_frac < 0.12 or fg_frac > 0.97:
            return False

        h, w = fg.shape
        thirds = [fg[i * h // 3: (i + 1) * h // 3, :] for i in range(3)]
        widths = []
        for band in thirds:
            if band.size == 0:
                widths.append(0.0)
                continue
            cols = np.any(band, axis=0)
            if not np.any(cols):
                widths.append(0.0)
                continue
            idx = np.where(cols)[0]
            widths.append(float(idx[-1] - idx[0] + 1) / float(w))

        top_w, mid_w, bot_w = widths
        # Wings (Nike): upper much wider than mid/lower torso
        if top_w >= 0.72 and top_w > mid_w * 1.25 and top_w > bot_w * 1.20:
            return True
        # Sphinx / animal body: lower much wider than upper (crouching beast).
        # Require real upper mass — bright faces make top_w≈0 and must not count.
        if (
            bot_w >= 0.65
            and top_w >= 0.18
            and bot_w > top_w * 1.20
            and mid_w > top_w * 1.05
        ):
            return True
        # Headless classical: top band sparse vs mid mass, and no face/skin up top
        if mid_w >= 0.55 and top_w < mid_w * 0.55 and top_w < 0.40:
            top_skin = float(np.mean(self._skin_mask(roi[: max(1, h // 3)])))
            if top_skin < 0.02:
                return True
        return False

    def _is_sculptural_3d_person(self, frame: np.ndarray, box: RawBox) -> bool:
        """Reject solid 3D casts (Nike / sphinx / bronze) mislabeled as PERSON.

        KEEP (return False) for photo standees / flat panels when any cue holds:
        face-region skin, clothing color, high chroma / print texture.
        Only grey/dark matte uniform casts with sculpture cues reject.
        Dark/underexposed printed panels: change the photo — do not loosen KEEP.
        """
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 16 or roi.shape[1] < 12:
            return False

        has_clothes = self._has_clothing_color_variation(roi)
        skin_ratio = float(np.mean(self._skin_mask(roi)))
        face_h = max(1, roi.shape[0] // 3)
        face_skin = float(np.mean(self._skin_mask(roi[:face_h])))

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sch = hsv[:, :, 1]
        vch = hsv[:, :, 2]
        sat_mean = float(np.mean(sch))
        sat_std = float(np.std(sch.astype(np.float32)))
        val_mean = float(np.mean(vch))
        val_std = float(np.std(vch.astype(np.float32)))
        chroma = self._chroma_mean(roi)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        texture = float(np.std(gray))
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        b, g, r = cv2.split(roi.astype(np.float32))
        chroma_map = (np.abs(r - g) + np.abs(g - b) + np.abs(b - r)) / 3.0
        chroma_edge = float(np.std(chroma_map))

        # --- Standee / real-person KEEP (any one cue) ---
        # HSV "skin" alone can fire on warm-lit dark cast paint (sphinx); require
        # photo-like RGB chroma, or clothing hues. Bright standees still KEEP.
        # Raised chroma floors — Pi/RealSense statues must not KEEP on faint skin.
        if (face_skin >= 0.040 or skin_ratio >= 0.050) and (
            chroma >= 11.0 or has_clothes
        ):
            return False
        if has_clothes and chroma >= 11.0:
            return False
        # High chroma / print texture → keep panel (chroma_edge alone can be
        # floor/edge noise on monochrome casts — pair with mean chroma)
        if chroma >= 16.0 or (chroma_edge >= 15.0 and chroma >= 11.0):
            return False
        if sat_std >= 32.0 and chroma >= 11.0:
            return False
        # Photo print often has higher local edge energy than matte cast
        if lap >= 240.0 and chroma >= 12.0:
            return False

        # Matte grey / dark cast body (aggressive for Nike/sphinx dark casts)
        grey_matte = (sch < 70) & (vch < 175) & (vch > 10)
        dark_matte = (sch < 65) & (vch < 135) & (vch > 10)
        grey_ratio = float(np.mean(grey_matte))
        dark_ratio = float(np.mean(dark_matte))
        matte_ok = grey_ratio >= 0.38 or dark_ratio >= 0.28
        # Dark pixels inflate HSV sat while RGB chroma stays near-mono — trust chroma
        if not matte_ok or chroma >= 15.0:
            return False
        if sat_mean >= 58 and chroma >= 9.5:
            return False

        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        grad_mag = float(np.mean(np.sqrt(gx * gx + gy * gy)))
        # Flat lighting (standee) vs 3D relief shading
        shading_3d = (
            grad_mag >= 11.0
            and chroma_edge < 14.0
            and sat_std < 32.0
            and chroma < 13.0
            and val_std >= 12.0
        )
        # Flat panel: modest gradients, more uniform lighting → do not reject alone
        flat_lighting = grad_mag < 11.0 or val_std < 11.0

        h, w = gray.shape
        t = max(2, min(h, w) // 16)
        border = np.zeros_like(gray, dtype=bool)
        border[:t, :] = True
        border[-t:, :] = True
        border[:, :t] = True
        border[:, -t:] = True
        inner = ~border
        if not inner.any() or not border.any():
            hard_sil = False
        else:
            edge = cv2.Canny(gray, 40, 120)
            border_edge = float(np.mean(edge[border] > 0))
            inner_edge = float(np.mean(edge[inner] > 0))
            border_mean = float(np.mean(gray[border]))
            inner_mean = float(np.mean(gray[inner]))
            hard_sil = (
                border_edge >= 0.07
                and border_edge > inner_edge * 1.10
            ) or (
                abs(inner_mean - border_mean) >= 16.0
                and chroma < 12.0
                and (sat_mean < 55 or chroma < 9.0)
            )

        has_pedestal = self._has_pedestal_under(frame, box)
        has_extras = self._has_nonhuman_silhouette_extras(roi)
        aspect = h / float(max(w, 1))
        sculpture_aspect = 0.45 <= aspect <= 4.0
        if not sculpture_aspect:
            return False

        # Flat photo panel without pedestal/wings → never sculptural reject
        if flat_lighting and not has_pedestal and not has_extras and chroma >= 9.0:
            return False
        # Very mono + flat: still allow dark-cast reject below (Nike underexposed)

        sculpture_cue = has_pedestal or has_extras or (shading_3d and hard_sil)
        # Warm-lit cast paint can fake a little HSV skin; tolerate more when mono
        skin_tol = 0.075 if chroma < 9.0 else 0.050

        # Strong path: matte + little skin + real sculpture cue
        # Allow slightly higher HSV sat when RGB chroma is clearly monochrome
        sat_ok_mono = sat_mean < 55 or (sat_mean < 75 and chroma < 9.0)
        if skin_ratio < skin_tol and chroma < 13.5 and sat_ok_mono:
            if sculpture_cue:
                return True
            # Solid grey cast from side: need hard silhouette OR strong 3D shading
            # (not flat standee lighting)
            if (
                not flat_lighting
                and (hard_sil or shading_3d)
                and grey_ratio >= 0.45
                and chroma < 11.5
                and val_mean < 140
                and texture < 55.0
            ):
                return True

        # Nike / winged: extras + low chroma (no clothing / little skin)
        if (
            has_extras
            and skin_ratio < 0.10
            and (sat_mean < 55 or (sat_mean < 72 and chroma < 9.0))
            and chroma < 14.5
            and (grey_ratio >= 0.38 or dark_ratio >= 0.28)
        ):
            return True

        # Pedestal + matte body (dark sphinx on plinth: HSV sat noisy, chroma low)
        if (
            has_pedestal
            and skin_ratio < (0.085 if chroma < 9.0 else 0.055)
            and chroma < 14.5
            and matte_ok
            and (sat_mean < 55 or chroma < 9.0)
        ):
            return True

        # Low-chroma dark/grey floor sculpture without clear plinth cue
        # (animal/hybrid body or hard silhouette); prefer drop over PERSON FP
        if (
            skin_ratio < skin_tol
            and not has_clothes
            and chroma < 10.0
            and grey_ratio >= 0.45
            and val_mean < 130
            and texture < 60.0
            and not flat_lighting
            and (has_extras or hard_sil or (aspect < 1.45 and grey_ratio >= 0.50))
        ):
            return True

        # Dark monochrome cast (Nike/sphinx under museum lights): no clothes,
        # very low RGB chroma — drop even when pedestal/extras are weak
        if (
            not has_clothes
            and skin_ratio < 0.060
            and chroma < 8.5
            and (grey_ratio >= 0.42 or dark_ratio >= 0.32)
            and val_mean < 135
            and sat_mean < 62
            and texture < 62.0
            and sculpture_aspect
        ):
            if has_pedestal or has_extras or hard_sil or shading_3d:
                return True
            # Solid dark body filling most of the box (no photo chroma)
            if dark_ratio >= 0.40 and chroma < 7.5 and face_skin < 0.045:
                return True

        # 3D shading dominant on uniform material
        if (
            shading_3d
            and skin_ratio < skin_tol
            and grey_ratio >= 0.45
            and val_std >= 16.0
            and chroma < 12.5
        ):
            return True

        # Aggressive Pi/RealSense path: near-mono body, no clothes, upright
        # sculpture aspect — drop even without strong pedestal (finetune miss)
        if (
            not has_clothes
            and skin_ratio < 0.045
            and chroma < 9.5
            and grey_ratio >= 0.48
            and sat_mean < 50
            and val_mean < 145
            and texture < 55.0
            and sculpture_aspect
            and (hard_sil or shading_3d or aspect >= 1.2 or grey_ratio >= 0.58)
        ):
            return True

        return False

    def _is_statue_like_person(self, frame: np.ndarray, box: RawBox) -> bool:
        """대리석/석고/브론즈·무광 단색 동상을 COCO person 오탐으로 걸러냄."""
        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 12 or roi.shape[1] < 12:
            return True

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hch, sch, vch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        skin = self._skin_mask(roi)
        skin_ratio = float(np.mean(skin))

        sat_mean = float(np.mean(sch))
        sat_std = float(np.std(sch.astype(np.float32)))
        val_mean = float(np.mean(vch))
        val_std = float(np.std(vch.astype(np.float32)))
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        texture = float(np.std(gray))
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        chroma = self._chroma_mean(roi)
        has_clothes_color = self._has_clothing_color_variation(roi)
        has_pedestal = self._has_pedestal_under(frame, box)
        has_extras = self._has_nonhuman_silhouette_extras(roi)
        face_h = max(1, roi.shape[0] // 3)
        face_skin = float(np.mean(self._skin_mask(roi[:face_h])))

        stone_white = (sch < 45) & (vch > 110)
        stone_warm = ((hch <= 35) | (hch >= 150)) & (sch < 70) & (vch > 60) & (vch < 200)
        # Dark bronze / painted matte + medium-grey cast (sphinx)
        dark_matte = (sch < 55) & (vch < 110) & (vch > 15)
        grey_matte = (sch < 60) & (vch < 155) & (vch > 18)
        stone_ratio = float(np.mean(stone_white | stone_warm))
        dark_matte_ratio = float(np.mean(dark_matte))
        grey_matte_ratio = float(np.mean(grey_matte))

        h, w = roi.shape[:2]
        aspect = h / float(max(w, 1))
        # Tall classical OR wide/squat animal-sphinx
        sculpture_aspect = 0.55 <= aspect <= 3.8
        wide_animal = aspect < 1.40

        # Color photo poster / clothed person / standee: KEEP
        # Standees: face skin and/or clothing hues and/or print chroma — not stone.
        if has_clothes_color and skin_ratio >= 0.02 and stone_ratio < 0.60:
            return False
        if face_skin >= 0.04 and chroma > 14.0 and stone_ratio < 0.55:
            return False
        if skin_ratio >= 0.05 and chroma > 16.0 and stone_ratio < 0.55:
            return False
        if skin_ratio >= 0.06 and texture > 48.0 and chroma > 18.0:
            # Obvious photo face / colorful person — keep
            return False
        if has_clothes_color and chroma > 16.0 and stone_ratio < 0.50:
            return False

        # 피부 있어도 석재 톤이 매우 강하면 조각상으로 본다
        if stone_ratio >= 0.55 and sat_mean < 50 and skin_ratio < 0.12:
            return True
        if skin_ratio >= self.config.min_person_skin_ratio:
            # Still reject dark monochrome sculpture with pedestal/wings even if
            # a painted face gives a little "skin" signal
            if (
                skin_ratio < 0.18
                and not has_clothes_color
                and (dark_matte_ratio >= 0.40 or grey_matte_ratio >= 0.55)
                and chroma < 18.0
                and sat_mean < 55
                and (has_pedestal or has_extras or (wide_animal and grey_matte_ratio >= 0.60))
            ):
                return True
            # Sphinx face paint can push skin a bit — still drop solid grey body
            if (
                skin_ratio < 0.10
                and not has_clothes_color
                and grey_matte_ratio >= 0.58
                and chroma < 14.0
                and sat_mean < 48
                and sculpture_aspect
                and texture < 52.0
            ):
                return True
            return False

        if stone_ratio >= 0.45 and sat_mean < 55:
            return True
        if sat_mean < 38 and val_mean > 100 and skin_ratio < 0.02:
            return True
        if sat_mean < 42 and texture < 38 and skin_ratio < 0.025:
            return True

        # Near-monochrome dark/grey matte body (sphinx / Nike bronze)
        if (
            not has_clothes_color
            and (dark_matte_ratio >= 0.32 or grey_matte_ratio >= 0.45)
            and sat_mean < 55
            and chroma < 20.0
            and sat_std < 34.0
            and skin_ratio < 0.040
            and sculpture_aspect
        ):
            if has_pedestal or has_extras:
                return True
            # Smooth cast surface even without clear pedestal cue
            if val_std < 50.0 and texture < 58.0 and chroma < 15.0:
                return True
            # Strong monochrome grey cast (solid dark/grey sphinx)
            if grey_matte_ratio >= 0.52 and chroma < 14.0 and sat_mean < 48:
                return True
            # Wide crouching animal-like silhouette (sphinx)
            if wide_animal and grey_matte_ratio >= 0.48 and skin_ratio < 0.030:
                return True

        # Pedestal + low clothing chroma (classical statue on plinth)
        if (
            has_pedestal
            and not has_clothes_color
            and sat_mean < 58
            and chroma < 20.0
            and skin_ratio < 0.050
        ):
            return True

        # Non-human silhouette extras on low-sat body
        if (
            has_extras
            and not has_clothes_color
            and sat_mean < 58
            and chroma < 22.0
            and skin_ratio < 0.050
        ):
            return True

        # Solid low-chroma sculpture without clothing/skin (finetune miss)
        # Prefer dropping statue→person FP over perfect standee recall.
        if (
            not has_clothes_color
            and skin_ratio < 0.040
            and sat_mean < 55
            and chroma < 15.5
            and grey_matte_ratio >= 0.45
            and sculpture_aspect
            and val_mean < 150
            and texture < 58.0
            and lap < 320.0
        ):
            return True

        # Distant dark bust / small monochrome sculpture (no statue label from finetune)
        # COCO person often fires on these; they are dark, low-chroma, upright.
        if (
            not has_clothes_color
            and skin_ratio < 0.040
            and sat_mean < 52
            and chroma < 17.0
            and (dark_matte_ratio >= 0.32 or grey_matte_ratio >= 0.42)
            and aspect >= 1.0
            and aspect <= 3.8
        ):
            if has_pedestal or has_extras:
                return True
            # Small distant silhouette: uniform dark body, limited texture
            if (
                h < 150
                and sat_std < 28.0
                and texture < 45.0
                and val_mean < 125
                and dark_matte_ratio >= 0.42
            ):
                return True
            # Medium upright mono cast without pedestal cue (Pi side views)
            if (
                grey_matte_ratio >= 0.50
                and chroma < 12.0
                and sat_mean < 48
                and texture < 50.0
                and val_mean < 140
            ):
                return True

        return False

    def _roi(self, frame: np.ndarray, box: RawBox) -> np.ndarray:
        x1 = max(0, box.x1)
        y1 = max(0, box.y1)
        x2 = min(frame.shape[1], box.x2)
        y2 = min(frame.shape[0], box.y2)
        return frame[y1:y2, x1:x2]

    def _is_uniform_smoke_false_positive(
        self, frame: np.ndarray, box: RawBox,
    ) -> bool:
        if not self.config.reject_uniform_smoke or box.cls != 'smoke':
            return False

        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
            return True

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        texture_std = float(np.std(gray))
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        hue_mean = float(np.mean(hsv[:, :, 0]))

        if texture_std < 20.0 and sat_mean > 90.0:
            return True

        warm_hue = hue_mean < 38.0 or hue_mean > 155.0
        if warm_hue and sat_mean > 70.0 and texture_std < 35.0:
            return True

        return False

    def _is_gray_surface_smoke_false_positive(
        self, frame: np.ndarray, box: RawBox,
    ) -> bool:
        """Reject smoke on monitors, gray walls, gray clothing (low-sat flat surfaces)."""
        if not self.config.reject_uniform_smoke or box.cls != 'smoke':
            return False

        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 8 or roi.shape[1] < 8:
            return True

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        texture_std = float(np.std(gray))
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        val_mean = float(np.mean(hsv[:, :, 2]))
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        fh, fw = frame.shape[:2]
        area_ratio = (max(0, box.x2 - box.x1) * max(0, box.y2 - box.y1)) / max(fh * fw, 1)

        # Small gray regions may be real smoke — only reject large flat surfaces
        if area_ratio < 0.12:
            return False

        # High-confidence detections survive (real dense smoke plumes)
        if box.conf >= 0.58:
            return False

        # Large flat gray region — monitor screen, projector wall
        if area_ratio > 0.22 and sat_mean < 60 and texture_std < 32 and lap_var < 120:
            return True

        # Gray / off-white uniform surface (wall, shirt, desk)
        if sat_mean < 50 and texture_std < 26 and lap_var < 90:
            return True

        # Bright hazy white wall
        if sat_mean < 42 and val_mean > 135 and texture_std < 32:
            return True

        # Sharp-edged flat panel (monitor UI / bezel) — smoke edges are soft
        if sat_mean < 65 and lap_var > 350 and texture_std < 35 and box.conf < 0.45:
            return True

        return False

    def _is_cold_fire_false_positive(self, frame: np.ndarray, box: RawBox) -> bool:
        """Reject fire labels on dark smoke / grey regions (YouTube screen test case)."""
        if not self.config.reject_cold_fire or box.cls != 'fire':
            return False

        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 6 or roi.shape[1] < 6:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        warm_orange = cv2.inRange(hsv, np.array([0, 55, 70]), np.array([35, 255, 255]))
        warm_ratio = float(np.count_nonzero(warm_orange)) / warm_orange.size
        if warm_ratio >= 0.05:
            return False

        bright_flame = cv2.inRange(hsv, np.array([10, 35, 170]), np.array([40, 255, 255]))
        if float(np.count_nonzero(bright_flame)) / bright_flame.size >= 0.03:
            return False

        return True

    def _is_overexposed_fire_false_positive(self, frame: np.ndarray, box: RawBox) -> bool:
        """Reject fire on blown-out white/yellow skin or lamp glare (webcam)."""
        if not self.config.reject_cold_fire or box.cls != 'fire':
            return False

        roi = self._roi(frame, box)
        if roi.size == 0 or roi.shape[0] < 6 or roi.shape[1] < 6:
            return False

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat_mean = float(np.mean(hsv[:, :, 1]))
        val_mean = float(np.mean(hsv[:, :, 2]))
        warm_orange = cv2.inRange(hsv, np.array([0, 60, 80]), np.array([35, 255, 255]))
        warm_ratio = float(np.count_nonzero(warm_orange)) / warm_orange.size

        if warm_ratio >= 0.18:
            return False

        b, g, r = cv2.split(roi)
        white_ratio = float(
            np.count_nonzero((r > 195) & (g > 195) & (b > 195))
        ) / roi.shape[0] / roi.shape[1]

        # Overexposed face / lamp hotspot — bright, low saturation, almost no orange
        if white_ratio > 0.20 and warm_ratio < 0.10:
            return True
        if val_mean > 175 and sat_mean < 105 and warm_ratio < 0.12:
            return True
        if val_mean > 200 and warm_ratio < 0.08:
            return True

        return False

    def filter_frame_boxes(
        self,
        frame: np.ndarray,
        raw_boxes: List[RawBox],
    ) -> Tuple[List[RawBox], Set[str]]:
        kept: List[RawBox] = []
        frame_classes: Set[str] = set()

        for box in raw_boxes:
            if box.cls == 'person':
                if not self._passes_person(box, frame, frame.shape):
                    continue
                kept.append(box)
                frame_classes.add('person')
                continue
            if box.cls == 'statue':
                if not self._passes_statue(box, frame, frame.shape):
                    continue
                kept.append(box)
                frame_classes.add('statue')
                continue
            if box.cls not in ('fire', 'smoke'):
                continue
            if not self._passes_confidence(box):
                continue
            if not self._passes_size(box, frame.shape):
                continue
            # Same framed-painting reject as person (gold + dark frames)
            if self.config.reject_picture_person and self._is_inside_picture_frame(frame, box):
                continue
            if self._is_uniform_smoke_false_positive(frame, box):
                continue
            if self._is_gray_surface_smoke_false_positive(frame, box):
                continue
            if self._is_cold_fire_false_positive(frame, box):
                continue
            if self._is_overexposed_fire_false_positive(frame, box):
                continue
            kept.append(box)
            frame_classes.add(box.cls)

        return kept, frame_classes

    def confirm(self, frame_classes: Set[str]) -> Set[str]:
        """Confirm when class appears in N of the last M frames (not only consecutive)."""
        self._history.append(frame_classes)
        confirmed: Set[str] = set()
        window = max(1, len(self._history))
        for cls in ('fire', 'smoke', 'person', 'statue'):
            need = min(self.confirm_hits_for(cls), window)
            hits = sum(1 for classes in self._history if cls in classes)
            if hits >= need:
                confirmed.add(cls)
        return confirmed

    def _passes_class_flip_gate(self, cls: str) -> bool:
        """Block person↔statue flicker: need N consecutive frames after the other class.

        No linger — suppress the *new* class until confirmed; old boxes stay off.
        """
        if cls not in ('person', 'statue'):
            return True
        need = max(1, int(self.config.class_flip_confirm_frames))
        if need <= 1:
            return True
        other = 'statue' if cls == 'person' else 'person'
        hist = list(self._history)
        if len(hist) < 1:
            return True
        # Other class in recent prior frames?
        prior = hist[:-1][-4:]
        if not any(other in s for s in prior):
            return True
        # Require last `need` frames (incl. current) all contain the new class
        if len(hist) < need:
            return False
        return all(cls in s for s in hist[-need:])

    def nms_boxes(self, boxes: List[RawBox]) -> List[RawBox]:
        merged = merge_overlapping_same_class(
            boxes,
            default_iou=self.config.nms_iou,
            iou_by_class={'statue': self.config.statue_nms_iou},
        )
        return merge_fragmented_statues(
            merged,
            soft_iou=self.config.statue_fragment_soft_iou,
            union_merge=self.config.statue_fragment_union,
        )

    def conflict_anchors(self, merged: List[RawBox]) -> List[RawBox]:
        """Statue/fire boxes used to suppress overlapping person (may be weak)."""
        anchors: List[RawBox] = []
        fire_floor = self.config.person_vs_fire_anchor_conf
        statue_floor = min(
            self.config.person_vs_statue_anchor_conf,
            self.config.statue_confidence,
        )
        for box in merged:
            if box.cls == 'statue' and box.conf >= statue_floor:
                anchors.append(box)
            elif box.cls == 'fire' and box.conf >= fire_floor:
                anchors.append(box)
        return anchors

    def resolve_hybrid_person(
        self,
        kept: List[RawBox],
        anchors: List[RawBox],
        frame: np.ndarray | None = None,
    ) -> List[RawBox]:
        human_persons: List[RawBox] = []
        if (
            frame is not None
            and self.config.person_wins_over_statue_when_human
        ):
            for b in kept:
                if b.cls != 'person':
                    continue
                if not self._has_person_human_cues(frame, b):
                    continue
                # Sculptural ROI must not "win" over finetune statue
                if (
                    self.config.reject_sculptural_person
                    and self._is_sculptural_3d_person(frame, b)
                ):
                    continue
                if (
                    self.config.reject_statue_like
                    and self._is_statue_like_person(frame, b)
                ):
                    continue
                human_persons.append(b)
        return resolve_person_conflicts(
            kept,
            anchors=anchors,
            person_vs_statue_iou=self.config.person_vs_statue_iou,
            person_vs_fire_iou=self.config.person_vs_fire_iou,
            person_vs_statue_soft_iou=self.config.person_vs_statue_soft_iou,
            person_cover_thr=self.config.person_cover_thr,
            person_vs_statue_pad=self.config.person_vs_statue_pad,
            human_persons=human_persons,
        )

    def apply(
        self,
        frame: np.ndarray,
        raw_boxes: List[RawBox],
    ) -> Tuple[List[RawBox], Set[str]]:
        # Collapse multi-boxes first (esp. statue side-views / vertical fragments),
        # then ROI filters, then hybrid person-vs-statue/fire priority.
        merged = self.nms_boxes(raw_boxes)
        kept, frame_classes = self.filter_frame_boxes(frame, merged)
        anchors = self.conflict_anchors(merged)
        # Also use kept statue/fire (post-ROI) as anchors
        anchors = anchors + [b for b in kept if b.cls in ('statue', 'fire')]
        kept = self.resolve_hybrid_person(kept, anchors, frame=frame)
        frame_classes = {b.cls for b in kept}
        confirmed = self.confirm(frame_classes)
        # Flip gate after confirm (history already includes this frame)
        confirmed = {c for c in confirmed if self._passes_class_flip_gate(c)}
        # Confirm gates appearance (need N hits) but clear immediately when gone
        visible = [b for b in kept if b.cls in confirmed]
        return visible, {b.cls for b in visible}
