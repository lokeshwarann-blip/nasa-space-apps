"use client";

import React, { useState } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface ReadinessRingProps {
    score: number; // 0 to 100
    level: StatusLevel;
    confidence?: "high" | "moderate" | "low";
    onOpenDrawer?: () => void;
    className?: string;
}

export default function ReadinessRing({
    score,
    level,
    confidence = "high",
    onOpenDrawer,
    className = "",
}: ReadinessRingProps) {
    const [expanded, setExpanded] = useState(false);

    // Ring geometry (3px stroke, coral arc over a --line track)
    const radius = 80;
    const strokeWidth = 3;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (score / 100) * circumference;

    const statusChipLabels: Record<StatusLevel, string> = {
        normal: "Ready",
        watch: "Watch",
        act: "Act",
        call_ground: "Call Ground",
    };

    const confidenceLabels = {
        high: "Confidence: High (100% active)",
        moderate: "Confidence: Moderate (1 stale)",
        low: "Confidence: Low (recovering)",
    };

    const factors = [
        { name: "Cardiovascular Stability", score: 95, weight: "30%", level: "normal" as StatusLevel, note: "Resting HR 72 bpm nominal" },
        { name: "Sleep & Circadian Rhythm", score: 92, weight: "30%", level: "normal" as StatusLevel, note: "8.2h rest, PVT 184 ms optimal" },
        { name: "Musculoskeletal & Joint Strain", score: 84, weight: "20%", level: "watch" as StatusLevel, note: "Mild shoulder strain post-docking" },
        { name: "Immune Stress & Radiation Context", score: 93, weight: "20%", level: "normal" as StatusLevel, note: "Cumulative Sol 41 dose 0.42 mSv" },
    ];

    const handleClick = () => {
        setExpanded(!expanded);
        if (onOpenDrawer) {
            onOpenDrawer();
        }
    };

    return (
        <section
            className={className}
            onClick={handleClick}
            role="button"
            tabIndex={0}
            aria-expanded={expanded}
            onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleClick();
                }
            }}
            aria-label={`Readiness score: ${score} out of 100. Status: ${statusChipLabels[level]}. Click to toggle breakdown.`}
            style={{
                background: "var(--surface, rgba(6,8,14,0.86))",
                borderRadius: "2px",
                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "24px",
                cursor: "pointer",
                boxShadow: "none",
            }}
        >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                        EVA Readiness Score
                    </h3>
                    <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", letterSpacing: "0.06em" }}>
                        Mission Clearance Sol 41
                    </p>
                </div>

                <StatusBadge level={level} label={statusChipLabels[level]} size="sm" />
            </div>

            {/* Circular Ring Graphic: 3px stroke, coral arc over --line track */}
            <div style={{ position: "relative", width: "184px", height: "184px", display: "grid", placeItems: "center" }}>
                <svg width="184" height="184" viewBox="0 0 184 184" style={{ transform: "rotate(-90deg)" }}>
                    {/* Background track */}
                    <circle
                        cx="92"
                        cy="92"
                        r={radius}
                        fill="none"
                        stroke="var(--line, rgba(233,228,223,0.16))"
                        strokeWidth={strokeWidth}
                    />

                    {/* Progress track */}
                    <circle
                        cx="92"
                        cy="92"
                        r={radius}
                        fill="none"
                        stroke="var(--accent, #FF4D5A)"
                        strokeWidth={strokeWidth}
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        strokeLinecap="square"
                        style={{
                            transition: "stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
                        }}
                    />
                </svg>

                {/* Center score in Syne 64px+ */}
                <div style={{ position: "absolute", display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <span
                        style={{
                            fontSize: "68px",
                            fontWeight: 800,
                            color: "var(--text, #ECE8E3)",
                            fontFamily: "var(--font-display, sans-serif)",
                            letterSpacing: "-0.04em",
                            lineHeight: 0.9,
                        }}
                    >
                        {score}
                    </span>
                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", marginTop: "6px", textTransform: "uppercase", fontFamily: "var(--font-mono, monospace)", letterSpacing: "0.16em" }}>
                        out of 100
                    </span>
                </div>
            </div>

            {/* Uncertainty Chip & Chevron */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                <span
                    style={{
                        padding: "3px 8px",
                        borderRadius: "2px",
                        background: "var(--surface-2, rgba(255,255,255,0.04))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                        color: "var(--muted, rgba(236,232,227,0.55))",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px",
                    }}
                >
                    <svg width="10" height="10" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
                        <polygon points="5,1.5 11,1.5 14.5,5 14.5,11 11,14.5 5,14.5 1.5,11 1.5,5" />
                    </svg>
                    {confidenceLabels[confidence]}
                </span>

                {/* Small chevron icon instead of text */}
                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: "24px",
                        height: "24px",
                        color: "var(--accent, #FF4D5A)",
                        transition: "transform 0.2s ease",
                        transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
                    }}
                    aria-label={expanded ? "Collapse breakdown" : "Expand breakdown"}
                >
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="4 6 8 10 12 6" />
                    </svg>
                </span>
            </div>

            {/* Expandable 4-Factor Breakdown */}
            {expanded && (
                <div
                    style={{
                        width: "100%",
                        paddingTop: "16px",
                        borderTop: "1px solid var(--line, rgba(233,228,223,0.16))",
                        display: "flex",
                        flexDirection: "column",
                        gap: "12px",
                    }}
                    onClick={(e) => e.stopPropagation()}
                >
                    {factors.map((f) => (
                        <div
                            key={f.name}
                            style={{
                                padding: "10px 12px",
                                borderRadius: "2px",
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                display: "flex",
                                flexDirection: "column",
                                gap: "6px",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                    {f.name}
                                </span>
                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                        WT {f.weight}
                                    </span>
                                    <StatusBadge level={f.level} size="sm" />
                                </div>
                            </div>
                            <div style={{ width: "100%", height: "2px", background: "var(--line, rgba(233,228,223,0.16))", overflow: "hidden" }}>
                                <div
                                    style={{
                                        width: `${f.score}%`,
                                        height: "100%",
                                        background: f.level === "watch" ? "var(--warn, #FFB84D)" : "var(--accent, #FF4D5A)",
                                    }}
                                />
                            </div>
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                {f.note}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}
