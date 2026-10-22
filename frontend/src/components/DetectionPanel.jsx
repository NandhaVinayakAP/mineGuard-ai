import React from "react";

function CountTile({ label, value, accent }) {
  return (
    <div className="flex-1 min-w-[86px] rounded-md border border-line bg-panel px-3 py-2.5">
      <div className="text-[10px] uppercase tracking-wide text-ink/50 font-medium">{label}</div>
      <div className={`text-xl font-bold readout ${accent || "text-navy"}`}>{value}</div>
    </div>
  );
}

function ObjectCard({ obj }) {
  return (
    <div className="border border-line rounded-md px-3 py-2.5 bg-white">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-navy">
          {obj.class} #{String(obj.id).padStart(2, "0")}
        </span>
        <span className="text-[11px] readout text-ink/60">
          {Math.round((obj.confidence || 0) * 100)}%
        </span>
      </div>
      <div className="mt-1.5 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          <div className="text-ink/40">Distance</div>
          <div className="readout font-semibold text-ink">
            {obj.distance_m != null ? `${obj.distance_m} m` : "ESTIMATING..."}
          </div>
        </div>
        <div>
          <div className="text-ink/40">Speed</div>
          <div className="readout font-semibold text-ink">
            {obj.speed_kmh != null ? `${obj.speed_kmh} km/h` : "—"}
          </div>
        </div>
        <div>
          <div className="text-ink/40">Direction</div>
          <div className="readout font-semibold text-ink">{obj.direction || "•"}</div>
        </div>
      </div>
    </div>
  );
}

export default function DetectionPanel({ objects, dumperCount, personCount, otherCount, visibility, riskLevel }) {
  return (
    <section className="panel-card">
      <div className="px-4 py-3 border-b border-line flex items-center justify-between">
        <h2 className="text-sm font-semibold text-navy tracking-wide">THREAT DETECTION</h2>
        <span className="text-[11px] text-ink/50">Detected Objects: {objects.length}</span>
      </div>

      <div className="px-4 py-3 flex gap-2 flex-wrap">
        <CountTile label="Dumpers" value={dumperCount} accent="text-navy" />
        <CountTile label="Workers" value={personCount} accent="text-teal-dark" />
        <CountTile label="Obstacles" value={otherCount} accent="text-ink" />
        <CountTile label="Visibility" value={visibility} accent="text-warn" />
      </div>

      <div className="px-4 pb-4 flex flex-col gap-2 max-h-72 overflow-y-auto">
        {objects.length === 0 ? (
          <div className="text-[12px] text-ink/40 py-3 text-center">No objects currently tracked.</div>
        ) : (
          objects.map((obj) => <ObjectCard key={obj.id} obj={obj} />)
        )}
      </div>
    </section>
  );
}
