"use client";

import * as React from "react";
import EtchedAccretion, { AccretionPreset } from "@/components/ui/etched-accretion";

export default function Demo() {
  const [preset, setPreset] = React.useState<AccretionPreset>("crimson");

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-[#d3121f]/30 bg-black shadow-2xl">
      <EtchedAccretion height="450px" preset={preset} interactive={true}>
        <div className="pointer-events-none flex h-full flex-col justify-between p-6 text-white sm:p-8">
          <div className="flex items-center justify-between pointer-events-auto">
            <span className="inline-flex items-center gap-2 rounded-full border border-red-500/30 bg-red-950/60 px-3 py-1 text-xs font-mono tracking-widest text-red-200 uppercase backdrop-blur-md">
              <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              Singularity Horizon · WebGL2
            </span>
            <div className="flex gap-1.5">
              {(["crimson", "ember", "glacier", "ash", "orchid"] as AccretionPreset[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPreset(p)}
                  className={`px-2.5 py-1 text-[11px] font-mono rounded capitalize transition-colors ${
                    preset === p ? "bg-white text-black font-semibold" : "bg-white/10 text-white/70 hover:bg-white/20"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          <div className="max-w-xl">
            <h1 className="text-3xl font-light leading-[1.05] tracking-tight sm:text-5xl">
              Nothing <span className="italic text-[#ff3b47]">escapes</span>
              <br />
              the horizon.
            </h1>
            <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.3em] text-white/60">
              move cursor to drift parallax · hold pointer to feed the singularity
            </p>
          </div>
        </div>
      </EtchedAccretion>
    </div>
  );
}
