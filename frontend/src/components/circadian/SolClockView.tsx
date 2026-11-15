"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface SolClockViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
}

export default function SolClockView({
}: SolClockViewProps) {
    const [habitatHour, setHabitatHour] = useState<number>(14.42);
    const [bodyClockHour, setBodyClockHour] = useState<number>(16.15);
    const [plannedSleepStart, setPlannedSleepStart] = useState<number>(23.0);
    const [plannedSleepDuration, setPlannedSleepDuration] = useState<number>(8.0);
    const [blueLightExposureMins, setBlueLightExposureMins] = useState<number>(45);

    const phaseOffset = Math.round((bodyClockHour - habitatHour) * 10) / 10;
    const dailyRealignmentRate = Math.min(1.4, 0.5 + (blueLightExposureMins / 60) * 0.8);
    const realignmentSols = Math.max(1, Math.ceil(Math.abs(phaseOffset) / dailyRealignmentRate));

    useEffect(() => {
        let isMounted = true;
        const fetchCircadian = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/circadian/dial");
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setHabitatHour(data.habitat_hour);
                        setBodyClockHour(data.body_clock_hour);
                    }
                }
            } catch {
                // Offline tolerance
            }
        };
        fetchCircadian();
        return () => {
            isMounted = false;
        };
    }, []);

    const hourToAngle = (h: number) => (h % 24) * 15;
    const polarToCartesian = (cx: number, cy: number, r: number, angleDeg: number) => {
        const rad = ((angleDeg - 90) * Math.PI) / 180.0;
        return {
            x: cx + r * Math.cos(rad),
            y: cy + r * Math.sin(rad),
        };
    };

    const describeArc = (cx: number, cy: number, r: number, startHour: number, endHour: number) => {
        const startAngle = hourToAngle(startHour);
        let endAngle = hourToAngle(endHour);
        if (endAngle <= startAngle) endAngle += 360;

        const start = polarToCartesian(cx, cy, r, startAngle);
        const end = polarToCartesian(cx, cy, r, endAngle);
        const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

        return ["M", start.x, start.y, "A", r, r, 0, largeArcFlag, 1, end.x, end.y].join(" ");
    };

    const formatHour = (h: number) => {
        const normalized = (h + 24) % 24;
        const hrs = Math.floor(normalized);
        const mins = Math.floor((normalized - hrs) * 60);
        return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Main Stage Grid: Circadian Dial (Left) + Interactive Sleep Window Preview & Photic Plan (Right) */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr)) 1.2fr",
                    gap: "24px",
                    alignItems: "start",
                }}
            >
                {/* Left: Overlaid Circadian Dial */}
                <div
                    style={{
                        background: "var(--surface, rgba(6,8,14,0.86))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        borderRadius: "2px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "20px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
                        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                            24-Hour Circadian Dials
                        </h3>
                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.12em" }}>
                            Outer = Habitat · Inner = Body
                        </span>
                    </div>

                    {/* SVG Dual Dial */}
                    <div style={{ position: "relative", width: "280px", height: "280px" }}>
                        <svg width="280" height="280" viewBox="0 0 300 300">
                            {/* Outer Habitat Dial Track */}
                            <circle cx="150" cy="150" r="130" fill="none" stroke="var(--line, rgba(233,228,223,0.16))" strokeWidth="12" />

                            {/* Inner Body Clock Dial Track */}
                            <circle cx="150" cy="150" r="95" fill="none" stroke="var(--surface-2, rgba(255,255,255,0.04))" strokeWidth="12" />

                            {/* Sleep Window Arc on Outer Track */}
                            <path
                                d={describeArc(150, 150, 130, plannedSleepStart, (plannedSleepStart + plannedSleepDuration) % 24)}
                                fill="none"
                                stroke="var(--cool, #8FB8E8)"
                                strokeWidth="12"
                                opacity="0.6"
                            />

                            {/* Morning Light Pulse Arc */}
                            <path
                                d={describeArc(150, 150, 130, (plannedSleepStart + plannedSleepDuration) % 24, ((plannedSleepStart + plannedSleepDuration) % 24 + blueLightExposureMins / 60) % 24)}
                                fill="none"
                                stroke="var(--accent, #FF4D5A)"
                                strokeWidth="12"
                                opacity="0.85"
                            />

                            {/* 24-Hour Markers */}
                            {[0, 3, 6, 9, 12, 15, 18, 21].map((hr) => {
                                const pt = polarToCartesian(150, 150, 142, hourToAngle(hr));
                                return (
                                    <text
                                        key={hr}
                                        x={pt.x}
                                        y={pt.y + 4}
                                        fill="var(--muted, rgba(236,232,227,0.55))"
                                        fontSize="9"
                                        fontFamily="var(--font-mono, monospace)"
                                        textAnchor="middle"
                                    >
                                        {String(hr).padStart(2, "0")}
                                    </text>
                                );
                            })}

                            {/* Outer Dial Hand (Habitat Time) */}
                            {(() => {
                                const pt = polarToCartesian(150, 150, 120, hourToAngle(habitatHour));
                                return (
                                    <line
                                        x1="150"
                                        y1="150"
                                        x2={pt.x}
                                        y2={pt.y}
                                        stroke="var(--accent, #FF4D5A)"
                                        strokeWidth="2.5"
                                        strokeLinecap="square"
                                    />
                                );
                            })()}

                            {/* Inner Dial Hand (Body Clock Time) */}
                            {(() => {
                                const pt = polarToCartesian(150, 150, 85, hourToAngle(bodyClockHour));
                                return (
                                    <line
                                        x1="150"
                                        y1="150"
                                        x2={pt.x}
                                        y2={pt.y}
                                        stroke="var(--cool, #8FB8E8)"
                                        strokeWidth="2"
                                        strokeDasharray="4 3"
                                        strokeLinecap="square"
                                    />
                                );
                            })()}

                            {/* Center Hub */}
                            <circle cx="150" cy="150" r="5" fill="var(--text, #ECE8E3)" />
                        </svg>
                    </div>

                    {/* Dual Readout Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", width: "100%" }}>
                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                            }}
                        >
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: "var(--font-mono, monospace)" }}>
                                Habitat Clock
                            </span>
                            <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--accent, #FF4D5A)", fontFamily: "var(--font-display, sans-serif)", marginTop: "2px" }}>
                                {formatHour(habitatHour)}
                            </div>
                        </div>

                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                            }}
                        >
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", textTransform: "uppercase", letterSpacing: "0.1em", fontFamily: "var(--font-mono, monospace)" }}>
                                Internal DLMO
                            </span>
                            <div style={{ fontSize: "20px", fontWeight: 800, color: "var(--cool, #8FB8E8)", fontFamily: "var(--font-display, sans-serif)", marginTop: "2px" }}>
                                {formatHour(bodyClockHour)}
                            </div>
                        </div>
                    </div>

                    {/* Realignment Metric */}
                    <div
                        style={{
                            width: "100%",
                            background: "var(--surface-2, rgba(255,255,255,0.04))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "12px 16px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                        }}
                    >
                        <div>
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Estimated Realignment
                            </span>
                            <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-mono, monospace)", marginTop: "2px" }}>
                                {realignmentSols} Sols at current protocol
                            </div>
                        </div>
                        <StatusBadge level="watch" label={`Delay: +${phaseOffset}h`} size="sm" />
                    </div>
                </div>

                {/* Right: Controls & Protocol */}
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
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                            Photic Shift Controls
                        </h3>

                        {/* Sliders */}
                        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                            <div>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)", color: "var(--muted, rgba(236,232,227,0.55))", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                    <span>Target Sleep Onset</span>
                                    <span style={{ color: "var(--text, #ECE8E3)" }}>{formatHour(plannedSleepStart)}</span>
                                </div>
                                <input
                                    type="range"
                                    min="18"
                                    max="26"
                                    step="0.25"
                                    value={plannedSleepStart}
                                    onChange={(e) => setPlannedSleepStart(parseFloat(e.target.value))}
                                    style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                                />
                            </div>

                            <div>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)", color: "var(--muted, rgba(236,232,227,0.55))", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                    <span>Planned Sleep Duration</span>
                                    <span style={{ color: "var(--text, #ECE8E3)" }}>{plannedSleepDuration}h</span>
                                </div>
                                <input
                                    type="range"
                                    min="6"
                                    max="10"
                                    step="0.5"
                                    value={plannedSleepDuration}
                                    onChange={(e) => setPlannedSleepDuration(parseFloat(e.target.value))}
                                    style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                                />
                            </div>

                            <div>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontFamily: "var(--font-mono, monospace)", color: "var(--muted, rgba(236,232,227,0.55))", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                    <span>Morning 480nm Photic Pulse</span>
                                    <span style={{ color: "var(--text, #ECE8E3)" }}>{blueLightExposureMins} min</span>
                                </div>
                                <input
                                    type="range"
                                    min="0"
                                    max="90"
                                    step="15"
                                    value={blueLightExposureMins}
                                    onChange={(e) => setBlueLightExposureMins(parseInt(e.target.value))}
                                    style={{ width: "100%", accentColor: "var(--accent, #FF4D5A)" }}
                                />
                            </div>
                        </div>

                        {/* Photic Protocol Recommendation */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginTop: "8px" }}>
                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "4px",
                                }}
                            >
                                <span style={{ fontSize: "11px", color: "var(--accent, #FF4D5A)", fontWeight: 600, fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                    Morning Pulse
                                </span>
                                <strong style={{ fontSize: "13px", fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                    07:00 – 09:30
                                </strong>
                                <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                    480nm LED (450 lux)
                                </span>
                            </div>

                            <div
                                style={{
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    borderRadius: "2px",
                                    padding: "12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "4px",
                                }}
                            >
                                <span style={{ fontSize: "11px", color: "var(--cool, #8FB8E8)", fontWeight: 600, fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                    Dim Window
                                </span>
                                <strong style={{ fontSize: "13px", fontFamily: "var(--font-mono, monospace)", color: "var(--text, #ECE8E3)" }}>
                                    21:30 Onset
                                </strong>
                                <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                    Red-shifted &lt;30 lux
                                </span>
                            </div>
                        </div>

                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                fontSize: "11px",
                                color: "var(--muted, rgba(236,232,227,0.55))",
                                lineHeight: 1.6,
                                fontFamily: "var(--font-mono, monospace)",
                            }}
                        >
                            <strong style={{ color: "var(--text, #ECE8E3)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Operational Context:</strong> Maintaining consistent 07:00 wake with 45-min blue light pulse phase-advances central pacemaker by 0.8h daily. Check with flight surgeon prior to rapid sleep shifts.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
