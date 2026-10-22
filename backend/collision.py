"""
collision.py — pairwise collision-risk engine.

For every pair of tracked objects, estimates closing speed and time-to-
collision (TTC) from their distance + velocity estimates, then classifies
the pair into SAFE / CAUTION / CRITICAL / EMERGENCY.

TTC = distance / closing_speed
If closing speed <= 0 (objects not approaching), risk is SAFE and TTC is
reported as None ("SAFE" in the UI).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

import config
from tracker import Track
from distance import px_speed_to_kmh


@dataclass
class RiskPair:
    id_a: int
    id_b: int
    class_a: str
    class_b: str
    distance_m: Optional[float]
    closing_speed_mps: float
    ttc_s: Optional[float]
    risk_level: str
    recommended_action: str


def _closing_speed(a: Track, b: Track) -> float:
    """
    Approximate closing speed in m/s along the line connecting the two
    tracks' centroids, derived from their pixel velocities and each one's
    estimated distance (used as a rough px->metres scale per object).
    """
    dx = b.cx - a.cx
    dy = b.cy - a.cy
    dist_px = math.hypot(dx, dy)
    if dist_px < 1e-3:
        return 0.0
    nx, ny = dx / dist_px, dy / dist_px

    # Relative velocity vector (b relative to a) in px/s.
    rvx = b.vx - a.vx
    rvy = b.vy - a.vy

    # Component of relative velocity along the connecting line.
    # Positive => distance shrinking (approaching).
    closing_px_s = -(rvx * nx + rvy * ny)

    # Convert px/s to m/s using whichever object has a reliable distance.
    ref_distance = a.distance_m or b.distance_m
    if not ref_distance:
        return 0.0
    scale = ref_distance / config.CAMERA_FOCAL_LENGTH_PX
    return closing_px_s * scale


def _classify(ttc: Optional[float]) -> str:
    if ttc is None:
        return "SAFE"
    if ttc < config.TTC_EMERGENCY_THRESHOLD_S:
        return "EMERGENCY"
    if ttc < config.TTC_CAUTION_THRESHOLD_S:
        return "CRITICAL"
    if ttc <= config.TTC_SAFE_THRESHOLD_S:
        return "CAUTION"
    return "SAFE"


def _action_for(risk_level: str) -> str:
    return {
        "SAFE": "CONTINUE NORMAL OPERATION",
        "CAUTION": "MONITOR — REDUCE SPEED IF CLOSING",
        "CRITICAL": "REDUCE SPEED",
        "EMERGENCY": "EMERGENCY BRAKING",
    }[risk_level]


def evaluate_pairs(tracks: List[Track]) -> List[RiskPair]:
    pairs: List[RiskPair] = []
    n = len(tracks)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = tracks[i], tracks[j]
            if a.distance_m is None and b.distance_m is None:
                continue

            distance_m = None
            if a.distance_m is not None and b.distance_m is not None:
                distance_m = abs(round(a.distance_m - b.distance_m, 1)) or min(a.distance_m, b.distance_m)
                # For a demo, the more intuitive "gap" is the smaller of the
                # two absolute distances when both are roughly facing camera.
                distance_m = min(a.distance_m, b.distance_m)
            else:
                distance_m = a.distance_m or b.distance_m

            closing_speed = _closing_speed(a, b)

            ttc = None
            if closing_speed > 0.05 and distance_m is not None:
                ttc = round(distance_m / closing_speed, 1)

            risk_level = _classify(ttc)
            pairs.append(RiskPair(
                id_a=a.id, id_b=b.id,
                class_a=a.cls_name, class_b=b.cls_name,
                distance_m=distance_m,
                closing_speed_mps=round(max(closing_speed, 0.0), 2),
                ttc_s=ttc,
                risk_level=risk_level,
                recommended_action=_action_for(risk_level),
            ))
    return pairs


def overall_risk(pairs: List[RiskPair]) -> str:
    """Worst-case risk level across all pairs, for the top-level dashboard status."""
    order = {"SAFE": 0, "CAUTION": 1, "CRITICAL": 2, "EMERGENCY": 3}
    worst = "SAFE"
    for p in pairs:
        if order[p.risk_level] > order[worst]:
            worst = p.risk_level
    return worst
