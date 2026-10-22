"""
camera.py — unified camera/video/image source with fog simulation.

Supports three input modes (webcam, recorded video, single image) behind
one interface, and applies a "fog" visual overlay (CLEAR / MODERATE / DENSE)
used for the Bailadila Monsoon Scenario demo. The fog overlay is purely
cosmetic (blur + white haze blend) — it never claims to simulate real
atmospheric scattering physics.

Handles the required error cases gracefully: missing webcam, permission
issues, invalid video/image paths, etc. Every failure returns None from
read_frame() plus a human-readable self.last_error, instead of raising.
"""

from __future__ import annotations

import os
import threading
from typing import Optional

import cv2
import numpy as np

import config
from utils.logger import get_logger

log = get_logger("camera")


class CameraSource:
    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._still_image: Optional[np.ndarray] = None
        self.mode: str = "none"          # "webcam" | "video" | "image" | "none"
        self.fog_level: str = "CLEAR"
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- open
    def open_webcam(self, index: int = 0) -> bool:
        self.close()
        with self._lock:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                self.last_error = (
                    "Webcam unavailable. Check that a camera is connected, not in use "
                    "by another application, and that camera permission is granted."
                )
                log.error(self.last_error)
                return False
            self._cap = cap
            self.mode = "webcam"
            self.last_error = None
            log.info("Webcam opened.")
            return True

    def open_video(self, path: str) -> bool:
        self.close()
        if not os.path.exists(path):
            self.last_error = f"Video file not found: {path}"
            log.error(self.last_error)
            return False
        with self._lock:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                self.last_error = f"Invalid or unreadable video file: {path}"
                log.error(self.last_error)
                return False
            self._cap = cap
            self.mode = "video"
            self.last_error = None
            log.info(f"Video opened: {path}")
            return True

    def open_image(self, path: str) -> bool:
        self.close()
        if not os.path.exists(path):
            self.last_error = f"Image file not found: {path}"
            log.error(self.last_error)
            return False
        img = cv2.imread(path)
        if img is None:
            self.last_error = f"Invalid or unreadable image file: {path}"
            log.error(self.last_error)
            return False
        with self._lock:
            self._still_image = img
            self.mode = "image"
            self.last_error = None
            log.info(f"Image opened: {path}")
            return True

    def open_bytes_as_image(self, data: bytes) -> bool:
        self.close()
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            self.last_error = "Uploaded image could not be decoded."
            log.error(self.last_error)
            return False
        with self._lock:
            self._still_image = img
            self.mode = "image"
            self.last_error = None
            return True

    def open_bytes_as_video(self, data: bytes, tmp_path: str) -> bool:
        with open(tmp_path, "wb") as f:
            f.write(data)
        return self.open_video(tmp_path)

    # --------------------------------------------------------------- read
    def read_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self.mode == "image" and self._still_image is not None:
                frame = self._still_image.copy()
            elif self.mode in ("webcam", "video") and self._cap is not None:
                ok, frame = self._cap.read()
                if not ok:
                    if self.mode == "video":
                        # Loop recorded videos for a continuous demo feed.
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = self._cap.read()
                        if not ok:
                            self.last_error = "Video ended and could not be looped."
                            return None
                    else:
                        self.last_error = "Lost connection to webcam feed."
                        log.error(self.last_error)
                        return None
            else:
                return None

        return self._apply_fog(frame)

    # ---------------------------------------------------------------- fog
    def set_fog_level(self, level: str) -> bool:
        if level not in config.FOG_LEVELS:
            return False
        self.fog_level = level
        log.info(f"Fog level set to {level}.")
        return True

    def _apply_fog(self, frame: np.ndarray) -> np.ndarray:
        cfg = config.FOG_LEVELS.get(self.fog_level, config.FOG_LEVELS["CLEAR"])
        if cfg["alpha"] <= 0:
            return frame

        blurred = frame
        if cfg["blur"] > 0:
            k = cfg["blur"] | 1  # ensure odd kernel size
            blurred = cv2.GaussianBlur(frame, (k, k), 0)

        white = np.full_like(blurred, 235)
        foggy = cv2.addWeighted(blurred, 1 - cfg["alpha"], white, cfg["alpha"], 0)
        return foggy

    # --------------------------------------------------------------- close
    def close(self):
        with self._lock:
            if self._cap is not None:
                self._cap.release()
            self._cap = None
            self._still_image = None
            self.mode = "none"

    @property
    def is_open(self) -> bool:
        return self.mode != "none"
