import React from "react";

export default function Telemetry({ objects, pairs }) {
  const vehicles = objects.filter((o) => o.class === "DUMPER" || o.class === "CAR" || o.class === "VEHICLE");
  const relatedPair = (id) => pairs.find((p) => p.id_a === id || p.id_b === id);

  return (
    <section className="panel-card">
      <div className="px-4 py-3 border-b border-line">
        <h2 className="text-sm font-semibold text-navy tracking-wide">TELEMETRY</h2>
      </div>
      <div className="px-4 py-3 flex flex-col gap-2 max-h-60 overflow-y-auto">
        {vehicles.length === 0 ? (
          <div className="text-[12px] text-ink/40 py-2 text-center">No vehicles currently tracked.</div>
        ) : (
          vehicles.map((v) => {
            const pair = relatedPair(v.id);
            return (
              <div key={v.id} className="grid grid-cols-4 gap-2 items-center border border-line rounded-md px-3 py-2">
                <div className="text-xs font-bold text-navy">
                  {v.class} #{String(v.id).padStart(2, "0")}
                </div>
                <div className="text-[11px]">
                  <div className="text-ink/40">Distance</div>
                  <div className="readout font-semibold">{v.distance_m != null ? `${v.distance_m} m` : "—"}</div>
                </div>
                <div className="text-[11px]">
                  <div className="text-ink/40">Est. Speed</div>
                  <div className="readout font-semibold">{v.speed_kmh != null ? `${v.speed_kmh} km/h` : "—"}</div>
                </div>
                <div className="text-[11px]">
                  <div className="text-ink/40">TTC</div>
                  <div className="readout font-semibold">
                    {pair ? (pair.ttc_s != null ? `${pair.ttc_s} s` : "SAFE") : "—"}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
