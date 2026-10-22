"""
alerts.py — event logging (SQLite) and audio-warning state derivation.

Persists a simple event log so the frontend EventLog panel has a durable
history, and derives which audio warning pattern the frontend should play
for a given risk level (the actual sound is played client-side in the
browser; the backend just tells it which pattern to use).
"""

from __future__ import annotations

import sqlite3
import time
from typing import List, Dict, Any, Optional

import config
from utils.logger import get_logger

log = get_logger("alerts")

AUDIO_PATTERNS = {
    "SAFE": "none",
    "CAUTION": "single_beep",
    "CRITICAL": "repeated_beep",
    "EMERGENCY": "rapid_tone",
}


def init_db() -> None:
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts REAL NOT NULL,
            ts_label TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    log.info(f"Event database ready at {config.DB_PATH}")


def log_event(event_type: str, message: str) -> Dict[str, Any]:
    ts = time.time()
    ts_label = time.strftime("%H:%M:%S", time.localtime(ts))
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        "INSERT INTO events (ts, ts_label, event_type, message) VALUES (?, ?, ?, ?)",
        (ts, ts_label, event_type, message),
    )
    conn.commit()
    conn.close()
    return {"ts": ts, "ts_label": ts_label, "event_type": event_type, "message": message}


def recent_events(limit: int = 100) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ts, ts_label, event_type, message FROM events ORDER BY ts DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def audio_pattern_for(risk_level: str) -> str:
    return AUDIO_PATTERNS.get(risk_level, "none")
