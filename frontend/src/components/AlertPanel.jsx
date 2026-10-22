import React from "react";

function worstPair(pairs) {
  const order = { SAFE: 0, CAUTION: 1, CRITICAL: 2, EMERGENCY: 3 };
  return pairs.reduce((worst, p) => (order[p.risk_level] > order[(worst || {}).risk_level || "SAFE"] ? p : worst), null);
}

function SafetyResponse({ riskLevel }) {
  if (riskLevel !== "CRITICAL" && riskLevel !== "EMERGENCY") return null;

  const isEmergency = riskLevel === "EMERGENCY";
  return (
    <div className="mt-3 border border-line rounded-md bg-panel px-3 py-3">
      <div className="text-[11px] font-semibold text-ink/50 mb-2">SIMULATED SAFETY RESPONSE</div>
      <div className="flex items-center justify-between text-xs">
        <div className="text-center flex-1">
          <div className="text-ink/40">CURRENT SPEED</div>
          <div className="readout font-bold text-lg text-ink">12 km/h</div>
        </div>
        <div className="text-ink/30 px-2">↓</div>
        <div className="text-center flex-1">
          <div className="text-ink/40">AI RESPONSE</div>
          <div className="readout font-bold text-sm text-crit">
            {isEmergency ? "EMERGENCY BRAKING" : "REDUCE SPEED"}
          </div>
        </div>
        <div className="text-ink/30 px-2">↓</div>
        <div className="text-center flex-1">
          <div className="text-ink/40">SIMULATED SPEED</div>
          <div className="readout font-bold text-lg text-teal-dark">{isEmergency ? "0 km/h" : "6 km/h"}</div>
        </div>
      </div>
      {isEmergency && (
        <div className="mt-2 text-center text-[11px] font-semibold text-teal-dark">VEHICLE STOPPED SAFELY</div>
      )}
    </div>
  );
}

export default function AlertPanel({ pairs, riskLevel }) {
  const safe = riskLevel === "SAFE";
  const pair = worstPair(pairs);

  return (
    <section
      className={[
        "panel-card px-5 py-4 transition-colors",
        riskLevel === "CRITICAL" || riskLevel === "EMERGENCY" ? "border-crit/50 bg-crit/[0.03]" : "",
        riskLevel === "CAUTION" ? "border-warn/50 bg-warn/[0.03]" : "",
      ].join(" ")}
    >
      {safe || !pair ? (
        <div className="flex items-center gap-3 text-teal-dark">
          <span className="status-dot bg-teal" />
          <span className="text-sm font-semibold">All tracked objects at safe distance — no collision risk.</span>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <span className="text-xl">⚠</span>
            <h2 className="text-base font-extrabold tracking-tight text-crit">
              {riskLevel === "EMERGENCY" ? "EMERGENCY — COLLISION IMMINENT" : "COLLISION WARNING"}
            </h2>
          </div>
          <div className="mt-1 text-sm font-semibold text-navy">
            {pair.class_a} #{pair.id_a} ↔ {pair.class_b} #{pair.id_b}
          </div>

          <div className="mt-3 grid grid-cols-3 gap-3">
            <div>
              <div className="text-[11px] text-ink/50">Distance</div>
              <div className="readout text-lg font-bold">{pair.distance_m ?? "—"} m</div>
            </div>
            <div>
              <div className="text-[11px] text-ink/50">Closing Speed</div>
              <div className="readout text-lg font-bold">{pair.closing_speed_mps ?? "—"} m/s</div>
            </div>
            <div>
              <div className="text-[11px] text-ink/50">TTC</div>
              <div className="readout text-lg font-bold">{pair.ttc_s != null ? `${pair.ttc_s} s` : "SAFE"}</div>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-2 text-xs font-semibold text-white bg-navy inline-flex px-3 py-1.5 rounded-md w-fit">
            ACTION: {pair.recommended_action}
          </div>

          <div className="mt-4 pt-3 border-t border-line grid sm:grid-cols-3 gap-3 text-[11px]">
            <div>
              <div className="text-ink/40 mb-1">VISUAL</div>
              <div className="font-semibold text-crit">⚠ COLLISION WARNING</div>
            </div>
            <div>
              <div className="text-ink/40 mb-1">AUDIO</div>
              <div className="font-semibold text-navy">AUDIO WARNING ACTIVE</div>
            </div>
            <div>
              <div className="text-ink/40 mb-1">HAPTIC</div>
              <div className="font-semibold text-ink/60">HAPTIC ALERT — SIMULATION</div>
            </div>
          </div>

          <SafetyResponse riskLevel={riskLevel} />
        </>
      )}
    </section>
  );
}
