"use client";

import React, { useState } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

export interface EventMarker {
    id: string;
    type: "sleep_loss" | "exercise" | "eva" | "solar_event";
    label: string;
    icon: string;
    time: string;
    detail: string;
    impact: string;
}

export interface HistoryPoint {
    time: string;
    value: number;
    quality?: "good" | "degraded" | "calibrating";
}

export interface ForecastPoint {
    time: string;
    forecastLow: number;
    forecastHigh: number;
    projected: number;
}

export interface ZoneData {
    id: string;
    name: string;
    icon: string;
    level: StatusLevel;
    value: string;
    unit: string;
    baselineLow: number;
    baselineHigh: number;
    currentNumeric: number;
    evidence: "established" | "emerging" | "illustrative";
    sensorQuality: "good" | "sensor issue";
    oneLiner: string;
    shortParagraph: string;
    deepContext: string;
    history: HistoryPoint[];
    history7d?: HistoryPoint[];
    history14d?: HistoryPoint[];
    forecast?: ForecastPoint[];
    events?: EventMarker[];
}

interface ZoneZoomPanelProps {
    zone: ZoneData | null;
    onClose: () => void;
}

export default function ZoneZoomPanel({ zone, onClose }: ZoneZoomPanelProps) {
    const [depthLevel, setDepthLevel] = useState<1 | 2 | 3>(1);
    const [range, setRange] = useState<"24h" | "7d" | "14d">("24h");
    const [selectedPoint, setSelectedPoint] = useState<HistoryPoint | null>(null);
    const [selectedEvent, setSelectedEvent] = useState<EventMarker | null>(null);

    if (!zone) return null;

    const evidenceBadges = {
        established: { label: "Established Evidence (NASA HRP)", color: "#009e73" },
        emerging: { label: "Emerging Research (ISS Flight Data)", color: "#0072b2" },
        illustrative: { label: "Illustrative Flight Model", color: "#e69f00" },
    };

    const ev = evidenceBadges[zone.evidence];

    // Default multi-range data if not explicitly provided
    const history24h: HistoryPoint[] = zone.history && zone.history.length > 0 ? zone.history : [
        { time: "00:00", value: zone.currentNumeric * 0.94, quality: "good" },
        { time: "04:00", value: zone.currentNumeric * 0.91, quality: "good" },
        { time: "08:00", value: zone.currentNumeric * 1.05, quality: "good" },
        { time: "12:00", value: zone.currentNumeric * 1.02, quality: "good" },
        { time: "16:00", value: zone.currentNumeric * 0.98, quality: "good" },
        { time: "20:00", value: zone.currentNumeric, quality: zone.sensorQuality === "sensor issue" ? "degraded" : "good" },
    ];

    const history7d: HistoryPoint[] = zone.history7d || [
        { time: "Sol 35", value: zone.currentNumeric * 0.97, quality: "good" },
        { time: "Sol 36", value: zone.currentNumeric * 0.96, quality: "good" },
        { time: "Sol 37", value: zone.currentNumeric * 0.99, quality: "good" },
        { time: "Sol 38", value: zone.currentNumeric * 1.04, quality: "good" },
        { time: "Sol 39", value: zone.currentNumeric * 1.07, quality: "good" },
        { time: "Sol 40", value: zone.currentNumeric * 1.01, quality: "good" },
        { time: "Sol 41", value: zone.currentNumeric, quality: "good" },
    ];

    const history14d: HistoryPoint[] = zone.history14d || [
        { time: "Sol 28", value: zone.currentNumeric * 0.96, quality: "good" },
        { time: "Sol 30", value: zone.currentNumeric * 0.98, quality: "good" },
        { time: "Sol 32", value: zone.currentNumeric * 0.95, quality: "good" },
        { time: "Sol 34", value: zone.currentNumeric * 0.99, quality: "good" },
        { time: "Sol 36", value: zone.currentNumeric * 0.97, quality: "good" },
        { time: "Sol 38", value: zone.currentNumeric * 1.03, quality: "good" },
        { time: "Sol 40", value: zone.currentNumeric * 1.02, quality: "good" },
        { time: "Sol 41", value: zone.currentNumeric, quality: "good" },
    ];

    const activeHistory = range === "24h" ? history24h : range === "7d" ? history7d : history14d;

    // Projected Forecast Cone (forecast_low to forecast_high)
    const forecast: ForecastPoint[] = zone.forecast || [
        {
            time: "+2h",
            forecastLow: zone.baselineLow + (zone.currentNumeric - zone.baselineLow) * 0.7,
            forecastHigh: zone.baselineHigh - (zone.baselineHigh - zone.currentNumeric) * 0.2,
            projected: zone.currentNumeric * 0.99,
        },
        {
            time: "+4h",
            forecastLow: zone.baselineLow + 1,
            forecastHigh: zone.baselineHigh - 1,
            projected: zone.currentNumeric * 0.98,
        },
        {
            time: "+8h",
            forecastLow: zone.baselineLow + 2,
            forecastHigh: zone.baselineHigh - 2,
            projected: (zone.baselineLow + zone.baselineHigh) / 2,
        },
    ];

    // Canonical Event Markers on timeline
    const events: EventMarker[] = zone.events || [
        {
            id: "ev_sleep",
            type: "sleep_loss",
            label: "Fragmented Rest",
            icon: "🛌",
            time: "Sol 39 02:15",
            detail: "4.2h sleep duration due to scheduled habitat telemetry pass.",
            impact: "Transient elevation in sympathetic tone and cortisol proxy.",
        },
        {
            id: "ev_exercise",
            type: "exercise",
            label: "ARED Resistance Session",
            icon: "🏋️",
            time: "Sol 40 10:30",
            detail: "2.0h resistive loading; deadlift and squat protocol.",
            impact: "Stabilizes bone calcium retention and paraspinal muscle tone.",
        },
        {
            id: "ev_eva",
            type: "eva",
            label: "Orbital Hatch EVA",
            icon: "🧑‍🚀",
            time: "Sol 41 08:00",
            detail: "High-torque suited maintenance on external docking airlock.",
            impact: "Asymmetric rotational torque produced mild left shoulder tenderness.",
        },
        {
            id: "ev_solar",
            type: "solar_event",
            label: "Solar Particle Event",
            icon: "☀️",
            time: "Sol 37 14:10",
            detail: "Transient solar proton increase detected by habitat dosimeter.",
            impact: "0.12 mSv dose absorbed; astronaut retreated to shielded bunk.",
        },
    ];

    // Chart dimensions
    const chartWidth = 560;
    const chartHeight = 180;
    const paddingX = 40;
    const paddingY = 24;

    const allValues = [
        ...activeHistory.map((h) => h.value),
        ...forecast.map((f) => f.forecastLow),
        ...forecast.map((f) => f.forecastHigh),
        zone.baselineLow,
        zone.baselineHigh,
    ];

    const minVal = Math.min(...allValues) * 0.94;
    const maxVal = Math.max(...allValues) * 1.06;

    const getY = (val: number) => {
        return (
            chartHeight -
            paddingY -
            ((val - minVal) / (maxVal - minVal)) * (chartHeight - paddingY * 2)
        );
    };

    const totalSteps = activeHistory.length + forecast.length - 1;
    const getX = (index: number) => {
        return paddingX + (index / totalSteps) * (chartWidth - paddingX * 2);
    };

    const baselineTopY = getY(zone.baselineHigh);
    const baselineBottomY = getY(zone.baselineLow);
    const baselineBandHeight = Math.max(6, baselineBottomY - baselineTopY);

    // Measured historical polyline points
    const histPoints = activeHistory.map((h, i) => `${getX(i)},${getY(h.value)}`).join(" ");

    // Forecast cone polygon points (shaded cone between forecast_low and forecast_high)
    const lastHistIdx = activeHistory.length - 1;
    const lastHistX = getX(lastHistIdx);
    const lastHistY = getY(activeHistory[lastHistIdx].value);

    const upperForecastPoints = forecast.map((f, i) => `${getX(lastHistIdx + 1 + i)},${getY(f.forecastHigh)}`).join(" ");
    const lowerForecastPoints = forecast
        .slice()
        .reverse()
        .map((f, i) => `${getX(lastHistIdx + forecast.length - i)},${getY(f.forecastLow)}`)
        .join(" ");

    const forecastConePolygon = `${lastHistX},${lastHistY} ${upperForecastPoints} ${lowerForecastPoints} ${lastHistX},${lastHistY}`;

    // Forecast projected center line
    const forecastCenterLine = `${lastHistX},${lastHistY} ` + forecast.map((f, i) => `${getX(lastHistIdx + 1 + i)},${getY(f.projected)}`).join(" ");

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 120,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "rgba(0, 0, 0, 0.75)",
                backdropFilter: "blur(8px)",
                padding: "16px",
            }}
            onClick={onClose}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: "640px",
                    maxHeight: "92vh",
                    overflowY: "auto",
                    background: "rgba(11, 20, 27, 0.98)",
                    border: "1px solid rgba(0, 229, 255, 0.35)",
                    borderRadius: "24px",
                    padding: "28px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "20px",
                    boxShadow: "0 24px 60px rgba(0, 0, 0, 0.85), inset 0 0 40px rgba(0, 229, 255, 0.05)",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                        <span style={{ fontSize: "32px" }}>{zone.icon}</span>
                        <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                                <h3 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#ffffff" }}>
                                    {zone.name}
                                </h3>
                                <StatusBadge level={zone.level} size="sm" />
                            </div>
                            <div style={{ fontSize: "13px", color: "#94a3b8", fontFamily: "var(--font-mono, monospace)" }}>
                                Current Reading:{" "}
                                <strong style={{ color: "#00e5ff", fontSize: "15px" }}>
                                    {zone.value} {zone.unit}
                                </strong>
                            </div>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close detail panel"
                        style={{
                            background: "rgba(255, 255, 255, 0.08)",
                            color: "#ffffff",
                            border: "none",
                            borderRadius: "8px",
                            padding: "6px 12px",
                            fontSize: "14px",
                            cursor: "pointer",
                        }}
                    >
                        ✕
                    </button>
                </div>

                {/* Evidence Badge & Fault Gate Data-Quality Chip */}
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
                    <span
                        style={{
                            fontSize: "11px",
                            fontFamily: "var(--font-mono, monospace)",
                            padding: "4px 10px",
                            borderRadius: "8px",
                            border: `1px solid ${ev.color}50`,
                            backgroundColor: `${ev.color}15`,
                            color: ev.color,
                            fontWeight: 600,
                        }}
                    >
                        {ev.label}
                    </span>

                    {/* Sensor Data Quality Chip (from Fault Gate) */}
                    <div
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono, monospace)",
                            padding: "4px 10px",
                            borderRadius: "8px",
                            border:
                                zone.sensorQuality === "good"
                                    ? "1px solid rgba(0, 158, 115, 0.45)"
                                    : "1px solid rgba(230, 159, 0, 0.65)",
                            backgroundColor:
                                zone.sensorQuality === "good"
                                    ? "rgba(0, 158, 115, 0.15)"
                                    : "rgba(230, 159, 0, 0.2)",
                            color: zone.sensorQuality === "good" ? "#009e73" : "#e69f00",
                            fontWeight: 600,
                        }}
                    >
                        <span>{zone.sensorQuality === "good" ? "✓" : "⚠️"}</span>
                        <span>
                            {zone.sensorQuality === "good"
                                ? "Data Quality: Good (Sensor Telemetry Nominal)"
                                : "Data Quality: FAULTY_SENSOR (Hardware telemetry issue, not a health alert)"}
                        </span>
                    </div>
                </div>

                {/* ADVANCED TIME-SERIES CHART */}
                <div
                    style={{
                        background: "rgba(15, 26, 34, 0.75)",
                        borderRadius: "18px",
                        padding: "18px 20px",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px",
                    }}
                >
                    {/* Chart Header & Range Toggle */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div>
                            <strong style={{ fontSize: "13px", color: "#ffffff" }}>
                                Time-Series Trend & Predictive Cone
                            </strong>
                            <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                                Tap any point or event pin for details
                            </div>
                        </div>

                        {/* Range Toggle: 24h / 7d / 14d */}
                        <div
                            style={{
                                display: "inline-flex",
                                background: "rgba(0, 0, 0, 0.4)",
                                borderRadius: "8px",
                                padding: "2px",
                                border: "1px solid rgba(255, 255, 255, 0.1)",
                            }}
                        >
                            {(["24h", "7d", "14d"] as const).map((r) => (
                                <button
                                    key={r}
                                    type="button"
                                    onClick={() => {
                                        setRange(r);
                                        setSelectedPoint(null);
                                    }}
                                    style={{
                                        background: range === r ? "rgba(0, 229, 255, 0.25)" : "transparent",
                                        color: range === r ? "#00e5ff" : "#94a3b8",
                                        border: "none",
                                        padding: "4px 10px",
                                        borderRadius: "6px",
                                        fontSize: "11px",
                                        fontFamily: "var(--font-mono, monospace)",
                                        fontWeight: 700,
                                        cursor: "pointer",
                                    }}
                                >
                                    {r}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* SVG Chart Graphic */}
                    <div style={{ position: "relative", width: "100%", height: `${chartHeight}px` }}>
                        <svg
                            width="100%"
                            height={chartHeight}
                            viewBox={`0 0 ${chartWidth} ${chartHeight}`}
                            preserveAspectRatio="none"
                            style={{ overflow: "visible" }}
                        >
                            <defs>
                                <linearGradient id="forecastGradient" x1="0" y1="0" x2="1" y2="0">
                                    <stop offset="0%" stopColor="#00e5ff" stopOpacity="0.25" />
                                    <stop offset="100%" stopColor="#00e5ff" stopOpacity="0.05" />
                                </linearGradient>
                            </defs>

                            {/* Shaded Personal Normal Range Band (baseline_low to baseline_high) */}
                            <rect
                                x={paddingX}
                                y={baselineTopY}
                                width={chartWidth - paddingX * 2}
                                height={baselineBandHeight}
                                fill="rgba(0, 229, 255, 0.1)"
                                stroke="rgba(0, 229, 255, 0.35)"
                                strokeDasharray="3 3"
                            />

                            {/* Baseline Threshold Guideline Labels */}
                            <text
                                x={paddingX + 6}
                                y={baselineTopY + 12}
                                fill="rgba(0, 229, 255, 0.75)"
                                fontSize="9"
                                fontFamily="monospace"
                            >
                                Baseline Upper: {zone.baselineHigh} {zone.unit}
                            </text>
                            <text
                                x={paddingX + 6}
                                y={baselineBottomY - 4}
                                fill="rgba(0, 229, 255, 0.75)"
                                fontSize="9"
                                fontFamily="monospace"
                            >
                                Baseline Lower: {zone.baselineLow} {zone.unit}
                            </text>

                            {/* Shaded Predictive Forecast Cone */}
                            <polygon points={forecastConePolygon} fill="url(#forecastGradient)" />
                            <polyline
                                fill="none"
                                stroke="#00e5ff"
                                strokeWidth="1.5"
                                strokeDasharray="4 4"
                                points={forecastCenterLine}
                            />

                            {/* Measured Historical Polyline */}
                            <polyline
                                fill="none"
                                stroke="#00e5ff"
                                strokeWidth="2.8"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                points={histPoints}
                            />

                            {/* Interactive Data Points on Historical Line */}
                            {activeHistory.map((pt, i) => {
                                const px = getX(i);
                                const py = getY(pt.value);
                                const isSelected = selectedPoint?.time === pt.time;

                                return (
                                    <g key={pt.time} style={{ cursor: "pointer" }} onClick={() => setSelectedPoint(pt)}>
                                        <circle
                                            cx={px}
                                            cy={py}
                                            r={isSelected ? 6 : 4}
                                            fill={isSelected ? "#ffffff" : "#00e5ff"}
                                            stroke="#0a151b"
                                            strokeWidth="2"
                                        />
                                    </g>
                                );
                            })}
                        </svg>

                        {/* Interactive Event Markers on Timeline */}
                        <div
                            style={{
                                position: "absolute",
                                top: "8px",
                                left: `${paddingX}px`,
                                right: `${paddingX}px`,
                                display: "flex",
                                justifyContent: "space-between",
                                pointerEvents: "none",
                            }}
                        >
                            {events.map((evItem) => (
                                <button
                                    key={evItem.id}
                                    type="button"
                                    onClick={() => setSelectedEvent(evItem)}
                                    title={`${evItem.label} (${evItem.time}) - Click for details`}
                                    style={{
                                        pointerEvents: "auto",
                                        background: selectedEvent?.id === evItem.id ? "rgba(0, 229, 255, 0.35)" : "rgba(18, 30, 38, 0.9)",
                                        border: `1px solid ${selectedEvent?.id === evItem.id ? "#00e5ff" : "rgba(255, 255, 255, 0.2)"}`,
                                        borderRadius: "8px",
                                        padding: "3px 7px",
                                        fontSize: "11px",
                                        color: "#ffffff",
                                        cursor: "pointer",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: "4px",
                                    }}
                                >
                                    <span>{evItem.icon}</span>
                                    <span style={{ fontSize: "10px", fontFamily: "var(--font-mono, monospace)" }}>
                                        {evItem.label.split(" ")[0]}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Chart Legend & Explanations */}
                    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "8px", fontSize: "11px", color: "#94a3b8" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                                <span style={{ width: "12px", height: "10px", background: "rgba(0, 229, 255, 0.15)", border: "1px dashed #00e5ff", display: "inline-block" }} />
                                Your normal range ({zone.baselineLow}–{zone.baselineHigh} {zone.unit})
                            </span>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                                <span style={{ width: "12px", height: "8px", background: "rgba(0, 229, 255, 0.3)", display: "inline-block" }} />
                                Forecast cone (Next Sol)
                            </span>
                        </div>
                        <span style={{ fontStyle: "italic" }}>Personal baseline, never population norm</span>
                    </div>

                    {/* Selected Point Callout (Tap point for value & quality) */}
                    {selectedPoint && (
                        <div
                            style={{
                                padding: "8px 12px",
                                borderRadius: "10px",
                                background: "rgba(0, 229, 255, 0.12)",
                                border: "1px solid rgba(0, 229, 255, 0.35)",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                fontSize: "12px",
                            }}
                        >
                            <div>
                                <strong style={{ color: "#ffffff" }}>Reading at {selectedPoint.time}: </strong>
                                <span style={{ color: "#00e5ff", fontFamily: "var(--font-mono, monospace)", fontWeight: 700 }}>
                                    {selectedPoint.value.toFixed(1)} {zone.unit}
                                </span>
                            </div>
                            <span style={{ color: "#a4c2cb", fontSize: "11px" }}>
                                Quality: <strong style={{ color: selectedPoint.quality === "good" ? "#009e73" : "#e69f00" }}>{selectedPoint.quality}</strong>
                            </span>
                        </div>
                    )}

                    {/* Selected Event Marker Callout */}
                    {selectedEvent && (
                        <div
                            style={{
                                padding: "10px 14px",
                                borderRadius: "10px",
                                background: "rgba(18, 32, 42, 0.9)",
                                border: "1px solid rgba(255, 255, 255, 0.15)",
                                display: "flex",
                                flexDirection: "column",
                                gap: "4px",
                                fontSize: "12px",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <strong style={{ color: "#ffffff", display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span>{selectedEvent.icon}</span> {selectedEvent.label} ({selectedEvent.time})
                                </strong>
                                <button
                                    type="button"
                                    onClick={() => setSelectedEvent(null)}
                                    style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "12px" }}
                                >
                                    ✕
                                </button>
                            </div>
                            <p style={{ margin: 0, color: "#e2e8f0" }}>{selectedEvent.detail}</p>
                            <span style={{ fontSize: "11px", color: "#00e5ff" }}>
                                <strong>Physiological Context:</strong> {selectedEvent.impact}
                            </span>
                        </div>
                    )}
                </div>

                {/* 3-DEPTH "WHY THIS MATTERS" CARD */}
                <div
                    style={{
                        background: "rgba(15, 26, 34, 0.75)",
                        borderRadius: "18px",
                        padding: "18px 20px",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "13px", fontWeight: 700, color: "#ffffff", textTransform: "uppercase" }}>
                            Why this matters in spaceflight
                        </span>

                        {/* 3-Depth Toggles */}
                        <div style={{ display: "flex", gap: "4px", background: "rgba(0,0,0,0.3)", padding: "2px", borderRadius: "8px" }}>
                            <button
                                type="button"
                                onClick={() => setDepthLevel(1)}
                                style={{
                                    fontSize: "11px",
                                    padding: "3px 10px",
                                    borderRadius: "6px",
                                    border: "none",
                                    cursor: "pointer",
                                    background: depthLevel === 1 ? "rgba(255, 255, 255, 0.2)" : "transparent",
                                    color: depthLevel === 1 ? "#ffffff" : "#94a3b8",
                                    fontWeight: depthLevel === 1 ? 700 : 500,
                                }}
                            >
                                1. One line
                            </button>
                            <button
                                type="button"
                                onClick={() => setDepthLevel(2)}
                                style={{
                                    fontSize: "11px",
                                    padding: "3px 10px",
                                    borderRadius: "6px",
                                    border: "none",
                                    cursor: "pointer",
                                    background: depthLevel === 2 ? "rgba(255, 255, 255, 0.2)" : "transparent",
                                    color: depthLevel === 2 ? "#ffffff" : "#94a3b8",
                                    fontWeight: depthLevel === 2 ? 700 : 500,
                                }}
                            >
                                2. Context
                            </button>
                            <button
                                type="button"
                                onClick={() => setDepthLevel(3)}
                                style={{
                                    fontSize: "11px",
                                    padding: "3px 10px",
                                    borderRadius: "6px",
                                    border: "none",
                                    cursor: "pointer",
                                    background: depthLevel === 3 ? "rgba(255, 255, 255, 0.2)" : "transparent",
                                    color: depthLevel === 3 ? "#ffffff" : "#94a3b8",
                                    fontWeight: depthLevel === 3 ? 700 : 500,
                                }}
                            >
                                3. Learn more
                            </button>
                        </div>
                    </div>

                    <div style={{ fontSize: "13px", color: "#e2e8f0", lineHeight: 1.5 }}>
                        {depthLevel === 1 && (
                            <p style={{ margin: 0, fontWeight: 500 }}>{zone.oneLiner}</p>
                        )}
                        {depthLevel === 2 && (
                            <p style={{ margin: 0 }}>{zone.shortParagraph}</p>
                        )}
                        {depthLevel === 3 && (
                            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                <p style={{ margin: 0 }}>{zone.deepContext}</p>
                                <div
                                    style={{
                                        fontSize: "11px",
                                        color: "#94a3b8",
                                        background: "rgba(0, 0, 0, 0.3)",
                                        padding: "8px 12px",
                                        borderRadius: "8px",
                                        borderLeft: "3px solid #00e5ff",
                                    }}
                                >
                                    <strong>Flight Surgeon Protocol:</strong> Trend monitoring active. Check with terrestrial flight surgeon before adjusting medication or workout intensity.
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Mandatory Universal Disclaimer Footer */}
                <div style={{ marginTop: "auto", fontSize: "11px", color: "rgba(255, 255, 255, 0.45)", textAlign: "center", fontFamily: "var(--font-mono, monospace)" }}>
                    Simulated data. Decision support, not a medical device.
                </div>
            </div>
        </div>
    );
}
