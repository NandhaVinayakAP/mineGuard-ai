import React, { useEffect, useRef, useState, useCallback } from "react";
import CameraFeed from "./components/CameraFeed.jsx";
import DetectionPanel from "./components/DetectionPanel.jsx";
import AlertPanel from "./components/AlertPanel.jsx";
import SystemStatus from "./components/SystemStatus.jsx";
import Telemetry from "./components/Telemetry.jsx";
import EventLog from "./components/EventLog.jsx";

const API = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

const PIPELINE_STAGES = [
  "CAMERA",
  "YOLO AI",
  "TRACKING",
  "DISTANCE ESTIMATION",
  "COLLISION PREDICTION",
  "WARNING",
];

// --- tiny Web Audio beeper, no external audio files required -------------
function useAudioWarnings(pattern, enabled) {
  const ctxRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!enabled) return;
    if (!ctxRef.current) {
      ctxRef.current = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = ctxRef.current;

    const beep = (freq = 880, duration = 0.12) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.type = "square";
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration + 0.02);
    };

    clearInterval(timerRef.current);

    if (pattern === "single_beep") {
      beep(700, 0.15);
    } else if (pattern === "repeated_beep") {
      beep(760, 0.15);
      timerRef.current = setInterval(() => beep(760, 0.15), 700);
    } else if (pattern === "rapid_tone") {
      beep(980, 0.09);
      timerRef.current = setInterval(() => beep(980, 0.09), 220);
    }

    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pattern, enabled]);
}

export default function App() {
  const [connected, setConnected] = useState(false);
  const [telemetry, setTelemetry] = useState({
    frame: null,
    objects: [],
    pairs: [],
    risk_level: "SAFE",
    visibility: "50+ m",
    pipeline_stage: "IDLE",
    audio_pattern: "none",
    demo_active: false,
    fps: 0,
    camera_error: null,
    ai_ready: false,
  });
  const [status, setStatus] = useState(null);
  const [events, setEvents] = useState([]);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [fogLevel, setFogLevel] = useState("CLEAR");
  const wsRef = useRef(null);

  useAudioWarnings(telemetry.audio_pattern, audioEnabled);

  // --- websocket lifecycle ------------------------------------------------
  useEffect(() => {
    let retryTimer;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        retryTimer = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === "telemetry") {
            setTelemetry((prev) => ({ ...prev, ...data }));
          }
        } catch {
          // ignore malformed frame
        }
      };
    }

    connect();
    return () => {
      clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, []);

  // --- polling for status + events (cheap, low frequency) ----------------
  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/status`);
      setStatus(await res.json());
    } catch {
      setStatus((s) => s || { system: "UNREACHABLE" });
    }
  }, []);

  const refreshEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API}/events?limit=50`);
      const data = await res.json();
      setEvents(data.events || []);
    } catch {
      // backend not reachable yet — leave existing log as-is
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    refreshEvents();
    const t1 = setInterval(refreshStatus, 2000);
    const t2 = setInterval(refreshEvents, 2000);
    return () => {
      clearInterval(t1);
      clearInterval(t2);
    };
  }, [refreshStatus, refreshEvents]);

  // --- actions -------------------------------------------------------------
  const startWebcam = async () => {
    setAudioEnabled(true);
    await fetch(`${API}/camera/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "webcam" }),
    });
    refreshStatus();
  };

  const stopCamera = async () => {
    await fetch(`${API}/camera/stop`, { method: "POST" });
    refreshStatus();
  };

  const uploadVideo = async (file) => {
    setAudioEnabled(true);
    const form = new FormData();
    form.append("file", file);
    await fetch(`${API}/camera/upload-video`, { method: "POST", body: form });
    refreshStatus();
  };

  const uploadImage = async (file) => {
    setAudioEnabled(true);
    const form = new FormData();
    form.append("file", file);
    await fetch(`${API}/camera/upload-image`, { method: "POST", body: form });
    refreshStatus();
  };

  const changeFog = async (level) => {
    setFogLevel(level);
    await fetch(`${API}/fog-mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level }),
    });
  };

  const startDemo = async () => {
    setAudioEnabled(true);
    await fetch(`${API}/simulation/start`, { method: "POST" });
  };

  const stopDemo = async () => {
    await fetch(`${API}/simulation/stop`, { method: "POST" });
  };

  const dumperCount = telemetry.objects.filter((o) => o.class === "DUMPER").length;
  const personCount = telemetry.objects.filter((o) => o.class === "PERSON").length;
  const otherCount = telemetry.objects.length - dumperCount - personCount;

  return (
    <div className="min-h-screen bg-panel">
      <SystemStatus
        connected={connected}
        status={status}
        pipelineStage={telemetry.pipeline_stage}
        stages={PIPELINE_STAGES}
        demoActive={telemetry.demo_active}
      />

      <main className="max-w-[1500px] mx-auto px-5 py-5 grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-5">
        {/* LEFT: live camera + collision status + safety response */}
        <div className="flex flex-col gap-5 min-w-0">
          <CameraFeed
            frame={telemetry.frame}
            cameraOpen={status?.camera_open}
            cameraError={telemetry.camera_error || status?.camera_error}
            fogLevel={fogLevel}
            onFogChange={changeFog}
            onStartWebcam={startWebcam}
            onStopCamera={stopCamera}
            onUploadVideo={uploadVideo}
            onUploadImage={uploadImage}
            onStartDemo={startDemo}
            onStopDemo={stopDemo}
            demoActive={telemetry.demo_active}
            visibility={telemetry.visibility}
            riskLevel={telemetry.risk_level}
          />
          <AlertPanel pairs={telemetry.pairs} riskLevel={telemetry.risk_level} />
        </div>

        {/* RIGHT: threat detection, telemetry, event log */}
        <div className="flex flex-col gap-5 min-w-0">
          <DetectionPanel
            objects={telemetry.objects}
            dumperCount={dumperCount}
            personCount={personCount}
            otherCount={otherCount}
            visibility={telemetry.visibility}
            riskLevel={telemetry.risk_level}
          />
          <Telemetry objects={telemetry.objects} pairs={telemetry.pairs} />
          <EventLog events={events} />
        </div>
      </main>

      <footer className="max-w-[1500px] mx-auto px-5 pb-6 text-xs text-ink/50 leading-relaxed">
        Phase 1 prototype — vision-estimated distance and speed for demonstration purposes only.
        Not a certified industrial safety sensor. See README for full engineering limitations.
      </footer>
    </div>
  );
}
