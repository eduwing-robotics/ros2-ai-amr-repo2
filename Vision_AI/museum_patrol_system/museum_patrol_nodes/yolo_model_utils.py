"""Companion model helpers for museum fire/smoke (+ finetune person/statue) YOLO."""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple, TYPE_CHECKING

from museum_patrol_nodes.detection_filters import RawBox

if TYPE_CHECKING:
    from ultralytics import YOLO

# COCO class index for person in yolov8n.pt (fallback only)
PERSON_CLASS_IDS_COCO = [0]

_PERSON_ALIASES = frozenset({'person', 'people', 'human', '사람'})
# Classes the companion may contribute when main is fire/smoke-only
COMPANION_TARGET_NAMES = frozenset({'fire', 'person', 'statue'})
# Hybrid: finetune main (fire/statue) + COCO companion for person only
PERSON_ONLY_TARGET_NAMES = frozenset({'person'})


def model_has_person(names: Dict[int, str]) -> bool:
    for name in names.values():
        if name.lower().strip() in _PERSON_ALIASES:
            return True
    return False


def model_has_class(names: Dict[int, str], class_name: str) -> bool:
    needle = class_name.lower().strip()
    return any(name.lower().strip() == needle for name in names.values())


def person_class_ids(names: Dict[int, str]) -> List[int]:
    """Class indices whose name is person (works for COCO id0 and finetune id1)."""
    ids = [
        idx
        for idx, name in names.items()
        if name.lower().strip() in _PERSON_ALIASES
    ]
    return ids if ids else list(PERSON_CLASS_IDS_COCO)


def target_class_ids(
    names: Dict[int, str],
    wanted: Iterable[str] = COMPANION_TARGET_NAMES,
) -> List[int]:
    """Class indices for museum target names present in the model."""
    wanted_set = {w.lower().strip() for w in wanted}
    return [
        idx
        for idx, name in names.items()
        if name.lower().strip() in wanted_set
        or (name.lower().strip() in _PERSON_ALIASES and 'person' in wanted_set)
    ]


def extract_target_boxes(
    results,
    model_names: Dict[int, str],
    scale: float = 1.0,
    wanted: FrozenSet[str] = COMPANION_TARGET_NAMES,
) -> List[RawBox]:
    """Keep fire/person/statue (etc.) boxes from a companion or main model."""
    boxes: List[RawBox] = []
    for result in results:
        if result.boxes is None:
            continue
        for box in result.boxes:
            class_id = int(box.cls[0])
            name = model_names.get(class_id, str(class_id)).lower().strip()
            if name in _PERSON_ALIASES:
                name = 'person'
            if name not in wanted:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            if scale != 1.0:
                x1 /= scale
                y1 /= scale
                x2 /= scale
                y2 /= scale
            boxes.append(
                RawBox(
                    cls=name,
                    conf=float(box.conf[0]),
                    x1=int(x1),
                    y1=int(y1),
                    x2=int(x2),
                    y2=int(y2),
                )
            )
    return boxes


def extract_person_boxes(
    results,
    model_names: Dict[int, str],
    scale: float = 1.0,
) -> List[RawBox]:
    return extract_target_boxes(
        results, model_names, scale=scale, wanted=frozenset({'person'})
    )


def load_companion_person_model(
    person_model_path: str,
) -> Optional[Tuple['YOLO', Dict[int, str]]]:
    path = person_model_path.strip()
    if not path:
        return None
    from ultralytics import YOLO

    model = YOLO(path)
    names = {idx: name.lower() for idx, name in model.names.items()}
    return model, names
