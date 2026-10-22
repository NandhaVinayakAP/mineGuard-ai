import React from "react";

function PipelineStage({ label, active, done }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={[
          "px-3 py-1.5 rounded-md text-[11px] font-semibold tracking-wide border transition-colors",
          active
            ? "bg-teal text-white border-teal"
            : done
            ? "bg-teal/10 text-teal border-teal/30"
            : "bg-white text-ink/40 border-line",
        ].join(" ")}
      >
        {label}
      </div>
    </div>
  );
}

export default function SystemStatus({ connected, status, pipelineStage, stages, demoActive }) {
  const activeIdx = stages.indexOf(pipelineStage);
  const aiReady = status?.ai_ready;

  return (
    <header className="bg-navy text-white">
      <div className="max-w-[1500px] mx-auto px-5 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-baseline gap-3">
            <h1 className="text-lg font-bold tracking-tight">MineGuard AI</h1>
            <span className="text-[11px] uppercase tracking-widest text-teal-light font-medium">
              AI-Based Low-Visibility Safety System
            </span>
          </div>
          <div className="text-[11px] text-white/50 mt-0.5">
            NMDC Bailadila open-cast reference environment · Phase 1 prototype
          </div>
        </div>

        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2 text-sm">
            <span
              className={`status-dot ${connected ? "bg-teal-light" : "bg-crit"}`}
              style={{ boxShadow: connected ? "0 0 0 3px rgba(87,191,193,0.25)" : "none" }}
            />
            <span className="font-medium">{connected ? "SYSTEM ONLINE" : "CONNECTING..."}</span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-sm text-white/70">
            <span className={`status-dot ${aiReady ? "bg-teal-light" : "bg-warn"}`} />
            <span>{aiReady ? `AI READY (${status?.device?.toUpperCase() || "CPU"})` : "AI OFFLINE"}</span>
          </div>
          {demoActive && (
            <div className="text-[11px] font-semibold bg-warn/90 text-navy px-2.5 py-1 rounded-md">
              DEMO RUNNING
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-white/10 bg-navy-dark">
        <div className="max-w-[1500px] mx-auto px-5 py-2.5 flex items-center gap-2 overflow-x-auto">
          <span className="text-[11px] text-white/40 font-medium mr-1 shrink-0">PIPELINE</span>
          {stages.map((s, i) => (
            <React.Fragment key={s}>
              <PipelineStage label={s} active={i === activeIdx} done={i < activeIdx} />
              {i < stages.length - 1 && <span className="text-white/20 text-xs">→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>
    </header>
  );
}
