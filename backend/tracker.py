"""
tracker.py — lightweight centroid-based multi-object tracker.

Assigns a stable ID to each detection across frames using nearest-centroid
matching, and maintains an EMA-smoothed velocity + direction estimate per
track. This is intentionally simple (no Kalman filter) so it stays fast
enough for CPU-only laptops; swapping in `supervision`'s ByteTrack is a
drop-in future upgrade (see README Phase 2 notes).
"""

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

import config
from detector import Detection
from utils.logger import get_logger

log = get_logger("tracker")


def _direction_arrow(vx: float, vy: float) -> str:
    if abs(vx) < 0.05 and abs(vy) < 0.05:
        return "•"
    angle = math.degrees(math.atan2(vy, vx))
    arrows = ["→", "↘", "↓", "↙", "←", "↖", "↑", "↗"]
    idx = int(((angle + 22.5) % 360) // 45)
    return arrows[idx]


class Track:
    def __init__(self, track_id: int, detection: Detection, timestamp: float):
        self.id = track_id
        self.cls_name = detection.cls_name
        self.cx, self.cy = detection.center
        self.width = detection.width
        self.height = detection.height
        self.confidence = detection.confidence
        self.vx = 0.0
        self.vy = 0.0
        self.speed_px_s = 0.0
        self.direction = "•"
        self.misses = 0
        self.last_seen = timestamp
        self.distance_m: Optional[float] = None
        self.history: List[tuple] = [(self.cx, self.cy, timestamp)]

    def update(self, detection: Detection, timestamp: float):
        dt = max(1e-3, timestamp - self.last_seen)
        new_cx, new_cy = detection.center

        raw_vx = (new_cx - self.cx) / dt
        raw_vy = (new_cy - self.cy) / dt

        a = config.VELOCITY_SMOOTHING
        self.vx = a * raw_vx + (1 - a) * self.vx
        self.vy = a * raw_vy + (1 - a) * self.vy
        self.speed_px_s = math.hypot(self.vx, self.vy)
        self.direction = _direction_arrow(self.vx, self.vy)

        self.cx, self.cy = new_cx, new_cy
        self.width, self.height = detection.width, detection.height
        self.confidence = detection.confidence
        self.cls_name = detection.cls_name
        self.last_seen = timestamp
        self.misses = 0
        self.history.append((self.cx, self.cy, timestamp))
        if len(self.history) > 30:
            self.history.pop(0)

    def mark_missed(self):
        self.misses += 1


class Tracker:
    def __init__(self):
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1

    def reset(self):
        self._tracks.clear()
        self._next_id = 1

    def update(self, detections: List[Detection]) -> List[Track]:
        timestamp = time.time()
        unmatched_detections = list(detections)
        matched_track_ids = set()

        # Greedy nearest-centroid matching.
        for track_id, track in list(self._tracks.items()):
            best_det = None
            best_dist = config.MAX_MATCH_DISTANCE_PX
            for det in unmatched_detections:
                dcx, dcy = det.center
                dist = math.hypot(dcx - track.cx, dcy - track.cy)
                if dist < best_dist and det.cls_name == track.cls_name:
                    best_dist = dist
                    best_det = det

            if best_det is not None:
                track.update(best_det, timestamp)
                unmatched_detections.remove(best_det)
                matched_track_ids.add(track_id)
            else:
                track.mark_missed()

        # New tracks for unmatched detections.
        for det in unmatched_detections:
            track = Track(self._next_id, det, timestamp)
            self._tracks[self._next_id] = track
            self._next_id += 1

        # Drop stale tracks.
        for track_id in list(self._tracks.keys()):
            if self._tracks[track_id].misses > config.MAX_TRACK_MISSES:
                del self._tracks[track_id]

        return list(self._tracks.values())

    @property
    def active_tracks(self) -> List[Track]:
        return list(self._tracks.values())
