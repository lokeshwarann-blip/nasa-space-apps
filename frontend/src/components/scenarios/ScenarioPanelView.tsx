"use client";

import React, { useState } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";
import DisclaimerFooter from "../common/DisclaimerFooter";

export interface ScenarioInfo {
    scenario_id: string;
    name: string;
    description: string;
    alert_level: StatusLevel;
    alert_title: string;
    alert_reason: string;
    alert_next_step: string;
    sensor_quality: "good" | "sensor issue";
    network_link_status: "online" | "blackout";
    telemetry_hr: number;
    telemetry_spo2: number;
    telemetry_temp: number;
    message: string;
}

interface ScenarioPanelViewProps {
    alertLevel?: StatusLevel;
    onApplyScenario?: (scenario: ScenarioInfo) => void;
}

const PRESET_SCENARIOS = [
    {
        id: "nominal",
        name: "Nominal Flight Baseline",
        icon: "🛰️",
        level: "normal" as StatusLevel,
        badgeText: "●✓ Nominal",
        summary: "All environmental scrubbers, life support, and crew vitals within personalized normal baseline bands.",
        impact: "Zero alerts. Routine Sol 41 operational schedule.",
    },
    {
        id: "dust_storm",
        name: "Martian Dust Storm (Atmospheric Opacity)",
        icon: "🌪️",
        level: "watch" as StatusLevel,
        badgeText: "▲ Watch Advisory",
        summary: "Atmospheric optical depth (tau > 3.0) reduces solar array yield by 65%. Habitat enters power-saving mode.",
        impact: "HEPA air scrubbing verified, non-critical EVA postponed, indoor lighting dimmed.",
    },
    {
        id: "comms_blackout",
        name: "Deep Space Comms Blackout (Solar Conjunction)",
        icon: "📡",
        level: "watch" as StatusLevel,
        badgeText: "▲ Link Offline",
        summary: "Terrestrial ground station relay occluded by solar conjunction. Full autonomous edge decision support active.",
        impact: "Telemetry cached locally in memory. Zero data loss. Offline-tolerant mode demonstrated.",
    },
    {
        id: "sensor_fault",
        name: "Biometric Sensor Anomaly (Optical Dropout)",
        icon: "⚡",
        level: "watch" as StatusLevel,
        badgeText: "◆ Sensor Issue",
        summary: "Left ring finger photoplethysmogram clip photodiode loses optical coupling during resistance workout.",
        impact: "Fault Gate triggers: Displayed as hardware sensor issue, NEVER as an astronaut health emergency.",
    },
    {
        id: "coordinated_drift",
        name: "Coordinated Physiological Drift (Post-EVA Strain)",
        icon: "🩺",
        level: "act" as StatusLevel,
        badgeText: "◆ Action Required",
        summary: "Post-EVA hatch egress fluid loss induces mild resting tachycardia (88 bpm) and thermal drift (37.6°C).",
        impact: "Exceeds personal normal baseline band (58–82 bpm). Rehydration & cooling garment protocol engaged.",
    },
];

