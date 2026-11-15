"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface ImmuneShieldViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
    onNavigateToQuests?: () => void;
}

interface Stressor {
    id: string;
    name: string;
    value: string;
    impact_pct: number;
    icon: string;
    mechanism: string;
}

export default function ImmuneShieldView({
    onNavigateToQuests,
}: ImmuneShieldViewProps) {
    const BASELINE_LOW = 70;
    const BASELINE_HIGH = 95;

    const [shieldScore, setShieldScore] = useState<number>(74);
    const [stressors, setStressors] = useState<Stressor[]>([
        {
            id: "sleep_debt",
            name: "Cumulative Sleep Debt",
            value: "1.8 hrs deficit",
            impact_pct: 14,
            icon: "sleep",
            mechanism: "Elevates FOXP3+ regulatory T-cells (Tregs) and temporarily down-regulates interleukin cascades.",
        },
        {
            id: "mission_stress",
            name: "Operational & Confinement Stress",
            value: "Elevated cortisol profile",
            impact_pct: 8,
            icon: "stress",
            mechanism: "Subclinical latent viral reactivation pressure (EBV, CMV) under chronic glucocorticoid elevations.",
        },
        {
            id: "radiation_dose",
            name: "Cosmic Radiation Dosimetry",
            value: "0.42 mSv transit dose",
            impact_pct: 4,
            icon: "rad",
            mechanism: "High-Z/Energy (HZE) particle ionization tracks stimulating DNA double-strand repair responses.",
        },
        {
            id: "fluid_shift",
            name: "Cephalad Fluid Shift",
            value: "Active rostral gradient",
            impact_pct: 5,
            icon: "fluid",
            mechanism: "Central venous and cranial lymphatic congestion slowing microvascular interstitial drainage.",
        },
    ]);

    const [activeStressor, setActiveStressor] = useState<Stressor | null>(null);

    useEffect(() => {
        let isMounted = true;
        const fetchImmune = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/immune/shield");
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setShieldScore(data.shield_score);
                        if (data.stressors) setStressors(data.stressors);
                    }
                }
            } catch {
                // Offline tolerance
            }
        };

        fetchImmune();
        return () => {
            isMounted = false;
        };
    }, []);

    const radius = 80;
    const strokeWidth = 3;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (shieldScore / 100) * circumference;

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Main Stage Grid: Shield Meter (Left) + Multi-Factor Stressor Cards (Right) */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr)) 1.25fr",
                    gap: "24px",
                    alignItems: "start",
                }}
            >
                {/* Left: Shield Meter Display */}
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
                            Immune Resilience Capacity
                        </h3>
                        <StatusBadge level="watch" label="Moderate Stress" size="sm" />
                    </div>

                    {/* Circular Shield Gauge */}
                    <div
                        style={{
                            position: "relative",
                            width: "184px",
                            height: "184px",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                        }}
                    >
                        <svg width="184" height="184" viewBox="0 0 184 184" style={{ transform: "rotate(-90deg)" }}>
                            <circle
                                cx="92"
                                cy="92"
                                r={radius}
                                fill="none"
                                stroke="var(--line, rgba(233,228,223,0.16))"
                                strokeWidth={strokeWidth}
                            />
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
                                style={{ transition: "stroke-dashoffset 0.6s ease" }}
                            />
                        </svg>

                        <div
                            style={{
                                position: "absolute",
                                display: "flex",
                                flexDirection: "column",
                                alignItems: "center",
                            }}
                        >
                            <span style={{ fontSize: "64px", fontWeight: 800, fontFamily: "var(--font-display, sans-serif)", color: "var(--text, #ECE8E3)", lineHeight: 0.9 }}>
                                {shieldScore}
                            </span>
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.14em", marginTop: "4px" }}>
                                / 100 PTS
                            </span>
                        </div>
                    </div>

                    <div
                        style={{
                            width: "100%",
                            background: "var(--surface-2, rgba(255,255,255,0.04))",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "10px 14px",
                            display: "flex",
                            justifyContent: "space-between",
                            fontSize: "11px",
                            fontFamily: "var(--font-mono, monospace)",
                            color: "var(--muted, rgba(236,232,227,0.55))",
                        }}
                    >
                        <span>YOUR NORMAL RANGE:</span>
                        <strong style={{ color: "var(--cool, #8FB8E8)" }}>{BASELINE_LOW} – {BASELINE_HIGH} PTS</strong>
                    </div>

                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textAlign: "center" }}>
                        Decision support context · check with flight surgeon
                    </span>
                </div>

                {/* Right: Stressor Breakdown */}
                <div
                    style={{
                        background: "var(--surface, rgba(6,8,14,0.86))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        borderRadius: "2px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "20px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                            Spaceflight Stressor Influences
                        </h3>
                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                            Select for Mechanism
                        </span>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                        {stressors.map((s) => {
                            const isSelected = activeStressor?.id === s.id;
                            return (
                                <div
                                    key={s.id}
                                    onClick={() => setActiveStressor(isSelected ? null : s)}
                                    style={{
                                        background: isSelected ? "var(--surface-2, rgba(255,255,255,0.08))" : "var(--surface-2, rgba(255,255,255,0.04))",
                                        border: isSelected ? "1px solid var(--accent, #FF4D5A)" : "1px solid var(--line, rgba(233,228,223,0.16))",
                                        borderRadius: "2px",
                                        padding: "12px 14px",
                                        cursor: "pointer",
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "8px",
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                                            {s.name}
                                        </span>
                                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                                {s.value}
                                            </span>
                                            <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--accent, #FF4D5A)", fontFamily: "var(--font-mono, monospace)" }}>
                                                -{s.impact_pct}%
                                            </span>
                                        </div>
                                    </div>

                                    {isSelected && (
                                        <p style={{ margin: "4px 0 0 0", fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.6, fontFamily: "var(--font-mono, monospace)" }}>
                                            {s.mechanism}
                                        </p>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    {onNavigateToQuests && (
                        <button
                            type="button"
                            onClick={onNavigateToQuests}
                            style={{
                                marginTop: "auto",
                                background: "var(--accent, #FF4D5A)",
                                color: "var(--accent-ink, #030307)",
                                border: "none",
                                borderRadius: "2px",
                                padding: "8px 16px",
                                fontSize: "12px",
                                fontFamily: "var(--font-mono, monospace)",
                                fontWeight: 600,
                                letterSpacing: "0.14em",
                                textTransform: "uppercase",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                justifyContent: "center",
                                gap: "8px",
                            }}
                        >
                            Open Countermeasure Quests →
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
