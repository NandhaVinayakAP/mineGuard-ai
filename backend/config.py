"""
config.py — MineGuard AI Phase 1
Central configuration for detection, calibration, thresholds, and paths.
All values here are safe to tune from the frontend Settings panel (future work)
or by editing this file directly.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "alerts.db")

# --------------------------------------------------------------------------
# YOLO / DETECTION
# --------------------------------------------------------------------------
# Small model chosen so the prototype runs acceptably on CPU-only laptops.
# Ultralytics will auto-download this the first time it is used, unless a
# local copy already exists in backend/models/.
YOLO_MODEL_NAME = "yolov8n.pt"
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, YOLO_MODEL_NAME)

# Classes we care about, mapped to COCO class names. "truck" is treated as
# the closest available proxy for a mining dumper — see README limitations.
RELEVANT_CLASSES = {
    "person": "PERSON",
    "car": "CAR",
    "truck": "DUMPER",       # dumper approximation
    "bus": "DUMPER",         # large vehicle -> treated as dumper-class too
    "motorcycle": "VEHICLE",
}

CONFIDENCE_THRESHOLD = 0.35
INFERENCE_IMG_SIZE = 480          # smaller = faster on CPU
FRAME_SKIP = 1                    # process every Nth frame (1 = every frame)

# --------------------------------------------------------------------------
# DISTANCE ESTIMATION (approximate, monocular, bounding-box based)
# --------------------------------------------------------------------------
# distance ≈ (KNOWN_WIDTH_M * FOCAL_LENGTH_PX) / apparent_pixel_width
# This is a rough pinhole-camera approximation, not a calibrated measurement.
CAMERA_FOCAL_LENGTH_PX = 800.0
CAMERA_MOUNT_HEIGHT_M = 3.0

# Approximate real-world widths (metres) used for the distance formula.
KNOWN_OBJECT_WIDTHS_M = {
    "PERSON": 0.5,
    "CAR": 1.8,
    "DUMPER": 3.5,
    "VEHICLE": 0.8,
}

MIN_SAFE_DISTANCE_M = 10.0
DISTANCE_UNRELIABLE_MIN_PX_WIDTH = 12  # below this, distance is too noisy

# --------------------------------------------------------------------------
# COLLISION RISK (time-to-collision, seconds)
# --------------------------------------------------------------------------
TTC_SAFE_THRESHOLD_S = 8.0
TTC_CAUTION_THRESHOLD_S = 4.0
TTC_EMERGENCY_THRESHOLD_S = 1.5

# --------------------------------------------------------------------------
# TRACKING
# --------------------------------------------------------------------------
MAX_TRACK_MISSES = 15          # frames a track can go undetected before drop
MAX_MATCH_DISTANCE_PX = 120    # centroid distance gate for track association
VELOCITY_SMOOTHING = 0.6       # EMA smoothing factor for velocity estimate

# --------------------------------------------------------------------------
# FOG SIMULATION
# --------------------------------------------------------------------------
FOG_LEVELS = {
    "CLEAR": {"alpha": 0.0, "blur": 0, "visibility": "50+ m"},
    "MODERATE": {"alpha": 0.35, "blur": 5, "visibility": "10-20 m"},
    "DENSE": {"alpha": 0.65, "blur": 11, "visibility": "3-5 m"},
}

# --------------------------------------------------------------------------
# SERVER
# --------------------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8000
WEBSOCKET_BROADCAST_HZ = 10   # target telemetry pushes per second

# --------------------------------------------------------------------------
# LIMITATIONS (surfaced verbatim to the frontend so it can display them)
# --------------------------------------------------------------------------
ENGINEERING_LIMITATIONS = [
    "A normal RGB camera cannot produce genuine thermal data.",
    "Fog simulation is only a visualization overlay, not a sensor capability.",
    "Vision-based distance estimation is approximate and uncalibrated for field use.",
    "A webcam is not a certified industrial safety sensor.",
    "Phase 1 does not directly control any real vehicle.",
    "Automatic braking / speed reduction is simulated only.",
    "Real deployment would require certified LiDAR/radar and functional-safety review.",
]
