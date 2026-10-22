"""
detector.py — YOLO-based object detection for MineGuard AI.

Wraps Ultralytics YOLO so the rest of the app never has to think about
torch/device selection, missing weights, or malformed frames. Always
degrades gracefully: if the model can't be loaded, detect() returns an
empty list and the caller can still run (dashboard shows "AI OFFLINE").
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

import numpy as np

import config
from utils.logger import get_logger

log = get_logger("detector")


class Detection:
    __slots__ = ("cls_name", "confidence", "x1", "y1", "x2", "y2")

    def __init__(self, cls_name: str, confidence: float, x1: float, y1: float, x2: float, y2: float):
        self.cls_name = cls_name
        self.confidence = confidence
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2

    @property
    def width(self) -> float:
        return max(1.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(1.0, self.y2 - self.y1)

    @property
    def center(self) -> tuple:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def to_dict(self) -> Dict[str, Any]:
        cx, cy = self.center
        return {
            "class": self.cls_name,
            "confidence": round(self.confidence, 3),
            "bbox": [round(self.x1, 1), round(self.y1, 1), round(self.x2, 1), round(self.y2, 1)],
            "center": [round(cx, 1), round(cy, 1)],
            "width": round(self.width, 1),
            "height": round(self.height, 1),
        }


class Detector:
    """Loads a YOLO model once, exposes detect(frame) -> List[Detection]."""

    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.ready = False
        self._load()

    def _load(self):
        try:
            import torch
            from ultralytics import YOLO

            self.device = "cuda" if torch.cuda.is_available() else "cpu"

            weights = config.YOLO_MODEL_PATH if os.path.exists(config.YOLO_MODEL_PATH) else config.YOLO_MODEL_NAME
            log.info(f"Loading YOLO model '{weights}' on device '{self.device}'...")
            self.model = YOLO(weights)
            self.ready = True
            log.info("YOLO model ready.")
        except Exception as exc:  # noqa: BLE001 — we want to survive ANY load failure
            self.model = None
            self.ready = False
            log.error(f"Could not load YOLO model ({exc}). Detection will be disabled "
                      f"until a model is available. See README for setup instructions.")

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if not self.ready or frame is None:
            return []

        try:
            results = self.model.predict(
                source=frame,
                imgsz=config.INFERENCE_IMG_SIZE,
                conf=config.CONFIDENCE_THRESHOLD,
                device=self.device,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            log.error(f"Inference error: {exc}")
            return []

        detections: List[Detection] = []
        if not results:
            return detections

        result = results[0]
        names = result.names
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            if cls_name not in config.RELEVANT_CLASSES:
                continue
            mapped_name = config.RELEVANT_CLASSES[cls_name]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            detections.append(Detection(mapped_name, conf, x1, y1, x2, y2))

        return detections
