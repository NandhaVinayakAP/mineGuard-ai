"""
app.py — MineGuard AI Phase 1 backend entrypoint.

FastAPI application that ties together:
    CAMERA -> DETECTOR -> TRACKER -> DISTANCE -> COLLISION -> ALERTS
and exposes it over REST + WebSocket to the React frontend.

Run:
    python app.py --source webcam
    python app.py --source sample_videos/mine.mp4
    python app.py                      (starts with no camera open; use the
                                         frontend or POST /camera/start)
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import tempfile
import time
from typing import List, Optional, Set

import cv2
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import alerts
from camera import CameraSource
from detector import Detector
from tracker import Tracker
from distance import update_track_distance, px_speed_to_kmh
from collision import evaluate_pairs, overall_risk
from utils.logger import get_logger

log = get_logger("app")

# --------------------------------------------------------------------------
# Global system state (single-camera prototype; fine for Phase 1 scope)
# --------------------------------------------------------------------------
app = FastAPI(title="MineGuard AI — Phase 1", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

camera = CameraSource()
detector = Detector()
tracker = Tracker()

state = {
    "pipeline_stage": "IDLE",     # CAMERA / YOLO AI / TRACKING / DISTANCE / COLLISION / WARNING
    "risk_level": "SAFE",
    "visibility": config.FOG_LEVELS["CLEAR"]["visibility"],
    "objects": [],
    "pairs": [],
    "audio_pattern": "none",
    "demo_active": False,
    "demo_phase": 0,
    "camera_error": None,
    "fps": 0.0,
}

_ws_clients: Set[WebSocket] = set()
_broadcast_lock = asyncio.Lock()

DEMO_PHASES = [
    {"name": "NORMAL VISIBILITY", "risk": "SAFE", "fog": "CLEAR", "visibility": "50+ m"},
    {"name": "MONSOON FOG", "risk": "SAFE", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "TRUCK DETECTED", "risk": "SAFE", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "SECOND TRUCK DETECTED", "risk": "SAFE", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "DISTANCE DECREASING", "risk": "CAUTION", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "AI PREDICTS COLLISION", "risk": "CAUTION", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "ORANGE WARNING — CAUTION", "risk": "CAUTION", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "RED WARNING — COLLISION RISK", "risk": "CRITICAL", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "SPEED REDUCTION", "risk": "CRITICAL", "fog": "DENSE", "visibility": "3-5 m"},
    {"name": "SAFE DISTANCE RESTORED", "risk": "CAUTION", "fog": "MODERATE", "visibility": "10-20 m"},
    {"name": "SYSTEM RETURNS TO SAFE", "risk": "SAFE", "fog": "CLEAR", "visibility": "50+ m"},
]


# --------------------------------------------------------------------------
# REST models
# --------------------------------------------------------------------------
class FogModeRequest(BaseModel):
    level: str  # CLEAR | MODERATE | DENSE


class CameraStartRequest(BaseModel):
    source: str            # "webcam" | "video" | "image"
    path: Optional[str] = None
    webcam_index: Optional[int] = 0


# --------------------------------------------------------------------------
# REST endpoints
# --------------------------------------------------------------------------
@app.get("/status")
def get_status():
    return {
        "system": "ONLINE",
        "ai_ready": detector.ready,
        "device": detector.device,
        "camera_open": camera.is_open,
        "camera_mode": camera.mode,
        "camera_error": camera.last_error,
        "pipeline_stage": state["pipeline_stage"],
        "risk_level": state["risk_level"],
        "visibility": state["visibility"],
        "demo_active": state["demo_active"],
        "fps": round(state["fps"], 1),
        "limitations": config.ENGINEERING_LIMITATIONS,
    }


@app.get("/detections")
def get_detections():
    return {"objects": state["objects"]}


@app.get("/telemetry")
def get_telemetry():
    return {
        "objects": state["objects"],
        "pairs": state["pairs"],
        "risk_level": state["risk_level"],
        "visibility": state["visibility"],
        "pipeline_stage": state["pipeline_stage"],
    }


@app.get("/alerts")
def get_alerts():
    return {"pairs": [p for p in state["pairs"] if p["risk_level"] != "SAFE"],
            "audio_pattern": state["audio_pattern"]}


@app.get("/events")
def get_events(limit: int = 100):
    return {"events": alerts.recent_events(limit)}


@app.post("/camera/start")
def camera_start(req: CameraStartRequest):
    tracker.reset()
    if req.source == "webcam":
        ok = camera.open_webcam(req.webcam_index or 0)
    elif req.source == "video":
        path = req.path or ""
        if not os.path.isabs(path):
            path = os.path.join(config.BASE_DIR, "..", path)
        ok = camera.open_video(path)
    elif req.source == "image":
        path = req.path or ""
        if not os.path.isabs(path):
            path = os.path.join(config.BASE_DIR, "..", path)
        ok = camera.open_image(path)
    else:
        return {"ok": False, "error": f"Unknown source '{req.source}'"}

    if ok:
        alerts.log_event("SYSTEM", f"Camera source started: {req.source}")
    return {"ok": ok, "error": camera.last_error}


@app.post("/camera/upload-video")
async def camera_upload_video(file: UploadFile = File(...)):
    tracker.reset()
    data = await file.read()
    tmp_path = os.path.join(tempfile.gettempdir(), f"mineguard_{int(time.time())}_{file.filename}")
    ok = camera.open_bytes_as_video(data, tmp_path)
    if ok:
        alerts.log_event("SYSTEM", f"Uploaded video started: {file.filename}")
    return {"ok": ok, "error": camera.last_error}


@app.post("/camera/upload-image")
async def camera_upload_image(file: UploadFile = File(...)):
    tracker.reset()
    data = await file.read()
    ok = camera.open_bytes_as_image(data)
    if ok:
        alerts.log_event("SYSTEM", f"Uploaded image opened: {file.filename}")
    return {"ok": ok, "error": camera.last_error}


@app.post("/camera/stop")
def camera_stop():
    camera.close()
    tracker.reset()
    state["objects"] = []
    state["pairs"] = []
    state["risk_level"] = "SAFE"
    state["pipeline_stage"] = "IDLE"
    alerts.log_event("SYSTEM", "Camera stopped")
    return {"ok": True}


@app.post("/fog-mode")
def fog_mode(req: FogModeRequest):
    ok = camera.set_fog_level(req.level.upper())
    if ok:
        state["visibility"] = config.FOG_LEVELS[req.level.upper()]["visibility"]
        alerts.log_event("SYSTEM", f"Fog mode set to {req.level.upper()}")
    return {"ok": ok, "visibility": state["visibility"]}


@app.post("/simulation/start")
def simulation_start():
    state["demo_active"] = True
    state["demo_phase"] = 0
    alerts.log_event("SYSTEM", "BAILADILA MONSOON SCENARIO demo started")
    return {"ok": True}


@app.post("/simulation/stop")
def simulation_stop():
    state["demo_active"] = False
    state["demo_phase"] = 0
    camera.set_fog_level("CLEAR")
    state["visibility"] = config.FOG_LEVELS["CLEAR"]["visibility"]
    alerts.log_event("SYSTEM", "Demo stopped")
    return {"ok": True}


# --------------------------------------------------------------------------
# WebSocket — live telemetry + frame stream
# --------------------------------------------------------------------------
@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    log.info(f"WebSocket client connected ({len(_ws_clients)} total)")
    try:
        while True:
            # We don't require inbound messages; keep the connection alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        _ws_clients.discard(websocket)
        log.info(f"WebSocket client disconnected ({len(_ws_clients)} total)")


async def _broadcast(payload: dict):
    if not _ws_clients:
        return
    message = json.dumps(payload)
    dead = []
    for client in list(_ws_clients):
        try:
            await client.send_text(message)
        except Exception:  # noqa: BLE001
            dead.append(client)
    for d in dead:
        _ws_clients.discard(d)


# --------------------------------------------------------------------------
# Demo (scripted) mode
# --------------------------------------------------------------------------
def _run_demo_step():
    phase = DEMO_PHASES[state["demo_phase"]]
    camera.set_fog_level(phase["fog"])
    state["visibility"] = phase["visibility"]
    state["risk_level"] = phase["risk"]
    state["pipeline_stage"] = "WARNING" if phase["risk"] != "SAFE" else "COLLISION PREDICTION"
    state["audio_pattern"] = alerts.audio_pattern_for(phase["risk"])

    alerts.log_event("DEMO", phase["name"])

    # Synthesize a plausible pair for the telemetry/warning panels so the
    # frontend has something concrete to display even with no live camera.
    if phase["risk"] != "SAFE":
        synthetic_pair = {
            "id_a": 1, "id_b": 2,
            "class_a": "DUMPER", "class_b": "DUMPER",
            "distance_m": {"CAUTION": 14.0, "CRITICAL": 6.2, "EMERGENCY": 2.5}.get(phase["risk"], 20.0),
            "closing_speed_mps": {"CAUTION": 1.8, "CRITICAL": 4.8, "EMERGENCY": 6.0}.get(phase["risk"], 0.0),
            "ttc_s": {"CAUTION": 6.5, "CRITICAL": 2.1, "EMERGENCY": 1.1}.get(phase["risk"], None),
            "risk_level": phase["risk"],
            "recommended_action": {
                "CAUTION": "MONITOR — REDUCE SPEED IF CLOSING",
                "CRITICAL": "REDUCE SPEED",
                "EMERGENCY": "EMERGENCY BRAKING",
            }.get(phase["risk"], "CONTINUE NORMAL OPERATION"),
        }
        state["pairs"] = [synthetic_pair]
        state["objects"] = [
            {"id": 1, "class": "DUMPER", "confidence": 0.91, "distance_m": synthetic_pair["distance_m"] + 3,
             "speed_kmh": 12.0, "direction": "→", "bbox": [80, 120, 280, 300]},
            {"id": 2, "class": "DUMPER", "confidence": 0.88, "distance_m": synthetic_pair["distance_m"],
             "speed_kmh": 8.0, "direction": "←", "bbox": [400, 140, 600, 320]},
        ]
    else:
        state["pairs"] = []
        if "TRUCK DETECTED" in phase["name"] or phase["name"] == "SAFE DISTANCE RESTORED" \
                or phase["name"] == "SYSTEM RETURNS TO SAFE":
            state["objects"] = [
                {"id": 1, "class": "DUMPER", "confidence": 0.91, "distance_m": 22.0,
                 "speed_kmh": 12.0, "direction": "→", "bbox": [80, 120, 280, 300]},
            ] if "SECOND" not in phase["name"] else [
                {"id": 1, "class": "DUMPER", "confidence": 0.91, "distance_m": 22.0,
                 "speed_kmh": 12.0, "direction": "→", "bbox": [80, 120, 280, 300]},
                {"id": 2, "class": "DUMPER", "confidence": 0.88, "distance_m": 30.0,
                 "speed_kmh": 8.0, "direction": "←", "bbox": [400, 140, 600, 320]},
            ]
        else:
            state["objects"] = []

    state["demo_phase"] += 1
    if state["demo_phase"] >= len(DEMO_PHASES):
        state["demo_active"] = False
        state["demo_phase"] = 0
        alerts.log_event("DEMO", "BAILADILA MONSOON SCENARIO complete — SENSE / ANALYZE / PREDICT / WARN / ACT")


# --------------------------------------------------------------------------
# Main perception loop (runs continuously in the background)
# --------------------------------------------------------------------------
async def perception_loop():
    frame_count = 0
    last_fps_time = time.time()
    fps_frames = 0
    demo_step_interval = 2.0
    last_demo_step = 0.0

    while True:
        loop_start = time.time()

        if state["demo_active"]:
            if loop_start - last_demo_step >= demo_step_interval:
                _run_demo_step()
                last_demo_step = loop_start
            frame = None
            if camera.is_open:
                frame = camera.read_frame()
            state["pipeline_stage"] = "WARNING" if state["risk_level"] != "SAFE" else "COLLISION PREDICTION"

        elif camera.is_open:
            state["pipeline_stage"] = "CAMERA"
            frame = camera.read_frame()
            state["camera_error"] = camera.last_error

            if frame is not None:
                frame_count += 1
                if frame_count % config.FRAME_SKIP == 0:
                    state["pipeline_stage"] = "YOLO AI"
                    detections = detector.detect(frame)

                    state["pipeline_stage"] = "TRACKING"
                    tracks = tracker.update(detections)

                    state["pipeline_stage"] = "DISTANCE ESTIMATION"
                    for t in tracks:
                        update_track_distance(t)

                    state["pipeline_stage"] = "COLLISION PREDICTION"
                    pairs = evaluate_pairs(tracks)
                    risk = overall_risk(pairs)

                    prev_risk = state["risk_level"]
                    state["risk_level"] = risk
                    state["pairs"] = [p.__dict__ for p in pairs]
                    state["objects"] = [
                        {
                            "id": t.id, "class": t.cls_name,
                            "confidence": round(t.confidence, 2),
                            "distance_m": t.distance_m,
                            "speed_kmh": px_speed_to_kmh(t.speed_px_s, t.distance_m),
                            "direction": t.direction,
                            "bbox": [round(t.cx - t.width / 2, 1), round(t.cy - t.height / 2, 1),
                                     round(t.cx + t.width / 2, 1), round(t.cy + t.height / 2, 1)],
                        }
                        for t in tracks
                    ]

                    if risk != "SAFE":
                        state["pipeline_stage"] = "WARNING"
                    state["audio_pattern"] = alerts.audio_pattern_for(risk)

                    if risk in ("CRITICAL", "EMERGENCY") and prev_risk != risk:
                        worst = max(pairs, key=lambda p: -( p.ttc_s if p.ttc_s is not None else 999))
                        alerts.log_event(
                            risk,
                            f"{worst.class_a} #{worst.id_a} <-> {worst.class_b} #{worst.id_b} "
                            f"| dist {worst.distance_m}m | TTC {worst.ttc_s}s"
                        )
                    elif risk == "CAUTION" and prev_risk == "SAFE":
                        alerts.log_event("CAUTION", "Closing distance detected between tracked objects")
                    elif risk == "SAFE" and prev_risk != "SAFE":
                        alerts.log_event("SAFE", "Risk cleared — safe distance restored")
        else:
            frame = None
            state["pipeline_stage"] = "IDLE"

        # Encode frame (if any) for the live video panel.
        frame_b64 = None
        if frame is not None:
            _draw_overlays(frame, state["objects"])
            ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                frame_b64 = base64.b64encode(buf).decode("ascii")

        fps_frames += 1
        if loop_start - last_fps_time >= 1.0:
            state["fps"] = fps_frames / (loop_start - last_fps_time)
            fps_frames = 0
            last_fps_time = loop_start

        payload = {
            "type": "telemetry",
            "frame": frame_b64,
            "objects": state["objects"],
            "pairs": state["pairs"],
            "risk_level": state["risk_level"],
            "visibility": state["visibility"],
            "pipeline_stage": state["pipeline_stage"],
            "audio_pattern": state["audio_pattern"],
            "demo_active": state["demo_active"],
            "fps": round(state["fps"], 1),
            "camera_error": state["camera_error"],
            "ai_ready": detector.ready,
        }
        await _broadcast(payload)

        elapsed = time.time() - loop_start
        target_dt = 1.0 / config.WEBSOCKET_BROADCAST_HZ
        await asyncio.sleep(max(0.0, target_dt - elapsed))


def _draw_overlays(frame, objects: List[dict]):
    for obj in objects:
        try:
            x1, y1, x2, y2 = [int(v) for v in obj["bbox"]]
        except Exception:  # noqa: BLE001
            continue
        color = (36, 156, 0)  # teal-ish green (BGR)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f'{obj["class"]} #{obj["id"]} {int(obj.get("confidence", 0) * 100)}%'
        cv2.putText(frame, label, (x1, max(15, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if obj.get("distance_m") is not None:
            cv2.putText(frame, f'{obj["distance_m"]} m', (x1, y2 + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


@app.on_event("startup")
async def on_startup():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    alerts.init_db()
    alerts.log_event("SYSTEM", "MineGuard AI backend started")
    asyncio.create_task(perception_loop())


# --------------------------------------------------------------------------
# CLI entrypoint
# --------------------------------------------------------------------------
def _parse_args():
    parser = argparse.ArgumentParser(description="MineGuard AI Phase 1 backend")
    parser.add_argument("--source", choices=["webcam", "video", "image", "none"], default="none")
    parser.add_argument("--path", type=str, default=None, help="Path for --source video/image")
    parser.add_argument("--host", type=str, default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    return parser.parse_args()


def _apply_startup_source(args):
    if args.source == "webcam":
        camera.open_webcam(0)
    elif args.source == "video" and args.path:
        camera.open_video(args.path)
    elif args.source == "image" and args.path:
        camera.open_image(args.path)


if __name__ == "__main__":
    args = _parse_args()
    _apply_startup_source(args)
    uvicorn.run(app, host=args.host, port=args.port)
