# scripts/yolo_training

Local tools for collecting RealSense frames, labeling YOLO bounding boxes, and
training custom object-detection weights on the Mac.

Rules:

1. Keep robot-side work read-only unless a launch command is explicitly needed.
2. Store generated datasets under `datasets/` and training output under `runs/`;
   both are ignored by git.
3. Write YOLO labels in Ultralytics format and keep `data.yaml` reproducible.
4. Prefer the existing `test/.venv` Python environment unless the caller
   overrides `PYTHON` or runs from another activated environment.
5. Do not commit `.pt` weights. Record the best weight path in evidence docs.
