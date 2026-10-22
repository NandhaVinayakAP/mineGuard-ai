import React, { useRef } from "react";

const FOG_OPTIONS = ["CLEAR", "MODERATE", "DENSE"];

const RISK_STYLES = {
  SAFE: { bg: "bg-teal", text: "SAFE" },
  CAUTION: { bg: "bg-warn", text: "CAUTION" },
  CRITICAL: { bg: "bg-crit", text: "COLLISION RISK" },
  EMERGENCY: { bg: "bg-crit", text: "EMERGENCY" },
};

export default function CameraFeed({
  frame,
  cameraOpen,
  cameraError,
  fogLevel,
  onFogChange,
  onStartWebcam,
  onStopCamera,
  onUploadVideo,
  onUploadImage,
  onStartDemo,
  onStopDemo,
  demoActive,
  visibility,
  riskLevel,
}) {
  const videoInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const risk = RISK_STYLES[riskLevel] || RISK_STYLES.SAFE;

  return (
    <section className="panel-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-line">
        <h2 className="text-sm font-semibold text-navy tracking-wide">LIVE CAMERA</h2>
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-white text-[11px] font-bold ${risk.bg}`}>
          {riskLevel === "CRITICAL" || riskLevel === "EMERGENCY" ? "⚠ " : ""}
          {risk.text}
        </div>
      </div>

      <div className="relative bg-navy-dark aspect-video flex items-center justify-center">
        {frame ? (
          <img
            src={`data:image/jpeg;base64,${frame}`}
            alt="Live camera feed"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="text-white/40 text-sm text-center px-6">
            {cameraError ? (
              <span className="text-warn-light">{cameraError}</span>
            ) : (
              "No active feed — start the webcam, upload a video, or upload an image below."
            )}
          </div>
        )}

        <div className="absolute top-3 left-3 bg-black/50 text-white text-[11px] px-2.5 py-1 rounded-md">
          VISIBILITY: <span className="readout">{visibility}</span>
        </div>
      </div>

      <div className="px-4 py-3 text-[11px] text-ink/50 border-b border-line bg-panel/60">
        Distance is vision-estimated for prototype demonstration — not a certified sensor measurement.
      </div>

      <div className="px-4 py-3 flex flex-wrap items-center gap-2">
        {!cameraOpen ? (
          <button onClick={onStartWebcam} className="btn-primary">
            Start Camera
          </button>
        ) : (
          <button onClick={onStopCamera} className="btn-secondary">
            Stop Camera
          </button>
        )}

        <button onClick={() => videoInputRef.current?.click()} className="btn-secondary">
          Upload Video
        </button>
        <input
          ref={videoInputRef}
          type="file"
          accept="video/*"
          hidden
          onChange={(e) => e.target.files[0] && onUploadVideo(e.target.files[0])}
        />

        <button onClick={() => imageInputRef.current?.click()} className="btn-secondary">
          Upload Image
        </button>
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => e.target.files[0] && onUploadImage(e.target.files[0])}
        />

        <div className="ml-auto flex items-center gap-2">
          {!demoActive ? (
            <button onClick={onStartDemo} className="btn-demo">
              START SAFETY DEMO
            </button>
          ) : (
            <button onClick={onStopDemo} className="btn-secondary">
              Stop Demo
            </button>
          )}
        </div>
      </div>

      <div className="px-4 pb-4 flex items-center gap-2">
        <span className="text-[11px] font-medium text-ink/50 mr-1">FOG MODE</span>
        {FOG_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => onFogChange(opt)}
            className={[
              "px-2.5 py-1 rounded-md text-[11px] font-semibold border transition-colors",
              fogLevel === opt
                ? "bg-navy text-white border-navy"
                : "bg-white text-ink/60 border-line hover:border-navy/30",
            ].join(" ")}
          >
            {opt === "CLEAR" ? "CLEAR" : opt === "MODERATE" ? "MODERATE FOG" : "DENSE FOG"}
          </button>
        ))}
      </div>

      <style>{`
        .btn-primary {
          background: #0F8B8D; color: white; font-size: 12px; font-weight: 600;
          padding: 8px 14px; border-radius: 6px;
        }
        .btn-primary:hover { background: #0A6567; }
        .btn-secondary {
          background: white; color: #1E2530; font-size: 12px; font-weight: 600;
          padding: 8px 14px; border-radius: 6px; border: 1px solid #E2E5EA;
        }
        .btn-secondary:hover { border-color: #0B2545; }
        .btn-demo {
          background: #E8792D; color: white; font-size: 12px; font-weight: 700;
          padding: 8px 16px; border-radius: 6px; letter-spacing: 0.02em;
        }
        .btn-demo:hover { background: #cf691f; }
      `}</style>
    </section>
  );
}