export default function ScenarioPanelView({
    alertLevel = "normal",
    onApplyScenario,
}: ScenarioPanelViewProps) {
    const [activeScenarioId, setActiveScenarioId] = useState<string>("nominal");
    const [isTriggering, setIsTriggering] = useState<boolean>(false);
    const [notification, setNotification] = useState<string | null>(null);

    const handleSelectScenario = async (scId: string) => {
        setIsTriggering(true);
        setActiveScenarioId(scId);

        try {
            const res = await fetch("http://127.0.0.1:8000/api/v1/scenario", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario_id: scId }),
            });

            if (res.ok) {
                const data: ScenarioInfo = await res.json();
                setNotification(`Scenario Activated: ${data.name}`);
                if (onApplyScenario) {
                    onApplyScenario(data);
                }
            }
        } catch {
            setNotification(`Simulated offline scenario: ${scId}`);
        } finally {
            setIsTriggering(false);
            setTimeout(() => setNotification(null), 3500);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "22px", width: "100%", paddingBottom: "36px" }}>
            {/* Header Banner */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "14px",
                    background: "rgba(15, 23, 42, 0.7)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "14px",
                    padding: "20px 24px",
                    backdropFilter: "blur(12px)",
                }}
            >
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span
                            style={{
                                fontSize: "18px",
                                background: "rgba(204, 121, 167, 0.2)",
                                padding: "6px 10px",
                                borderRadius: "8px",
                                border: "1px solid rgba(204, 121, 167, 0.4)",
                            }}
                        >
                            🎮
                        </span>
                        <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                            Scenario Panel (Demo & Simulation Mode)
                        </h1>
                        <span
                            style={{
                                padding: "3px 8px",
                                borderRadius: "6px",
                                fontSize: "11px",
                                fontWeight: 700,
                                fontFamily: "monospace",
                                background: "rgba(0, 114, 178, 0.15)",
                                color: "#70b6ff",
                                border: "1px solid rgba(0, 114, 178, 0.35)",
                            }}
                        >
                            Live System Stress Test
                        </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", maxWidth: "680px", lineHeight: 1.5 }}>
                        Trigger pre-programmed environmental and physiological scenarios (`POST /api/v1/scenario`) to test live UI reactions,
                        data-quality fault gates, offline comms tolerance, and alert state management.
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <button
                        onClick={() => handleSelectScenario("nominal")}
                        style={{
                            background: "rgba(0, 158, 115, 0.15)",
                            border: "1px solid rgba(0, 158, 115, 0.4)",
                            color: "#009e73",
                            borderRadius: "8px",
                            padding: "6px 14px",
                            fontSize: "12px",
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                        }}
                    >
                        <span>↺ Restore Nominal Baseline</span>
                    </button>
                </div>
            </div>

            {/* Notification Toast */}
            {notification && (
                <div
                    style={{
                        background: "rgba(0, 114, 178, 0.2)",
                        border: "1px solid rgba(0, 114, 178, 0.5)",
                        borderRadius: "10px",
                        padding: "12px 18px",
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "#f8fafc",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                    }}
                >
                    <span>⚡ {notification}</span>
                </div>
            )}

            {/* Scenarios Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
                    gap: "18px",
                }}
            >
                {PRESET_SCENARIOS.map((sc) => {
                    const isActive = activeScenarioId === sc.id;
                    return (
                        <div
                            key={sc.id}
                            style={{
                                background: isActive
                                    ? "linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(2, 132, 199, 0.15) 100%)"
                                    : "rgba(15, 23, 42, 0.8)",
                                border: isActive ? "2px solid #0072b2" : "1px solid rgba(255, 255, 255, 0.08)",
                                borderRadius: "16px",
                                padding: "20px",
                                display: "flex",
                                flexDirection: "column",
                                gap: "12px",
                                transition: "all 0.2s ease",
                                boxShadow: isActive ? "0 0 20px rgba(0, 114, 178, 0.3)" : "none",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                                    <span style={{ fontSize: "24px" }}>{sc.icon}</span>
                                    <div>
                                        <h3 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "#f8fafc" }}>
                                            {sc.name}
                                        </h3>
                                    </div>
                                </div>
                                <StatusBadge level={sc.level} size="sm" label={sc.badgeText} />
                            </div>

                            <p style={{ margin: 0, fontSize: "12px", color: "#cbd5e1", lineHeight: 1.5 }}>
                                {sc.summary}
                            </p>

                            <div
                                style={{
                                    background: "rgba(0, 0, 0, 0.3)",
                                    borderRadius: "8px",
                                    padding: "8px 12px",
                                    fontSize: "11px",
                                    color: "#94a3b8",
                                    lineHeight: 1.4,
                                    marginTop: "auto",
                                }}
                            >
                                <strong>System Impact:</strong> {sc.impact}
                            </div>

                            <button
                                onClick={() => handleSelectScenario(sc.id)}
                                disabled={isTriggering && isActive}
                                style={{
                                    marginTop: "6px",
                                    background: isActive ? "rgba(0, 114, 178, 0.3)" : "rgba(255, 255, 255, 0.06)",
                                    border: `1px solid ${isActive ? "rgba(0, 114, 178, 0.6)" : "rgba(255, 255, 255, 0.12)"}`,
                                    color: isActive ? "#70b6ff" : "#f8fafc",
                                    borderRadius: "8px",
                                    padding: "8px 14px",
                                    fontSize: "12px",
                                    fontWeight: 700,
                                    cursor: "pointer",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    gap: "6px",
                                }}
                            >
                                {isActive ? "✓ Scenario Active" : "Trigger Scenario →"}
                            </button>
                        </div>
                    );
                })}
            </div>

            {/* Rule Assurance Box */}
            <div
                style={{
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid rgba(255, 255, 255, 0.06)",
                    borderRadius: "12px",
                    padding: "16px 20px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                    fontSize: "12px",
                    color: "#94a3b8",
                }}
            >
                <strong style={{ color: "#f8fafc" }}>NASA Medical & Telemetry Safety Protocols Verified:</strong>
                <span>• Fault Gate: Sensor dropouts flag hardware degradation, never health emergencies.</span>
                <span>• Alert Suppression: In alert states (`watch`, `act`, `call_ground`), all celebratory gamification effects are automatically muted.</span>
                <span>• Language Rule: Strictly no words like &ldquo;diagnosis&rdquo; — system acts as non-diagnostic flight decision support.</span>
            </div>

            {/* Universal Footer (Global Rule 3) */}
            <DisclaimerFooter />
        </div>
    );
}
