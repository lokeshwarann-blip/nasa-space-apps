"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";
import ZoneZoomPanel, { ZoneData } from "./ZoneZoomPanel";

// Dynamic import for the 3D model component to ensure client-only WebGL rendering
const HumanBody = dynamic(() => import("../HumanBody"), { ssr: false });

export default function BodyMap() {
    const [selectedZone, setSelectedZone] = useState<ZoneData | null>(null);
    const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);
    const [focusedOrgan, setFocusedOrgan] = useState<string | null>(null);
    const [viewMode, setViewMode] = useState<"3d" | "2d">("3d");

    // 6 Canonical Anatomical Zones with individual baselines & telemetry
    const ZONES: Record<string, ZoneData & { organKey: string; meterPct: number }> = {
        brain: {
            id: "brain",
            organKey: "brain",
            name: "Brain & Sleep",
            icon: "BRN",
            level: "normal",
            value: "8.2",
            unit: "hours rest",
            baselineLow: 7.0,
            baselineHigh: 9.0,
            currentNumeric: 8.2,
            meterPct: 88,
            evidence: "established",
            sensorQuality: "good",
            oneLiner: "Circadian alignment and cognitive reaction latency are at optimal flight vigilance.",
            shortParagraph:
                "Psychomotor Vigilance Test (PVT) median reaction latency is 184 ms. Headward fluid shift has produced nominal intracranial pressure with zero reported visual disturbance (SANS screen clear).",
            deepContext:
                "Microgravity eliminates hydrostatic pressure gradients, causing 1.5–2.0L of cephalad fluid redistribution. While optic nerve sheath diameter (ONSD) remains stable at 5.2 mm, monitoring sleep fragmentation is essential for cognitive autonomy.",
            history: [
                { time: "00:00", value: 7.8 },
                { time: "04:00", value: 8.0 },
                { time: "08:00", value: 8.4 },
                { time: "12:00", value: 8.1 },
                { time: "16:00", value: 8.3 },
                { time: "20:00", value: 8.2 },
            ],
        },
        heart: {
            id: "heart",
            organKey: "heart",
            name: "Heart & Vessels",
            icon: "HRT",
            level: "normal",
            value: "72",
            unit: "bpm",
            baselineLow: 60,
            baselineHigh: 82,
            currentNumeric: 72,
            meterPct: 75,
            evidence: "established",
            sensorQuality: "good",
            oneLiner: "Cardiac rhythm and stroke volume are steady within resting personal limits.",
            shortParagraph:
                "Resting heart rate 72 bpm with 118/76 mmHg mean arterial pressure. Cardiac workload has adapted to microgravity; left ventricular myocardial compliance remains nominal.",
            deepContext:
                "In weightlessness, central venous pressure transiently elevates then stabilizes. Daily 45-minute aerobic sessions maintain left ventricular end-diastolic volume, counteracting orthostatic intolerance.",
            history: [
                { time: "00:00", value: 68 },
                { time: "04:00", value: 65 },
                { time: "08:00", value: 76 },
                { time: "12:00", value: 74 },
                { time: "16:00", value: 71 },
                { time: "20:00", value: 72 },
            ],
        },
        lungs: {
            id: "lungs",
            organKey: "lungs",
            name: "Lungs & Chest",
            icon: "LNG",
            level: "normal",
            value: "98",
            unit: "% SpO2",
            baselineLow: 96,
            baselineHigh: 100,
            currentNumeric: 98,
            meterPct: 98,
            evidence: "established",
            sensorQuality: "good",
            oneLiner: "Pulmonary diffusion capacity and tissue oxygenation are fully nominal.",
            shortParagraph:
                "Blood oxygen saturation 98% under 21% O2 habitat mix. Ventilation-perfusion matching across apical and basilar zones is balanced without fluid congestion.",
            deepContext:
                "Zero-G removes gravitational alveolar ventilation gradients. Thoracic compliance is slightly reduced by upward diaphragmatic displacement; lung vital capacity is 97% of terrestrial pre-flight baseline.",
            history: [
                { time: "00:00", value: 98 },
                { time: "04:00", value: 97 },
                { time: "08:00", value: 99 },
                { time: "12:00", value: 98 },
                { time: "16:00", value: 98 },
                { time: "20:00", value: 98 },
            ],
        },
        bones: {
            id: "bones",
            organKey: "skeleton",
            name: "Bones & Spine",
            icon: "SKL",
            level: "normal",
            value: "96.2",
            unit: "% density",
            baselineLow: 94.0,
            baselineHigh: 100.0,
            currentNumeric: 96.2,
            meterPct: 96,
            evidence: "established",
            sensorQuality: "good",
            oneLiner: "Trabecular mineral density in lumbar spine and calcaneus is well-preserved.",
            shortParagraph:
                "Spinal elongation +1.8 cm over baseline; paraspinal stiffness managed via daily axial loading. Urinary calcium excretion indicates stable calcium homeostasis under ARED resistive protocol.",
            deepContext:
                "Without continuous 1G gravitational loading, osteoclastic resorption outpaces osteoblastic formation. Astronaut Thorne's resistance regime successfully suppresses bone demineralization to <0.3% this month.",
            history: [
                { time: "00:00", value: 96.5 },
                { time: "04:00", value: 96.4 },
                { time: "08:00", value: 96.3 },
                { time: "12:00", value: 96.2 },
                { time: "16:00", value: 96.2 },
                { time: "20:00", value: 96.2 },
            ],
        },
        muscles: {
            id: "muscles",
            organKey: "muscles",
            name: "Muscles & Limbs",
            icon: "MSC",
            level: "watch",
            value: "Grade 1",
            unit: "shoulder strain",
            baselineLow: 0,
            baselineHigh: 0,
            currentNumeric: 1,
            meterPct: 60,
            evidence: "established",
            sensorQuality: "good",
            oneLiner: "Localized left rotator cuff tenderness context from high-torque orbital hatch maintenance.",
            shortParagraph:
                "Mild anterior deltoid strain noted. Post-EVA biomechanical telemetry recorded asymmetric shoulder loading during docking hatch torque operations.",
            deepContext:
                "Zero-G posture shifts natural arm resting position higher (neutral body posture). Recommended next step: 10-minute resistance band rotator cuff stretching before next suited sortie. Check with flight surgeon if pain escalates.",
            history: [
                { time: "00:00", value: 0 },
                { time: "04:00", value: 0 },
                { time: "08:00", value: 1 },
                { time: "12:00", value: 1 },
                { time: "16:00", value: 1 },
                { time: "20:00", value: 1 },
            ],
        },
        immune: {
            id: "immune",
            organKey: "digestive",
            name: "Immune Stress",
            icon: "IMM",
            level: "normal",
            value: "Low Stress",
            unit: "context",
            baselineLow: 0,
            baselineHigh: 1,
            currentNumeric: 0.3,
            meterPct: 90,
            evidence: "emerging",
            sensorQuality: "good",
            oneLiner: "T-cell activation and latent viral containment remain intact. Not a diagnosis.",
            shortParagraph:
                "Cellular stress context indicates stable immune modulation. Cumulative cosmic radiation exposure (0.42 mSv Sol 41) remains well beneath NASA lifetime career limits.",
            deepContext:
                "Spaceflight stressors (microgravity, confinement, sleep shifts, ionizing radiation) alter peripheral leukocyte distribution. Biomarker panel confirms Epstein-Barr virus reactivation remains suppressed.",
            history: [
                { time: "00:00", value: 0.2 },
                { time: "04:00", value: 0.2 },
                { time: "08:00", value: 0.3 },
                { time: "12:00", value: 0.4 },
                { time: "16:00", value: 0.3 },
                { time: "20:00", value: 0.3 },
            ],
        },
    };

    const handleZoneClick = (zone: ZoneData & { organKey: string }) => {
        setFocusedOrgan(zone.organKey);
        setSelectedZone(zone);
    };

    return (
        <section
            style={{
                background: "rgba(18, 18, 24, 0.82)",
                backdropFilter: "blur(14px)",
                borderRadius: "24px",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                gap: "16px",
                boxShadow: "0 12px 32px rgba(0, 0, 0, 0.35)",
            }}
        >
            {/* Header */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "10px" }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: "17px", fontWeight: 700, color: "#ffffff" }}>
                        Anatomical Telemetry & Organ Systems
                    </h3>
                    <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "#94a3b8" }}>
                        {viewMode === "3d"
                            ? "High-precision 3D body viewer · Tap any system to zoom directly into organs & view personal baseline"
                            : "2D SVG Body Map · Interactive pins with status shapes, miniature meters & personal baselines"}
                    </p>
                </div>

                {/* View Mode Toggle: 3D Model vs 2D SVG Body Map */}
                <div style={{ display: "flex", gap: "4px", background: "rgba(0, 0, 0, 0.4)", borderRadius: "8px", padding: "3px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
                    <button
                        onClick={() => setViewMode("3d")}
                        style={{
                            background: viewMode === "3d" ? "rgba(0, 114, 178, 0.3)" : "transparent",
                            color: viewMode === "3d" ? "#70b6ff" : "#94a3b8",
                            border: viewMode === "3d" ? "1px solid rgba(0, 114, 178, 0.5)" : "none",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                        }}
                    >
                        <span>3D Anatomy Model</span>
                    </button>
                    <button
                        onClick={() => setViewMode("2d")}
                        style={{
                            background: viewMode === "2d" ? "rgba(0, 114, 178, 0.3)" : "transparent",
                            color: viewMode === "2d" ? "#70b6ff" : "#94a3b8",
                            border: viewMode === "2d" ? "1px solid rgba(0, 114, 178, 0.5)" : "none",
                            borderRadius: "6px",
                            padding: "4px 10px",
                            fontSize: "12px",
                            fontWeight: 600,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                        }}
                    >
                        <span>2D Zone Map</span>
                    </button>
                </div>
            </div>

            {/* 6 Canonical Zones Selector Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                    gap: "10px",
                }}
            >
                {Object.entries(ZONES).map(([key, zone]) => {
                    const isHovered = hoveredZoneId === key;
                    const isSelected = selectedZone?.id === key;

                    return (
                        <div
                            key={key}
                            onClick={() => handleZoneClick(zone)}
                            onMouseEnter={() => setHoveredZoneId(key)}
                            onMouseLeave={() => setHoveredZoneId(null)}
                            role="button"
                            tabIndex={0}
                            aria-label={`${zone.name}. Status: ${zone.level}. Value: ${zone.value} ${zone.unit}. Tap to zoom in 3D.`}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" || e.key === " ") {
                                    e.preventDefault();
                                    handleZoneClick(zone);
                                }
                            }}
                            style={{
                                position: "relative",
                                padding: "10px 12px",
                                borderRadius: "12px",
                                background: isSelected
                                    ? "rgba(0, 229, 255, 0.15)"
                                    : isHovered
                                    ? "rgba(18, 32, 42, 0.85)"
                                    : "rgba(14, 24, 32, 0.6)",
                                border: `1px solid ${
                                    isSelected
                                        ? "#00e5ff"
                                        : zone.level === "watch"
                                        ? "rgba(230, 159, 0, 0.45)"
                                        : "rgba(255, 255, 255, 0.08)"
                                }`,
                                cursor: "pointer",
                                display: "flex",
                                flexDirection: "column",
                                gap: "6px",
                                transition: "all 0.2s ease",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                    <span style={{ fontSize: "16px" }}>{zone.icon}</span>
                                    <strong style={{ fontSize: "12px", color: "#ffffff", whiteSpace: "nowrap" }}>
                                        {zone.name}
                                    </strong>
                                </div>
                                <StatusBadge level={zone.level} size="sm" />
                            </div>

                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                                <span style={{ fontSize: "12px", fontWeight: 700, color: "#c3f5ff", fontFamily: "var(--font-mono, monospace)" }}>
                                    {zone.value} <span style={{ fontSize: "10px", color: "#94a3b8" }}>{zone.unit}</span>
                                </span>
                            </div>

                            {/* Mini Progress Meter */}
                            <div style={{ width: "100%", height: "4px", background: "rgba(255, 255, 255, 0.08)", borderRadius: "999px", overflow: "hidden" }}>
                                <div
                                    style={{
                                        width: `${zone.meterPct}%`,
                                        height: "100%",
                                        background: zone.level === "watch" ? "#e69f00" : "#009e73",
                                        borderRadius: "999px",
                                    }}
                                />
                            </div>

                            {/* Hover Tooltip: Value + Personal Baseline */}
                            {isHovered && (
                                <div
                                    style={{
                                        position: "absolute",
                                        bottom: "108%",
                                        left: "50%",
                                        transform: "translateX(-50%)",
                                        background: "rgba(8, 16, 22, 0.98)",
                                        border: "1px solid rgba(0, 229, 255, 0.4)",
                                        borderRadius: "10px",
                                        padding: "8px 12px",
                                        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.8)",
                                        whiteSpace: "nowrap",
                                        pointerEvents: "none",
                                        zIndex: 40,
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "2px",
                                    }}
                                >
                                    <div style={{ fontSize: "11px", color: "#ffffff", fontWeight: 700 }}>
                                        {zone.name}: {zone.value} {zone.unit}
                                    </div>
                                    <div style={{ fontSize: "10px", color: "#00e5ff", fontFamily: "var(--font-mono, monospace)" }}>
                                        Your normal range: {zone.baselineLow}–{zone.baselineHigh} {zone.unit}
                                    </div>
                                    <div style={{ fontSize: "9px", color: "#94a3b8", marginTop: "2px" }}>
                                        Click to zoom 3D camera into organ →
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* 3D Model or 2D SVG Body Map */}
            {viewMode === "3d" ? (
                <div style={{ width: "100%", marginTop: "4px" }}>
                    <HumanBody
                        height={520}
                        focusedOrgan={focusedOrgan}
                        onSelectOrgan={(organId) => {
                            const matched = Object.values(ZONES).find((z) => z.organKey === organId || z.id === organId);
                            if (matched) setSelectedZone(matched);
                        }}
                    />
                </div>
            ) : (
                /* 2D SVG Body Map with Multi-Modal Pins & Meters */
                <div
                    style={{
                        position: "relative",
                        width: "100%",
                        height: "520px",
                        background: "radial-gradient(circle at center, rgba(14, 30, 45, 0.6) 0%, rgba(8, 16, 24, 0.9) 100%)",
                        borderRadius: "16px",
                        border: "1px solid rgba(255, 255, 255, 0.06)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        overflow: "hidden",
                    }}
                >
                    <svg viewBox="0 0 320 480" style={{ height: "92%", width: "auto" }}>
                        {/* Human Body Silhouette */}
                        <path
                            d="M 160 35 C 172 35 182 45 182 60 C 182 72 174 82 165 85 C 178 92 195 104 205 125 L 225 185 C 228 195 222 205 212 205 C 206 205 201 200 198 194 L 186 150 L 186 240 L 195 360 C 196 372 188 380 178 380 C 170 380 164 374 163 366 L 160 260 L 157 366 C 156 374 150 380 142 380 C 132 380 124 372 125 360 L 134 240 L 134 150 L 122 194 C 119 200 114 205 108 205 C 98 205 92 195 95 185 L 115 125 C 125 104 142 92 155 85 C 146 82 138 72 138 60 C 138 45 148 35 160 35 Z"
                            fill="rgba(0, 114, 178, 0.12)"
                            stroke="rgba(0, 229, 255, 0.4)"
                            strokeWidth="1.5"
                            strokeLinejoin="round"
                        />

                        {/* Head Circle */}
                        <circle cx="160" cy="58" r="16" fill="rgba(0, 114, 178, 0.2)" stroke="rgba(0, 229, 255, 0.5)" strokeWidth="1.2" />

                        {/* Ribcage / Torso lines */}
                        <path d="M 148 120 Q 160 128 172 120 M 144 135 Q 160 144 176 135 M 142 150 Q 160 160 178 150" fill="none" stroke="rgba(255, 255, 255, 0.12)" strokeWidth="1" />
                        <line x1="160" y1="85" x2="160" y2="240" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1.2" strokeDasharray="3 3" />

                        {/* Interactive Zone Pins on 2D Body Map */}
                        {[
                            { key: "brain", x: 160, y: 58 },
                            { key: "lungs", x: 140, y: 135 },
                            { key: "heart", x: 180, y: 145 },
                            { key: "immune", x: 160, y: 185 },
                            { key: "muscles", x: 104, y: 160 },
                            { key: "bones", x: 160, y: 245 },
                        ].map((pin) => {
                            const z = ZONES[pin.key];
                            const isPinHovered = hoveredZoneId === pin.key;
                            const pinColor = z.level === "watch" ? "#e69f00" : "#009e73";
                            const shapeText = z.level === "watch" ? "▲" : "●✓";

                            return (
                                <g
                                    key={pin.key}
                                    onClick={() => setSelectedZone(z)}
                                    onMouseEnter={() => setHoveredZoneId(pin.key)}
                                    onMouseLeave={() => setHoveredZoneId(null)}
                                    style={{ cursor: "pointer" }}
                                >
                                    {/* Pulse aura */}
                                    <circle cx={pin.x} cy={pin.y} r={isPinHovered ? 18 : 14} fill={pinColor} fillOpacity="0.25" stroke={pinColor} strokeWidth="1" />
                                    <circle cx={pin.x} cy={pin.y} r="10" fill="#081018" stroke={pinColor} strokeWidth="1.8" />
                                    <text x={pin.x} y={pin.y + 3.5} fill={pinColor} fontSize="8" fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                                        {shapeText}
                                    </text>

                                    {/* Pin Label with Mini Meter */}
                                    <g transform={`translate(${pin.x > 160 ? pin.x + 16 : pin.x - 72}, ${pin.y - 12})`}>
                                        <rect width="60" height="22" rx="4" fill="rgba(8, 16, 24, 0.9)" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="0.8" />
                                        <text x="6" y="10" fill="#f8fafc" fontSize="7.5" fontWeight="bold">
                                            {z.name.split(" ")[0]}
                                        </text>
                                        <rect x="6" y="14" width="48" height="3" rx="1.5" fill="rgba(255, 255, 255, 0.1)" />
                                        <rect x="6" y="14" width={(48 * z.meterPct) / 100} height="3" rx="1.5" fill={pinColor} />
                                    </g>
                                </g>
                            );
                        })}
                    </svg>

                    <span style={{ position: "absolute", bottom: "12px", right: "16px", fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>
                        Tap any pin to inspect personal baseline & forecast cone
                    </span>
                </div>
            )}

            {/* Zone Detail Modal with Personal Baseline Chart */}
            <ZoneZoomPanel zone={selectedZone} onClose={() => setSelectedZone(null)} />
        </section>
    );
}
