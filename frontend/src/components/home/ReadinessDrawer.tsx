"use client";

import React from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface Factor {
    title: string;
    score: number;
    weight: string;
    level: StatusLevel;
    summary: string;
    detail: string;
}

interface ReadinessDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    overallScore: number;
    overallLevel: StatusLevel;
}

export default function ReadinessDrawer({
    isOpen,
    onClose,
    overallScore,
    overallLevel,
}: ReadinessDrawerProps) {
    if (!isOpen) return null;

    const factors: Factor[] = [
        {
            title: "Cardiovascular Stability",
            score: 95,
            weight: "30%",
            level: "normal",
            summary: "Resting heart rate 72 bpm within personal baseline (60–82 bpm).",
            detail: "Hemodynamic response during ergometer session matches baseline. Left ventricular stroke volume nominal.",
        },
        {
            title: "Sleep & Circadian Rhythm",
            score: 92,
            weight: "30%",
            level: "normal",
            summary: "8.2 hours total sleep, 3.4h deep REM recovery.",
            detail: "Psychomotor vigilance (PVT) reaction time 184 ms indicates peak alertness. Habitat circadian dimming aligned.",
        },
        {
            title: "Musculoskeletal & Joint Strain",
            score: 84,
            weight: "20%",
            level: "watch",
            summary: "Mild left shoulder impingement context detected post-EVA hatch repair.",
            detail: "Spine elongation +1.8 cm within expected 0G limits. Rotator cuff resistance band routine recommended before next suited sortie.",
        },
        {
            title: "Immune Stress & Radiation Context",
            score: 93,
            weight: "20%",
            level: "normal",
            summary: "Cumulative Sol radiation 0.42 mSv, stress biomarkers nominal.",
            detail: "Treg/cytokine balance remains resilient. Not a diagnosis; context indicates stable cellular protection.",
        },
    ];

    return (
        <div
            style={{
                position: "fixed",
                inset: 0,
                zIndex: 100,
                display: "flex",
                justifyContent: "flex-end",
                background: "rgba(0, 0, 0, 0.65)",
                backdropFilter: "blur(6px)",
            }}
            onClick={onClose}
        >
            <div
                style={{
                    width: "100%",
                    maxWidth: "520px",
                    height: "100%",
                    background: "rgba(10, 18, 24, 0.98)",
                    borderLeft: "1px solid rgba(0, 229, 255, 0.25)",
                    padding: "32px 28px",
                    overflowY: "auto",
                    display: "flex",
                    flexDirection: "column",
                    gap: "24px",
                    boxShadow: "-12px 0 40px rgba(0, 0, 0, 0.8)",
                }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                            <h2 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#ffffff" }}>
                                Readiness Factor Breakdown
                            </h2>
                            <StatusBadge level={overallLevel} size="sm" />
                        </div>
                        <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8" }}>
                            Mission Clearance Algorithm · Individual baseline comparison
                        </p>
                    </div>

                    <button
                        type="button"
                        onClick={onClose}
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

                {/* Score Summary Box */}
                <div
                    style={{
                        padding: "16px 20px",
                        borderRadius: "16px",
                        background: "rgba(0, 229, 255, 0.06)",
                        border: "1px solid rgba(0, 229, 255, 0.2)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                    }}
                >
                    <div>
                        <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>Overall Score</span>
                        <div style={{ fontSize: "32px", fontWeight: 800, color: "#ffffff", fontFamily: "var(--font-mono, monospace)" }}>
                            {overallScore} <span style={{ fontSize: "14px", color: "#64748b" }}>/ 100</span>
                        </div>
                    </div>
                    <div style={{ textAlign: "right", fontSize: "12px", color: "#00e5ff", maxWidth: "200px" }}>
                        All 4 systems operating within flight-safe baseline boundaries.
                    </div>
                </div>

                {/* Breakdown List */}
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                    {factors.map((f, i) => (
                        <div
                            key={i}
                            style={{
                                padding: "16px",
                                borderRadius: "14px",
                                background: "rgba(18, 30, 38, 0.6)",
                                border: "1px solid rgba(255, 255, 255, 0.08)",
                                display: "flex",
                                flexDirection: "column",
                                gap: "10px",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <strong style={{ fontSize: "14px", color: "#ffffff" }}>{f.title}</strong>
                                    <span style={{ fontSize: "11px", color: "rgba(255, 255, 255, 0.4)", fontFamily: "var(--font-mono, monospace)" }}>
                                        weight {f.weight}
                                    </span>
                                </div>
                                <StatusBadge level={f.level} size="sm" />
                            </div>

                            {/* Progress bar */}
                            <div style={{ height: "6px", width: "100%", background: "rgba(255, 255, 255, 0.08)", borderRadius: "999px", overflow: "hidden" }}>
                                <div
                                    style={{
                                        height: "100%",
                                        width: `${f.score}%`,
                                        background: f.level === "watch" ? "#e69f00" : "#009e73",
                                        borderRadius: "999px",
                                    }}
                                />
                            </div>

                            <p style={{ margin: 0, fontSize: "12px", color: "#e2e8f0", lineHeight: 1.4 }}>
                                {f.summary}
                            </p>

                            <p style={{ margin: 0, fontSize: "11px", color: "#94a3b8", lineHeight: 1.4 }}>
                                <strong>Context:</strong> {f.detail}
                            </p>
                        </div>
                    ))}
                </div>

                <div style={{ marginTop: "auto", fontSize: "11px", color: "rgba(255, 255, 255, 0.4)", textAlign: "center" }}>
                    Simulated data. Decision support, not a medical device.
                </div>
            </div>
        </div>
    );
}
