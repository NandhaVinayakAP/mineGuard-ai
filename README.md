# MineGuard AI — Phase 1: AI Perception & Collision Warning

A laptop-based computer-vision prototype for low-visibility collision
awareness on heavy-mining haul roads, inspired by the NMDC Bailadila
open-cast iron-ore mining environment.

**This is a Phase 1 software proof-of-concept.** It uses a standard webcam
or recorded video to demonstrate the pipeline

```
SENSE → DETECT → TRACK → ESTIMATE DISTANCE → PREDICT COLLISION → WARN
```

It is **not** a certified industrial safety system, and webcam-based
distance estimation is **not** equivalent to LiDAR/radar. See
[Engineering Limitations](#15-engineering-limitations) below.

---

## 1. Project Overview

MineGuard AI watches a camera feed, detects dumpers, cars, workers and
other obstacles with YOLOv8, tracks them frame-to-frame, estimates their
approximate distance and closing speed, and predicts collision risk using
a time-to-collision (TTC) model. When risk crosses a threshold it raises a
visual + audio (+ simulated haptic) warning and simulates a speed-reduction
or emergency-braking response — nothing here controls a real vehicle.

A **Bailadila Monsoon Scenario** demo mode runs a fully scripted, 11-phase
low-visibility collision sequence end-to-end without needing any camera or
video file, for quick demonstrations.

---

## 2. System Architecture

```
┌───────────┐   ┌──────────┐   ┌─────────┐   ┌──────────┐   ┌────────────┐   ┌─────────┐
│  CAMERA   │──▶│ DETECTOR │──▶│ TRACKER │──▶│ DISTANCE │──▶│ COLLISION  │──▶│ ALERTS  │
│ (camera.py)│   │(detector.│   │(tracker.│   │(distance.│   │  (collision │   │(alerts. │
│           │   │   py)    │   │   py)   │   │   py)    │   │    .py)    │   │   py)   │
└───────────┘   └──────────┘   └─────────┘   └──────────┘   └────────────┘   └─────────┘
                                                                                    │
                                                                                    ▼
                                                              FastAPI REST + WebSocket (app.py)
                                                                                    │
                                                                                    ▼
                                                          React / Vite / Tailwind dashboard
```

- **backend/** — Python, FastAPI, OpenCV, Ultralytics YOLO. Runs the full
  perception loop as a background asyncio task and streams JPEG frames +
  telemetry JSON to the frontend over a single WebSocket (`/ws`).
- **frontend/** — React + Vite + Tailwind. Renders the live feed, detection
  panel, collision alerts, telemetry, pipeline animation, and event log.
- **Sensor interface architecture** is designed so Phase 2 sensors
  (thermal, LiDAR, radar, GPS/DGPS, IMU, V2V, V2I) can be added as
  additional adapters feeding the same normalized track + fusion layer,
  without changing the collision engine (see [Future Phase 2](#17-future-phase-2-placeholders)).

---

## 3. Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- A webcam (optional — video/image modes work without one)
- No GPU required. CUDA is used automatically if available, otherwise the
  app falls back to CPU.

---

## 4. Installation — Python environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
```

If you have a CUDA-capable GPU and want GPU acceleration, install the
matching CUDA build of `torch` from https://pytorch.org **before** running
`pip install -r requirements.txt`, then re-run the install so the other
packages fill in around it.

---

## 5. Installation — Node.js / frontend

```bash
cd frontend
npm install
```

---

## 6. Downloading the YOLO model

No manual download is required. The first time `Detector` loads, Ultralytics
automatically downloads `yolov8n.pt` (~6 MB) into the working directory. To
pin a specific copy for offline use instead, download it yourself and place
it at:

```
backend/models/yolov8n.pt
```

`detector.py` prefers this local path automatically when present.

---

## 7. Starting the backend

```bash
cd backend
python app.py                                   # no camera pre-selected
python app.py --source webcam                    # start with webcam
python app.py --source video --path ../sample_videos/mine.mp4
python app.py --source image --path ../sample_videos/frame.jpg
```

The API + WebSocket server starts at `http://localhost:8000`. You can also
start/stop the camera later from the dashboard or via REST — see
[API Reference](#12-api-reference).

---

## 8. Starting the frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173`. It connects to the backend automatically at
`ws://localhost:8000/ws`.

Or use the combined scripts from the project root:

```bash
./start.sh            # Linux / macOS
start.bat              # Windows
```

---

## 9. Using the webcam

Click **Start Camera** in the dashboard, or run the backend with
`--source webcam`. If the webcam is in use by another app or permission is
denied, the dashboard shows a clear inline error instead of crashing.

## 10. Using a sample video

Click **Upload Video** in the dashboard (any short clip with vehicles or
people works — see `sample_videos/README.txt`), or start the backend with
`--source video --path <file>`. Videos loop automatically for continuous
demos.

## 11. Enabling fog mode

Use the **FOG MODE** buttons (CLEAR / MODERATE FOG / DENSE FOG) under the
live camera panel, or `POST /fog-mode {"level": "DENSE"}`. This applies a
blur + haze overlay to the feed and reports a simulated visibility range —
it is a **visualization only**, not a real fog-penetration capability.

## 12. Running the demonstration

Click **START SAFETY DEMO**. This runs the scripted 11-phase Bailadila
Monsoon Scenario (normal visibility → monsoon fog → truck detection →
closing distance → collision prediction → caution → critical warning →
simulated speed reduction → safe distance restored → system returns to
safe), ending with:

```
SENSE → ANALYZE → PREDICT → WARN → ACT
```

---

## 13. Collision Algorithm

For every pair of currently tracked objects:

1. **Distance** — each object's distance is estimated independently (see
   below); the pair's gap is the smaller of the two.
2. **Closing speed** — the relative velocity vector between the two
   tracks' centroids, projected onto the line connecting them, converted
   from px/s to m/s using the nearer object's distance-based scale.
3. **Time-to-collision** — `TTC = distance / closing_speed`. If closing
   speed is zero or negative (objects not approaching), TTC is undefined
   and the pair is reported **SAFE**.
4. **Risk classification** (thresholds configurable in `backend/config.py`):

   | Level     | Condition            | Display            |
   |-----------|----------------------|---------------------|
   | SAFE      | TTC > 8s or n/a      | Green — SAFE        |
   | CAUTION   | 4s < TTC ≤ 8s        | Orange — CAUTION    |
   | CRITICAL  | 1.5s < TTC ≤ 4s      | Red — COLLISION RISK|
   | EMERGENCY | TTC ≤ 1.5s           | Red — EMERGENCY BRAKING|

The dashboard's top-level status shows the **worst** risk across all
currently tracked pairs.

---

## 14. Distance Estimation — method and limitations

Distance uses the classic monocular pinhole-camera relationship:

```
distance_m ≈ (known_real_width_m × focal_length_px) / apparent_pixel_width
```

`known_real_width_m` is a rough per-class assumption (e.g. ~3.5 m for a
dumper) and `focal_length_px` is a configurable calibration constant in
`backend/config.py`. **This is an approximation for demonstration only**:

- It assumes the object is roughly facing the camera and of "average" size
  for its class — a haul truck at an angle, or a non-standard vehicle,
  will read incorrectly.
- It has no independent depth ground-truth, so error grows with distance
  and shrinks with a properly calibrated `CAMERA_FOCAL_LENGTH_PX`.
- Objects smaller than `DISTANCE_UNRELIABLE_MIN_PX_WIDTH` on screen show
  `ESTIMATING...` instead of a number, rather than a false-confidence value.
- Estimated speed is derived the same way and inherits the same
  uncertainty — treat all displayed numbers as indicative, not certified.

---

## 15. Engineering Limitations

1. A normal RGB camera cannot produce genuine thermal data.
2. Fog simulation is only a visualization overlay, not a sensor capability.
3. Vision-based distance estimation is approximate and uncalibrated for
   field use.
4. A webcam is not a certified industrial safety sensor.
5. Phase 1 does not directly control any real vehicle.
6. Automatic braking / speed reduction is simulated only.
7. Real deployment would require certified LiDAR/radar and a full
   functional-safety (e.g. ISO 21448 / ISO 26262-style) review.

These are also served live from `GET /status` so the frontend can surface
them directly.

---

## 16. Hardware Required for Phase 2

- Thermal/IR camera for true low-visibility and night perception
- LiDAR and/or radar for certified-grade distance and velocity
- GPS/DGPS for absolute vehicle positioning on the haul road network
- IMU for vehicle orientation and dynamics
- V2V / V2I radio link between vehicles and site infrastructure
- Edge-AI compute unit (in-vehicle, ruggedized) for onboard inference
- Physical haptic actuator and an integration point with the vehicle's
  actual braking/speed-control system (with appropriate functional-safety
  certification — Phase 1 never controls a real vehicle)

## 17. Future Phase 2 Placeholders

The backend already separates sensing from decision-making so new sensors
slot in without touching the collision engine:

```
Sensor → Sensor Adapter → Normalized Sensor Data → Sensor Fusion → AI Decision Engine
```

`camera.py` currently implements one adapter (RGB camera). Phase 2 adds
adapters for THERMAL, LiDAR, RADAR, GPS/DGPS, IMU, V2V and V2I that each
normalize their readings into the same track schema `tracker.py` already
produces (id, class, position, velocity, distance), so `collision.py`
requires no changes to consume fused, higher-confidence sensor data.

## 18. Future Improvements

- Swap the centroid tracker for `supervision`'s ByteTrack/BoT-SORT for more
  robust ID persistence through occlusion.
- Add per-camera calibration UI instead of editing `config.py` by hand.
- Multi-camera fusion for full haul-road coverage.
- Historical analytics dashboard (near-miss frequency, hotspot mapping).
- Role-based access and audit logging for a real site deployment.

---

## 19. API Reference

REST (`http://localhost:8000`):

| Method | Path                     | Description                                   |
|--------|--------------------------|------------------------------------------------|
| GET    | `/status`                | System, AI, camera, and pipeline status         |
| GET    | `/detections`            | Current detected objects                        |
| GET    | `/alerts`                | Active (non-SAFE) collision pairs + audio pattern|
| GET    | `/telemetry`             | Objects, pairs, risk level, visibility           |
| GET    | `/events?limit=100`      | Recent event log entries                         |
| POST   | `/camera/start`          | `{"source":"webcam\|video\|image","path":"..."}` |
| POST   | `/camera/upload-video`   | Multipart file upload                            |
| POST   | `/camera/upload-image`   | Multipart file upload                            |
| POST   | `/camera/stop`           | Stop and release the current camera source       |
| POST   | `/fog-mode`              | `{"level":"CLEAR\|MODERATE\|DENSE"}`             |
| POST   | `/simulation/start`      | Start the Bailadila Monsoon Scenario demo        |
| POST   | `/simulation/stop`       | Stop the demo                                    |

WebSocket:

| Path  | Description                                             |
|-------|-----------------------------------------------------------|
| `/ws` | Live telemetry stream (~10 Hz), see payload shape below   |

```json
{
  "type": "telemetry",
  "frame": "<base64 JPEG or null>",
  "objects": [ { "id": 1, "class": "DUMPER", "confidence": 0.91,
                 "distance_m": 18.4, "speed_kmh": 12.0, "direction": "→",
                 "bbox": [x1, y1, x2, y2] } ],
  "pairs": [ { "id_a": 1, "id_b": 2, "distance_m": 6.2,
               "closing_speed_mps": 4.8, "ttc_s": 2.1,
               "risk_level": "CRITICAL", "recommended_action": "REDUCE SPEED" } ],
  "risk_level": "CRITICAL",
  "visibility": "3-5 m",
  "pipeline_stage": "WARNING",
  "audio_pattern": "repeated_beep",
  "demo_active": false,
  "fps": 14.2,
  "camera_error": null,
  "ai_ready": true
}
```

---

## 20. Error Handling

The application is designed to degrade gracefully rather than crash:

- **Webcam unavailable / permission denied** — `camera.py` returns a clear
  error string; the dashboard displays it inline instead of a blank feed.
- **Missing YOLO model / load failure** — `detector.py` catches any load
  exception, sets `ready = False`, and `/status` reports `AI OFFLINE`;
  the rest of the app keeps running (camera feed still displays).
- **No detections** — panels simply show zero counts, no error state.
- **CPU-only system** — `torch.cuda.is_available()` is checked once at
  startup and inference always targets the available device.
- **Backend unavailable** — the frontend WebSocket auto-reconnects every
  1.5s and REST polling fails silently, retrying on the next interval.
- **Invalid video/image** — `camera.py` validates the file opens before
  switching modes and reports a specific error instead of silently failing.

---

## 21. Performance

- Default model: `yolov8n.pt` (nano) for CPU-friendly inference.
- `INFERENCE_IMG_SIZE = 480` and `FRAME_SKIP` are configurable in
  `config.py` to trade accuracy for frame rate on slower laptops.
- WebSocket broadcast is capped at `WEBSOCKET_BROADCAST_HZ` (default 10)
  independent of raw camera FPS, so a slow inference loop doesn't flood
  the frontend with a growing backlog.
- Target: **10–20 FPS** on a normal modern laptop; actual FPS is shown
  live in `/status` and the top bar.

---

## 22. Project Structure

```
mineguard-ai/
├── backend/
│   ├── app.py            FastAPI app, WebSocket, perception loop, demo mode
│   ├── detector.py        YOLO wrapper (CPU/GPU auto-select, graceful failure)
│   ├── tracker.py         Centroid multi-object tracker w/ velocity+direction
│   ├── distance.py        Monocular distance + speed estimation
│   ├── collision.py       Pairwise TTC + risk classification
│   ├── camera.py          Webcam/video/image source + fog overlay
│   ├── alerts.py          SQLite event log + audio pattern mapping
│   ├── config.py          All tunable thresholds/calibration in one place
│   ├── requirements.txt
│   ├── models/            (yolov8n.pt cached here if downloaded manually)
│   ├── utils/logger.py
│   └── data/alerts.db     (created automatically on first run)
├── frontend/
│   ├── package.json, vite.config.js, tailwind.config.js, index.html
│   └── src/
│       ├── App.jsx         WebSocket client, layout, audio warnings
│       ├── main.jsx
│       ├── components/     CameraFeed, DetectionPanel, AlertPanel,
│       │                   SystemStatus, Telemetry, EventLog
│       └── styles/index.css
├── sample_videos/
├── README.md
├── start.sh / start.bat
└── .gitignore
```
