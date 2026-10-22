import React from "react";

const TYPE_COLOR = {
  SAFE: "text-teal-dark",
  CAUTION: "text-warn",
  CRITICAL: "text-crit",
  EMERGENCY: "text-crit",
  SYSTEM: "text-ink/50",
  DEMO: "text-navy",
};

export default function EventLog({ events }) {
  return (
    <section className="panel-card flex-1 min-h-[220px] flex flex-col">
      <div className="px-4 py-3 border-b border-line">
        <h2 className="text-sm font-semibold text-navy tracking-wide">EVENT LOG</h2>
      </div>
      <div className="px-4 py-3 flex flex-col gap-2 overflow-y-auto max-h-96">
        {events.length === 0 ? (
          <div className="text-[12px] text-ink/40 py-2 text-center">No events recorded yet.</div>
        ) : (
          events.map((e, i) => (
            <div key={i} className="text-[12px] leading-snug">
              <span className="readout text-ink/40 mr-2">{e.ts_label}</span>
              <span className={`font-semibold ${TYPE_COLOR[e.event_type] || "text-ink"}`}>
                {e.message}
              </span>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
