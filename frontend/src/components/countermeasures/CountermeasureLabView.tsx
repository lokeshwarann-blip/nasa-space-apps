"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface CountermeasureLabViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
}

interface CountermeasureResponse {
    readiness_score: number;
    readiness_delta: number;
    forecast_cone: Array<{
        sol: string;
        projected_hr: number;
        forecast_low: number;
        forecast_high: number;
    }>;
    body_systems: {
        cardiac_stability_pct: number;
        bone_retention_pct: number;
        cognitive_vigilance_pct: number;
        immune_resilience_pct: number;
    };
    flight_surgeon_context: string;
}

const DEFAULT_BASELINE = {
    sleep_hours: 8.2,
    resistance_exercise_minutes: 45,
    aerobic_exercise_minutes: 30,
    hydration_liters: 2.8,
};

export default function CountermeasureLabView({
}: CountermeasureLabViewProps) {
    const [sleepHours, setSleepHours] = useState<number>(DEFAULT_BASELINE.sleep_hours);
    const [resistanceMins, setResistanceMins] = useState<number>(DEFAULT_BASELINE.resistance_exercise_minutes);
    const [aerobicMins, setAerobicMins] = useState<number>(DEFAULT_BASELINE.aerobic_exercise_minutes);
    const [hydrationLiters, setHydrationLiters] = useState<number>(DEFAULT_BASELINE.hydration_liters);

    const [readinessScore, setReadinessScore] = useState<number>(88);
    const [readinessDelta, setReadinessDelta] = useState<number>(0);
    const [forecastCone, setForecastCone] = useState<Array<{ sol: string; projected_hr: number; forecast_low: number; forecast_high: number }>>([
        { sol: "Sol 41", projected_hr: 72, forecast_low: 68, forecast_high: 76 },
        { sol: "Sol 42", projected_hr: 71, forecast_low: 66, forecast_high: 77 },
        { sol: "Sol 43", projected_hr: 70, forecast_low: 65, forecast_high: 78 },
        { sol: "Sol 44", projected_hr: 69, forecast_low: 63, forecast_high: 79 },
        { sol: "Sol 45", projected_hr: 69, forecast_low: 62, forecast_high: 80 },
        { sol: "Sol 46", projected_hr: 68, forecast_low: 61, forecast_high: 81 },
        { sol: "Sol 47", projected_hr: 68, forecast_low: 60, forecast_high: 82 },
    ]);
    const [bodyMeters, setBodyMeters] = useState({
        cardiac_stability_pct: 95,
        bone_retention_pct: 92,
        cognitive_vigilance_pct: 88,
        immune_resilience_pct: 93,
    });
    const [operationalAdvice, setOperationalAdvice] = useState<string>(
        "Nominal protocol maintained. Planned 45-min ARED resistance sessions buffer bone loss during mission extension."
    );

    const [isSimulating, setIsSimulating] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        const timeoutId = setTimeout(async () => {
            setIsSimulating(true);
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/countermeasures/forecast", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        sleep_hours: sleepHours,
                        resistance_exercise_minutes: resistanceMins,
                        aerobic_exercise_minutes: aerobicMins,
                        hydration_liters: hydrationLiters,
                    }),
                    signal: controller.signal,
                });

                if (res.ok) {
                    const data: CountermeasureResponse = await res.json();
                    setReadinessScore(data.readiness_score);
                    setReadinessDelta(data.readiness_delta);
                    setForecastCone(data.forecast_cone);
                    setBodyMeters(data.body_systems);
                    setOperationalAdvice(data.flight_surgeon_context);
                }
            } catch {
                // Client-side fallback computation
                const sleepDelta = (sleepHours - DEFAULT_BASELINE.sleep_hours) * 3;
                const resistanceDelta = ((resistanceMins - DEFAULT_BASELINE.resistance_exercise_minutes) / 10) * 2;
                const aerobicDelta = ((aerobicMins - DEFAULT_BASELINE.aerobic_exercise_minutes) / 10) * 1.5;
                const hydrationDelta = (hydrationLiters - DEFAULT_BASELINE.hydration_liters) * 2.5;
                const totalDelta = Math.round(sleepDelta + resistanceDelta + aerobicDelta + hydrationDelta);

                setReadinessDelta(totalDelta);
                setReadinessScore(Math.min(100, Math.max(45, 88 + totalDelta)));
            } finally {
                setIsSimulating(false);
            }
        }, 180);

        return () => {
            clearTimeout(timeoutId);
            controller.abort();
        };
    }, [sleepHours, resistanceMins, aerobicMins, hydrationLiters]);

    const handleReset = () => {
        setSleepHours(DEFAULT_BASELINE.sleep_hours);
        setResistanceMins(DEFAULT_BASELINE.resistance_exercise_minutes);
        setAerobicMins(DEFAULT_BASELINE.aerobic_exercise_minutes);
        setHydrationLiters(DEFAULT_BASELINE.hydration_liters);
    };

    const applyPreset = (preset: "eva" | "recovery" | "shelter") => {
        if (preset === "eva") {
            setSleepHours(8.5);
            setResistanceMins(60);
            setAerobicMins(45);
            setHydrationLiters(3.4);
        } else if (preset === "recovery") {
            setSleepHours(9.5);
            setResistanceMins(20);
            setAerobicMins(15);
            setHydrationLiters(3.0);
        } else if (preset === "shelter") {
            setSleepHours(7.5);
            setResistanceMins(30);
            setAerobicMins(20);
            setHydrationLiters(2.5);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Presets Row */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    flexWrap: "wrap",
                    background: "var(--surface, rgba(6,8,14,0.86))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    borderRadius: "2px",
                    padding: "12px 18px",
                }}
            >
                <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.14em", marginRight: "6px" }}>
                    Mission Presets:
                </span>
                <button
                    type="button"
                    onClick={() => applyPreset("eva")}
                    style={{
                        background: "var(--surface-2, rgba(255,255,255,0.04))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        color: "var(--text, #ECE8E3)",
                        borderRadius: "2px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                    }}
                >
                    Pre-EVA Conditioning
                </button>
                <button
                    type="button"
                    onClick={() => applyPreset("recovery")}
                    style={{
                        background: "var(--surface-2, rgba(255,255,255,0.04))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        color: "var(--text, #ECE8E3)",
                        borderRadius: "2px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                    }}
                >
                    Sleep Recovery
                </button>
                <button
                    type="button"
                    onClick={() => applyPreset("shelter")}
                    style={{
                        background: "var(--surface-2, rgba(255,255,255,0.04))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        color: "var(--text, #ECE8E3)",
                        borderRadius: "2px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                    }}
                >
                    Radiation Storm Shelter
                </button>

                <button
                    type="button"
                    onClick={handleReset}
                    style={{
                        marginLeft: "auto",
                        background: "transparent",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        color: "var(--muted, rgba(236,232,227,0.55))",
                        borderRadius: "2px",
                        padding: "4px 10px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        letterSpacing: "0.12em",
                        textTransform: "uppercase",
                        cursor: "pointer",
                    }}
                >
                    Reset Baseline
                </button>
            </div>

            {/* Main Stage Grid: Interactive Sliders (Left) + Live Forecast & Body Meters (Right) */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr)) 1.3fr",
                    gap: "24px",
                    alignItems: "start",
                }}
            >
                {/* Left Column: Interactive Sliders */}
                <div
                    style={{
                        background: "var(--surface, rgba(6,8,14,0.86))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        borderRadius: "2px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "24px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                            Countermeasure Inputs
                        </h3>
                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.12em" }}>
                            {isSimulating ? "Simulating..." : "Real-Time Sync"}
                        </span>
                    </div>

                    {/* Slider 1: Sleep Hours */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Sleep Window Duration
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 700, fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                {sleepHours.toFixed(1)} hrs / night
                            </span>
                        </div>
                        <input
                            type="range"
                            min="4.0"
                            max="10.0"
                            step="0.1"
                            value={sleepHours}
                            onChange={(e) => setSleepHours(parseFloat(e.target.value))}
                            style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                            <span>4.0 h</span>
                            <span>Baseline: {DEFAULT_BASELINE.sleep_hours} h</span>
                            <span>10.0 h</span>
                        </div>
                    </div>

                    {/* Slider 2: ARED Resistance Exercise */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Resistance Training (ARED)
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 700, fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                {Math.round(resistanceMins)} mins / day
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="90"
                            step="5"
                            value={resistanceMins}
                            onChange={(e) => setResistanceMins(parseFloat(e.target.value))}
                            style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                            <span>0 min</span>
                            <span>Baseline: {DEFAULT_BASELINE.resistance_exercise_minutes} min</span>
                            <span>90 min</span>
                        </div>
                    </div>

                    {/* Slider 3: Aerobic Conditioning */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Aerobic Conditioning (T2 / Cycle)
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 700, fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                {Math.round(aerobicMins)} mins / day
                            </span>
                        </div>
                        <input
                            type="range"
                            min="0"
                            max="60"
                            step="5"
                            value={aerobicMins}
                            onChange={(e) => setAerobicMins(parseFloat(e.target.value))}
                            style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                            <span>0 min</span>
                            <span>Baseline: {DEFAULT_BASELINE.aerobic_exercise_minutes} min</span>
                            <span>60 min</span>
                        </div>
                    </div>

                    {/* Slider 4: Electrolyte Hydration */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                            <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Electrolyte Hydration Intake
                            </span>
                            <span style={{ fontSize: "13px", fontWeight: 700, fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                {hydrationLiters.toFixed(1)} L / day
                            </span>
                        </div>
                        <input
                            type="range"
                            min="1.5"
                            max="4.0"
                            step="0.1"
                            value={hydrationLiters}
                            onChange={(e) => setHydrationLiters(parseFloat(e.target.value))}
                            style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                        />
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "10px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                            <span>1.5 L</span>
                            <span>Baseline: {DEFAULT_BASELINE.hydration_liters} L</span>
                            <span>4.0 L</span>
                        </div>
                    </div>

                    {/* Projected Overall Readiness Badge */}
                    <div
                        style={{
                            background: "var(--surface-2, rgba(255,255,255,0.04))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "16px 20px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginTop: "8px",
                        }}
                    >
                        <div>
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: "var(--font-mono, monospace)", display: "block" }}>
                                Simulated Readiness Score
                            </span>
                            <div style={{ display: "flex", alignItems: "baseline", gap: "6px", marginTop: "2px" }}>
                                <span style={{ fontSize: "36px", fontWeight: 800, fontFamily: "var(--font-display, sans-serif)", color: "var(--text, #ECE8E3)" }}>
                                    {readinessScore}
                                </span>
                                <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>/ 100</span>
                            </div>
                        </div>

                        <span
                            style={{
                                padding: "4px 10px",
                                borderRadius: "2px",
                                fontSize: "11px",
                                fontWeight: 700,
                                fontFamily: "var(--font-mono, monospace)",
                                letterSpacing: "0.12em",
                                background: readinessDelta >= 0 ? "transparent" : "var(--accent, #FF4D5A)",
                                color: readinessDelta >= 0 ? "var(--cool, #8FB8E8)" : "var(--accent-ink, #030307)",
                                border: `1px solid ${readinessDelta >= 0 ? "var(--cool, #8FB8E8)" : "var(--accent, #FF4D5A)"}`,
                            }}
                        >
                            {readinessDelta >= 0 ? `+${readinessDelta} PTS` : `${readinessDelta} PTS`}
                        </span>
                    </div>
                </div>

                {/* Right Column: Live Forecast Cone Chart & Body System Meters */}
                <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
                    {/* Forecast Cone Card */}
                    <div
                        style={{
                            background: "var(--surface, rgba(6,8,14,0.86))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "24px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "18px",
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                            <div>
                                <h3 style={{ margin: "0 0 2px 0", fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                                    7-Sol Resting HR Forecast Cone
                                </h3>
                                <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                    Personal normal range: 58 – 82 bpm
                                </span>
                            </div>
                            <StatusBadge level="normal" label="Normal Range: 58–82 bpm" size="sm" />
                        </div>

                        {/* Forecast Cone SVG Visualization */}
                        <div
                            style={{
                                width: "100%",
                                height: "200px",
                                background: "var(--bg, #030307)",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 16px",
                                position: "relative",
                                overflow: "hidden",
                            }}
                        >
                            <svg viewBox="0 0 500 160" style={{ width: "100%", height: "100%", overflow: "visible" }}>
                                <rect x="20" y="24" width="460" height="96" fill="var(--surface-2, rgba(255,255,255,0.04))" stroke="var(--line, rgba(233,228,223,0.16))" strokeDasharray="3 3" />
                                <text x="24" y="36" fill="var(--muted, rgba(236,232,227,0.55))" fontSize="9" fontFamily="var(--font-mono, monospace)">Upper: 82 bpm</text>
                                <text x="24" y="116" fill="var(--muted, rgba(236,232,227,0.55))" fontSize="9" fontFamily="var(--font-mono, monospace)">Lower: 58 bpm</text>

                                {forecastCone.length > 0 && (
                                    <>
                                        <polygon
                                            points={
                                                forecastCone
                                                    .map((pt, i) => `${40 + i * 70},${140 - (pt.forecast_high - 50) * 3.2}`)
                                                    .join(" ") +
                                                " " +
                                                forecastCone
                                                    .slice()
                                                    .reverse()
                                                    .map((pt, i) => `${40 + (6 - i) * 70},${140 - (pt.forecast_low - 50) * 3.2}`)
                                                    .join(" ")
                                            }
                                            fill="rgba(255, 77, 90, 0.08)"
                                            stroke="var(--line, rgba(233,228,223,0.16))"
                                            strokeWidth="1"
                                        />

                                        <polyline
                                            points={forecastCone
                                                .map((pt, i) => `${40 + i * 70},${140 - (pt.projected_hr - 50) * 3.2}`)
                                                .join(" ")}
                                            fill="none"
                                            stroke="var(--accent, #FF4D5A)"
                                            strokeWidth="2"
                                        />

                                        {forecastCone.map((pt, i) => {
                                            const cx = 40 + i * 70;
                                            const cy = 140 - (pt.projected_hr - 50) * 3.2;
                                            return (
                                                <g key={pt.sol}>
                                                    <circle cx={cx} cy={cy} r="3" fill="var(--accent, #FF4D5A)" />
                                                    <text x={cx} y="152" fill="var(--muted, rgba(236,232,227,0.55))" fontSize="9" textAnchor="middle" fontFamily="var(--font-mono, monospace)">
                                                        {pt.sol}
                                                    </text>
                                                    <text x={cx} y={cy - 6} fill="var(--text, #ECE8E3)" fontSize="9" textAnchor="middle" fontWeight="bold" fontFamily="var(--font-mono, monospace)">
                                                        {pt.projected_hr}
                                                    </text>
                                                </g>
                                            );
                                        })}
                                    </>
                                )}
                            </svg>
                        </div>
                    </div>

                    {/* Body System Resilience Meters */}
                    <div
                        style={{
                            background: "var(--surface, rgba(6,8,14,0.86))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "24px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "18px",
                        }}
                    >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                                Systems Resilience Meters
                            </h3>
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Projected Adaptation
                            </span>
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                            {/* Meter 1: Cardiac Output */}
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "6px",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)" }}>
                                    <span style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>Cardiovascular</span>
                                    <strong style={{ color: "var(--cool, #8FB8E8)" }}>{bodyMeters.cardiac_stability_pct}%</strong>
                                </div>
                                <div style={{ height: "3px", background: "var(--line, rgba(233,228,223,0.16))", overflow: "hidden" }}>
                                    <div style={{ width: `${bodyMeters.cardiac_stability_pct}%`, height: "100%", background: "var(--cool, #8FB8E8)" }} />
                                </div>
                            </div>

                            {/* Meter 2: Trabecular Bone Density */}
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "6px",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)" }}>
                                    <span style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>Bone Guard</span>
                                    <strong style={{ color: "var(--cool, #8FB8E8)" }}>{bodyMeters.bone_retention_pct}%</strong>
                                </div>
                                <div style={{ height: "3px", background: "var(--line, rgba(233,228,223,0.16))", overflow: "hidden" }}>
                                    <div style={{ width: `${bodyMeters.bone_retention_pct}%`, height: "100%", background: "var(--cool, #8FB8E8)" }} />
                                </div>
                            </div>

                            {/* Meter 3: Cognitive Vigilance (PVT) */}
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "6px",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)" }}>
                                    <span style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>Vigilance PVT</span>
                                    <strong style={{ color: "var(--warn, #FFB84D)" }}>{bodyMeters.cognitive_vigilance_pct}%</strong>
                                </div>
                                <div style={{ height: "3px", background: "var(--line, rgba(233,228,223,0.16))", overflow: "hidden" }}>
                                    <div style={{ width: `${bodyMeters.cognitive_vigilance_pct}%`, height: "100%", background: "var(--warn, #FFB84D)" }} />
                                </div>
                            </div>

                            {/* Meter 4: Immune Stress Context */}
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "6px",
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)" }}>
                                    <span style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>Immune Context</span>
                                    <strong style={{ color: "var(--cool, #8FB8E8)" }}>{bodyMeters.immune_resilience_pct}%</strong>
                                </div>
                                <div style={{ height: "3px", background: "var(--line, rgba(233,228,223,0.16))", overflow: "hidden" }}>
                                    <div style={{ width: `${bodyMeters.immune_resilience_pct}%`, height: "100%", background: "var(--cool, #8FB8E8)" }} />
                                </div>
                            </div>
                        </div>

                        {/* Operational Guidance Callout */}
                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                                fontSize: "11px",
                                color: "var(--muted, rgba(236,232,227,0.55))",
                                lineHeight: 1.6,
                                fontFamily: "var(--font-mono, monospace)",
                            }}
                        >
                            <strong style={{ color: "var(--text, #ECE8E3)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Flight Surgeon Context:</strong> {operationalAdvice}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
