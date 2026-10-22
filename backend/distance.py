"""
distance.py — approximate monocular distance estimation.

IMPORTANT: this is a software approximation for demonstration purposes only.
It uses the classic pinhole-camera relationship:

    distance_m ≈ (known_real_width_m * focal_length_px) / apparent_width_px

Because a webcam has no depth sensor, this value is only as good as the
calibration constants in config.py, and gets noisier the smaller (farther)
the object is on screen. Never present this as a certified safety
measurement — see README "Distance Estimation Limitations".
"""

from __future__ import annotations

from typing import Optional

import config
from tracker import Track


def estimate_distance_m(track: Track) -> Optional[float]:
    """Returns an estimated distance in metres, or None if unreliable."""
    if track.width < config.DISTANCE_UNRELIABLE_MIN_PX_WIDTH:
        return None

    known_width = config.KNOWN_OBJECT_WIDTHS_M.get(track.cls_name)
    if not known_width:
        return None

    distance = (known_width * config.CAMERA_FOCAL_LENGTH_PX) / track.width
    # Clamp to a sane display range for a prototype demo.
    distance = max(0.5, min(distance, 250.0))
    return round(distance, 1)


def update_track_distance(track: Track) -> None:
    track.distance_m = estimate_distance_m(track)


def px_speed_to_kmh(speed_px_s: float, distance_m: Optional[float]) -> Optional[float]:
    """
    Very rough conversion of on-screen pixel speed to an approximate real
    world speed, scaled by estimated distance (farther objects move fewer
    pixels/sec for the same real speed). This is a demonstration heuristic,
    not a calibrated speed measurement.
    """
    if distance_m is None or distance_m <= 0:
        return None
    # Empirical scale factor tuned so a typical on-screen dumper crossing
    # the frame over ~2s at 15m reads out in a plausible km/h range.
    scale = distance_m / config.CAMERA_FOCAL_LENGTH_PX
    speed_m_s = speed_px_s * scale
    speed_kmh = speed_m_s * 3.6
    return round(min(speed_kmh, 80.0), 1)
