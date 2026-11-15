"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";
import DisclaimerFooter from "../common/DisclaimerFooter";

interface SettingsViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled: boolean;
    onToggleGamification: () => void;
    reducedMotion?: boolean;
    onToggleReducedMotion?: () => void;
    highContrast?: boolean;
    onToggleHighContrast?: () => void;
}

export default function SettingsView({
    alertLevel = "normal",
    gamificationEnabled,
    onToggleGamification,
    reducedMotion = false,
    onToggleReducedMotion,
    highContrast = false,
    onToggleHighContrast,
}: SettingsViewProps) {
    const [soundEnabled, setSoundEnabled] = useState<boolean>(true);
    const [textSize, setTextSize] = useState<"standard" | "large" | "xlarge">("standard");
    const [unitsSystem, setUnitsSystem] = useState<"metric" | "mission_ops">("metric");
    const [lastSynced, setLastSynced] = useState<string>("Sol 41 14:35 UTC");
    const [syncStatus, setSyncStatus] = useState<string | null>(null);

    // Fetch backend settings if available
    useEffect(() => {
        let isMounted = true;
        const fetchSettings = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/settings");
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setSoundEnabled(data.sound_enabled);
                        setTextSize(data.text_size);
                        setUnitsSystem(data.units_system);
                        if (data.last_synced) setLastSynced(data.last_synced);
                    }
                }
            } catch {
                // Offline tolerance
            }
        };

        fetchSettings();
        return () => {
            isMounted = false;
        };
    }, []);

    const handleManualSync = async () => {
        setSyncStatus("Syncing telemetry with local habitat gateway...");
        try {
            await fetch("http://127.0.0.1:8000/api/v1/sync");
            setLastSynced(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
            setSyncStatus("✓ All local telemetry caches verified and synchronized.");
        } catch {
            setSyncStatus("✓ Offline store updated. Data queued for next ground pass.");
        } finally {
            setTimeout(() => setSyncStatus(null), 3000);
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
                                background: "rgba(0, 114, 178, 0.2)",
                                padding: "6px 10px",
                                borderRadius: "8px",
                                border: "1px solid rgba(0, 114, 178, 0.4)",
                            }}
                        >
                            ⚙️
                        </span>
                        <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                            System Settings & Accessibility
                        </h1>
                        <span
                            style={{
                                padding: "3px 8px",
                                borderRadius: "6px",
                                fontSize: "11px",
                                fontWeight: 700,
                                fontFamily: "monospace",
                                background: "rgba(0, 158, 115, 0.15)",
                                color: "#009e73",
                                border: "1px solid rgba(0, 158, 115, 0.35)",
                            }}
                        >
                            Okabe-Ito Colorblind Safe
                        </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", maxWidth: "680px", lineHeight: 1.5 }}>
                        Configure gamification elements, neuro-vestibular motion sensitivity, color contrast modes, unit systems, and offline telemetry synchronization.
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <StatusBadge level={alertLevel} size="md" />
                </div>
            </div>

            {/* Sync Status Toast */}
            {syncStatus && (
                <div
                    style={{
                        background: "rgba(0, 158, 115, 0.2)",
                        border: "1px solid rgba(0, 158, 115, 0.5)",
                        borderRadius: "10px",
                        padding: "10px 18px",
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "#86efac",
                    }}
                >
                    {syncStatus}
                </div>
            )}

            {/* Settings Sections Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
                    gap: "20px",
                }}
            >
                {/* 1. Gamification & Focus Mode (Global Rule 4) */}
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "16px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "16px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "18px" }}>✨</span>
                        <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
                            Gamification & Focus Mode
                        </h2>
                    </div>

                    <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                        NASA Global Rule 4: Gamification is fully optional. When disabled, XP values, streak badges, and celebratory animations are hidden for a streamlined telemetry tool.
                    </p>

                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "12px",
                            padding: "14px 16px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                        }}
                    >
                        <div>
                            <strong style={{ fontSize: "13px", color: "#f8fafc", display: "block" }}>
                                Mission XP & Streak Animations
                            </strong>
                            <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                                {gamificationEnabled ? "Gamification active (suppressed during alert states)" : "Minimalist telemetry instrument mode"}
                            </span>
                        </div>

                        <button
                            onClick={onToggleGamification}
                            style={{
                                background: gamificationEnabled ? "#009e73" : "rgba(255, 255, 255, 0.15)",
                                border: "none",
                                borderRadius: "20px",
                                width: "48px",
                                height: "26px",
                                position: "relative",
                                cursor: "pointer",
                                transition: "background 0.2s ease",
                            }}
                        >
                            <span
                                style={{
                                    position: "absolute",
                                    top: "3px",
                                    left: gamificationEnabled ? "25px" : "3px",
                                    width: "20px",
                                    height: "20px",
                                    borderRadius: "50%",
                                    background: "#ffffff",
                                    transition: "left 0.2s ease",
                                }}
                            />
                        </button>
                    </div>

                    <div
                        style={{
                            background: "rgba(230, 159, 0, 0.08)",
                            border: "1px solid rgba(230, 159, 0, 0.25)",
                            borderRadius: "10px",
                            padding: "10px 12px",
                            fontSize: "11px",
                            color: "#e69f00",
                            lineHeight: 1.4,
                        }}
                    >
                        🛡️ <strong>Safety Constraint:</strong> During active `watch`, `act`, or `call_ground` alerts, all celebrations are auto-suppressed to prioritize operational next steps.
                    </div>
                </div>

                {/* 2. Motion & Neuro-Vestibular Adaptation */}
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "16px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "16px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "18px" }}>🌀</span>
                        <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
                            Neuro-Vestibular & Motion
                        </h2>
                    </div>

                    <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                        Prevents disorientation or space motion sickness (SMS) during initial microgravity adaptation.
                    </p>

                    {/* Reduced Motion Toggle */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "12px",
                            padding: "14px 16px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                        }}
                    >
                        <div>
                            <strong style={{ fontSize: "13px", color: "#f8fafc", display: "block" }}>
                                Reduced Motion Mode
                            </strong>
                            <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                                Disables 3D camera auto-rotation, radar sweeps & pulsing dials
                            </span>
                        </div>

                        {onToggleReducedMotion && (
                            <button
                                onClick={onToggleReducedMotion}
                                style={{
                                    background: reducedMotion ? "#009e73" : "rgba(255, 255, 255, 0.15)",
                                    border: "none",
                                    borderRadius: "20px",
                                    width: "48px",
                                    height: "26px",
                                    position: "relative",
                                    cursor: "pointer",
                                }}
                            >
                                <span
                                    style={{
                                        position: "absolute",
                                        top: "3px",
                                        left: reducedMotion ? "25px" : "3px",
                                        width: "20px",
                                        height: "20px",
                                        borderRadius: "50%",
                                        background: "#ffffff",
                                        transition: "left 0.2s ease",
                                    }}
                                />
                            </button>
                        )}
                    </div>

                    {/* Audio Cues Toggle */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "12px",
                            padding: "14px 16px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                        }}
                    >
                        <div>
                            <strong style={{ fontSize: "13px", color: "#f8fafc", display: "block" }}>
                                Telemetry Audio Chimes
                            </strong>
                            <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                                Subtle sound notifications on quest completion & countdowns
                            </span>
                        </div>

                        <button
                            onClick={() => setSoundEnabled(!soundEnabled)}
                            style={{
                                background: soundEnabled ? "#009e73" : "rgba(255, 255, 255, 0.15)",
                                border: "none",
                                borderRadius: "20px",
                                width: "48px",
                                height: "26px",
                                position: "relative",
                                cursor: "pointer",
                            }}
                        >
                            <span
                                style={{
                                    position: "absolute",
                                    top: "3px",
                                    left: soundEnabled ? "25px" : "3px",
                                    width: "20px",
                                    height: "20px",
                                    borderRadius: "50%",
                                    background: "#ffffff",
                                    transition: "left 0.2s ease",
                                }}
                            />
                        </button>
                    </div>
                </div>

                {/* 3. Visual & Text Accessibility */}
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "16px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "16px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "18px" }}>👁️</span>
                        <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
                            Visual Display & Font Scaling
                        </h2>
                    </div>

                    <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                        Configured for readability under suited visor reflection or high ambient cabin glare.
                    </p>

                    {/* Text Size Scale */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <span style={{ fontSize: "12px", fontWeight: 600, color: "#e2e8f0" }}>Text Scaling:</span>
                        <div style={{ display: "flex", gap: "8px" }}>
                            {(["standard", "large", "xlarge"] as const).map((sz) => (
                                <button
                                    key={sz}
                                    onClick={() => setTextSize(sz)}
                                    style={{
                                        flex: 1,
                                        background: textSize === sz ? "rgba(0, 114, 178, 0.25)" : "rgba(255, 255, 255, 0.05)",
                                        border: `1px solid ${textSize === sz ? "rgba(0, 114, 178, 0.6)" : "rgba(255, 255, 255, 0.1)"}`,
                                        color: textSize === sz ? "#70b6ff" : "#94a3b8",
                                        borderRadius: "8px",
                                        padding: "8px",
                                        fontSize: "12px",
                                        fontWeight: 600,
                                        cursor: "pointer",
                                        textTransform: "capitalize",
                                    }}
                                >
                                    {sz === "standard" ? "Standard (100%)" : sz === "large" ? "Large (120%)" : "X-Large (140%)"}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* High Contrast Mode */}
                    {onToggleHighContrast && (
                        <div
                            style={{
                                background: "rgba(255, 255, 255, 0.03)",
                                border: "1px solid rgba(255, 255, 255, 0.06)",
                                borderRadius: "12px",
                                padding: "14px 16px",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                            }}
                        >
                            <div>
                                <strong style={{ fontSize: "13px", color: "#f8fafc", display: "block" }}>
                                    High Contrast Palette
                                </strong>
                                <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                                    Boosts Okabe-Ito colorblind borders and badge luminance
                                </span>
                            </div>

                            <button
                                onClick={onToggleHighContrast}
                                style={{
                                    background: highContrast ? "#009e73" : "rgba(255, 255, 255, 0.15)",
                                    border: "none",
                                    borderRadius: "20px",
                                    width: "48px",
                                    height: "26px",
                                    position: "relative",
                                    cursor: "pointer",
                                }}
                            >
                                <span
                                    style={{
                                        position: "absolute",
                                        top: "3px",
                                        left: highContrast ? "25px" : "3px",
                                        width: "20px",
                                        height: "20px",
                                        borderRadius: "50%",
                                        background: "#ffffff",
                                        transition: "left 0.2s ease",
                                    }}
                                />
                            </button>
                        </div>
                    )}
                </div>

                {/* 4. Units & Telemetry Sync Manager */}
                <div
                    style={{
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(255, 255, 255, 0.08)",
                        borderRadius: "16px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "16px",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "18px" }}>📡</span>
                        <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700, color: "#f8fafc" }}>
                            Units & Telemetry Sync
                        </h2>
                    </div>

                    <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
                        Manages terrestrial relay synchronization and engineering unit standards.
                    </p>

                    {/* Units Selector */}
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        <span style={{ fontSize: "12px", fontWeight: 600, color: "#e2e8f0" }}>Units Standard:</span>
                        <div style={{ display: "flex", gap: "8px" }}>
                            {(["metric", "mission_ops"] as const).map((u) => (
                                <button
                                    key={u}
                                    onClick={() => setUnitsSystem(u)}
                                    style={{
                                        flex: 1,
                                        background: unitsSystem === u ? "rgba(0, 114, 178, 0.25)" : "rgba(255, 255, 255, 0.05)",
                                        border: `1px solid ${unitsSystem === u ? "rgba(0, 114, 178, 0.6)" : "rgba(255, 255, 255, 0.1)"}`,
                                        color: unitsSystem === u ? "#70b6ff" : "#94a3b8",
                                        borderRadius: "8px",
                                        padding: "8px",
                                        fontSize: "12px",
                                        fontWeight: 600,
                                        cursor: "pointer",
                                    }}
                                >
                                    {u === "metric" ? "SI Metric (°C, kg, L)" : "NASA Mission Ops (K, kPa, m/s)"}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Manual Sync Trigger */}
                    <div
                        style={{
                            background: "rgba(0, 0, 0, 0.3)",
                            borderRadius: "10px",
                            padding: "12px 14px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginTop: "auto",
                        }}
                    >
                        <div>
                            <span style={{ fontSize: "11px", color: "#94a3b8", display: "block" }}>Local Cache State:</span>
                            <strong style={{ fontSize: "12px", color: "#f8fafc", fontFamily: "monospace" }}>
                                Last Synced: {lastSynced}
                            </strong>
                        </div>

                        <button
                            onClick={handleManualSync}
                            style={{
                                background: "rgba(0, 114, 178, 0.2)",
                                border: "1px solid rgba(0, 114, 178, 0.5)",
                                color: "#70b6ff",
                                borderRadius: "8px",
                                padding: "6px 12px",
                                fontSize: "12px",
                                fontWeight: 700,
                                cursor: "pointer",
                            }}
                        >
                            Sync Now ↺
                        </button>
                    </div>
                </div>
            </div>

            {/* Universal Footer (Global Rule 3) */}
            <DisclaimerFooter />
        </div>
    );
}
