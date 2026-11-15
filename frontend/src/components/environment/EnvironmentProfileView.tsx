"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";
import DisclaimerFooter from "../common/DisclaimerFooter";

export interface EnvironmentProfile {
    id: string;
    name: string;
    icon: string;
    gravity_g: number;
    gravity_label: string;
    radiation_context: string;
    ambient_o2_kpa: number;
    ambient_co2_mmhg: number;
    diurnal_cycle: string;
    baseline_hr_low: number;
    baseline_high: number;
    countermeasure_focus: string;
    description: string;
}

interface EnvironmentProfileViewProps {
    alertLevel?: StatusLevel;
    onProfileChanged?: (profile: EnvironmentProfile) => void;
}

const DEFAULT_PROFILES: EnvironmentProfile[] = [
    {
        id: "mars_base",
        name: "Mars Surface Habitat",
        icon: "🔴",
        gravity_g: 0.38,
        gravity_label: "0.38 G (Martian Surface)",
        radiation_context: "Partial regolith berm shielding (0.35 mSv/sol)",
        ambient_o2_kpa: 21.3,
        ambient_co2_mmhg: 3.8,
        diurnal_cycle: "24h 39m 35s (Martian Sol)",
        baseline_hr_low: 58.0,
        baseline_high: 82.0,
        countermeasure_focus: "Orthostatic tolerance under 0.38G & perchlorate dust scrubbing",
        description: "Martian outpost habitat with subsurface regolith shielding and circadian tracking locked to the 24.65h Sol.",
    },
    {
        id: "spacecraft",
        name: "Deep Space Transit Vehicle (Orion/Starship)",
        icon: "🚀",
        gravity_g: 0.0,
        gravity_label: "Microgravity (0.0 G)",
        radiation_context: "Deep space GCR / Solar Particle Storm Shelter (1.2 mSv/sol)",
        ambient_o2_kpa: 23.5,
        ambient_co2_mmhg: 4.5,
        diurnal_cycle: "24.0h Artificial UTC lighting schedule",
        baseline_hr_low: 56.0,
        baseline_high: 80.0,
        countermeasure_focus: "Intensive ARED resistance (2.5h/day) to prevent 1% monthly bone demineralization",
        description: "Interplanetary transfer vehicle in transit between Earth and Mars. Maximum microgravity fluid shift context.",
    },
    {
        id: "space_station",
        name: "Orbital Space Station (ISS / Gateway)",
        icon: "🛰️",
        gravity_g: 0.0,
        gravity_label: "Microgravity (0.0 G)",
        radiation_context: "Low Earth Orbit / Geomagnetic cusp transit (0.5 mSv/sol)",
        ambient_o2_kpa: 21.0,
        ambient_co2_mmhg: 3.2,
        diurnal_cycle: "90-minute orbital sunrise/sunset anchored by 480nm LED interior lighting",
        baseline_hr_low: 58.0,
        baseline_high: 82.0,
        countermeasure_focus: "T2 treadmill, Cycle Ergometer (CEVIS), and SANS optical coherence tomography",
        description: "Permanent microgravity research outpost with daily tele-guidance from terrestrial flight surgeons.",
    },
    {
        id: "rover",
        name: "Pressurized Exploration Rover",
        icon: "🚜",
        gravity_g: 0.38,
        gravity_label: "0.38 G (Martian Surface)",
        radiation_context: "Mobile storm shelter water wall (0.45 mSv/sol)",
        ambient_o2_kpa: 24.0,
        ambient_co2_mmhg: 5.0,
        diurnal_cycle: "24h 39m Sol diurnal cycle",
        baseline_hr_low: 60.0,
        baseline_high: 85.0,
        countermeasure_focus: "Whole-body vibration dampening, suit egress ergonomics, and acute hydration",
        description: "Mobile pressurized exploration module supporting multi-sol surface traverses beyond base perimeter.",
    },
    {
        id: "lunar_base",
        name: "Lunar Surface Outpost (Artemis Base Camp)",
        icon: "🌕",
        gravity_g: 0.166,
        gravity_label: "0.166 G (Lunar Surface)",
        radiation_context: "Lava tube habitat / Sintered regolith shielding (0.28 mSv/sol)",
        ambient_o2_kpa: 22.0,
        ambient_co2_mmhg: 3.5,
        diurnal_cycle: "14 Earth-day lunar day / 14 Earth-day night cycle (Artificial habitat chronobiology)",
        baseline_hr_low: 57.0,
        baseline_high: 81.0,
        countermeasure_focus: "Partial-G muscle atrophy prevention and abrasive silica dust mitigation",
        description: "Shackleton Crater south-pole habitat optimized for deep cryogenic shadows and long lunar darkness.",
    },
];

export default function EnvironmentProfileView({
    alertLevel = "normal",
    onProfileChanged,
}: EnvironmentProfileViewProps) {
    const [profiles, setProfiles] = useState<EnvironmentProfile[]>(DEFAULT_PROFILES);
    const [activeProfileId, setActiveProfileId] = useState<string>("mars_base");
    const [isSwitching, setIsSwitching] = useState<boolean>(false);
    const [toastMessage, setToastMessage] = useState<string | null>(null);
    const [lastSynced, setLastSynced] = useState<string>("Just now");

    const currentProfile = profiles.find((p) => p.id === activeProfileId) || profiles[0];

    // Fetch live environment configuration
    useEffect(() => {
        let isMounted = true;
        const fetchProfiles = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/environment");
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        if (data.all_profiles) setProfiles(data.all_profiles);
                        if (data.active_profile) setActiveProfileId(data.active_profile.id);
                        setLastSynced(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
                    }
                }
            } catch {
                // Offline tolerance
            }
        };

        fetchProfiles();
        return () => {
            isMounted = false;
        };
    }, []);

    const handleSwitchProfile = async (profId: string) => {
        setIsSwitching(true);
        setActiveProfileId(profId);
        const selected = profiles.find((p) => p.id === profId);

        try {
            const res = await fetch("http://127.0.0.1:8000/api/v1/environment/switch", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ profile_id: profId }),
            });
            if (res.ok) {
                const data = await res.json();
                setToastMessage(`Switched environment to ${data.active_profile.name}`);
                if (onProfileChanged) onProfileChanged(data.active_profile);
            }
        } catch {
            setToastMessage(`Offline switch: ${selected?.name}`);
            if (selected && onProfileChanged) onProfileChanged(selected);
        } finally {
            setIsSwitching(false);
            setTimeout(() => setToastMessage(null), 3000);
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
                            🌍
                        </span>
                        <h1 style={{ margin: 0, fontSize: "20px", fontWeight: 700, color: "#f8fafc", letterSpacing: "0.02em" }}>
                            Environment Profile Switch
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
                            Active: {currentProfile.name}
                        </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "13px", color: "#94a3b8", maxWidth: "680px", lineHeight: 1.5 }}>
                        Select the operating habitat context. Dynamically recalibrates gravity acceleration, atmospheric gas composition,
                        diurnal chronobiology, and personalized physiological baseline thresholds.
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <StatusBadge level={alertLevel} size="md" />
                </div>
            </div>

            {/* Notification Toast */}
            {toastMessage && (
                <div
                    style={{
                        background: "rgba(0, 158, 115, 0.2)",
                        border: "1px solid rgba(0, 158, 115, 0.5)",
                        borderRadius: "10px",
                        padding: "10px 18px",
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "#86efac",
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                    }}
                >
                    <span>✓ {toastMessage}</span>
                </div>
            )}

            {/* Profiles Selector Cards */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "14px",
                }}
            >
                {profiles.map((p) => {
                    const isSelected = activeProfileId === p.id;
                    return (
                        <div
                            key={p.id}
                            onClick={() => handleSwitchProfile(p.id)}
                            style={{
                                background: isSelected
                                    ? "linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(0, 114, 178, 0.2) 100%)"
                                    : "rgba(15, 23, 42, 0.7)",
                                border: isSelected ? "2px solid #0072b2" : "1px solid rgba(255, 255, 255, 0.08)",
                                borderRadius: "14px",
                                padding: "16px",
                                cursor: "pointer",
                                display: "flex",
                                flexDirection: "column",
                                gap: "8px",
                                transition: "all 0.2s ease",
                                boxShadow: isSelected ? "0 0 20px rgba(0, 114, 178, 0.3)" : "none",
                            }}
                        >
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontSize: "24px" }}>{p.icon}</span>
                                <span
                                    style={{
                                        fontSize: "11px",
                                        fontFamily: "monospace",
                                        fontWeight: 700,
                                        color: isSelected ? "#009e73" : "#64748b",
                                    }}
                                >
                                    {isSelected ? "● ACTIVE" : "Select"}
                                </span>
                            </div>

                            <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "#f8fafc" }}>
                                {p.name}
                            </h3>

                            <span style={{ fontSize: "12px", color: "#70b6ff", fontWeight: 600, fontFamily: "monospace" }}>
                                {p.gravity_label}
                            </span>
                        </div>
                    );
                })}
            </div>

            {/* Active Profile Telemetry Dashboard & Baseline Adjustment */}
            <div
                style={{
                    background: "rgba(15, 23, 42, 0.85)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: "16px",
                    padding: "26px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "20px",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                    <div>
                        <span style={{ fontSize: "11px", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                            Active Habitat Specification
                        </span>
                        <h2 style={{ margin: "2px 0 0 0", fontSize: "18px", fontWeight: 700, color: "#f8fafc" }}>
                            {currentProfile.icon} {currentProfile.name}
                        </h2>
                    </div>

                    <div style={{ display: "flex", gap: "8px" }}>
                        <span
                            style={{
                                padding: "4px 10px",
                                borderRadius: "6px",
                                fontSize: "11px",
                                fontWeight: 700,
                                fontFamily: "monospace",
                                background: "rgba(0, 114, 178, 0.15)",
                                color: "#70b6ff",
                                border: "1px solid rgba(0, 114, 178, 0.35)",
                            }}
                        >
                            {currentProfile.gravity_label}
                        </span>
                    </div>
                </div>

                <p style={{ margin: 0, fontSize: "13px", color: "#cbd5e1", lineHeight: 1.5 }}>
                    {currentProfile.description}
                </p>

                {/* 4 Environmental Telemetry Metrics */}
                <div
                    style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: "14px",
                    }}
                >
                    {/* Metric 1: Gravity Acceleration */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "10px",
                            padding: "14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                        }}
                    >
                        <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                            Gravity Constant (g)
                        </span>
                        <strong style={{ fontSize: "20px", fontFamily: "monospace", color: "#f8fafc" }}>
                            {currentProfile.gravity_g.toFixed(3)} G
                        </strong>
                        <span style={{ fontSize: "11px", color: "#70b6ff" }}>{currentProfile.gravity_label}</span>
                    </div>

                    {/* Metric 2: Ambient O2 Partial Pressure */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "10px",
                            padding: "14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                        }}
                    >
                        <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                            Ambient Oxygen (ppO2)
                        </span>
                        <strong style={{ fontSize: "20px", fontFamily: "monospace", color: "#009e73" }}>
                            {currentProfile.ambient_o2_kpa} kPa
                        </strong>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>Normoxic partial pressure</span>
                    </div>

                    {/* Metric 3: Ambient CO2 Scrubber Level */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "10px",
                            padding: "14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                        }}
                    >
                        <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                            Carbon Dioxide (ppCO2)
                        </span>
                        <strong style={{ fontSize: "20px", fontFamily: "monospace", color: "#e69f00" }}>
                            {currentProfile.ambient_co2_mmhg} mmHg
                        </strong>
                        <span style={{ fontSize: "11px", color: "#94a3b8" }}>CDRA scrubber threshold &lt;5.0</span>
                    </div>

                    {/* Metric 4: Adjusted Normal Baseline */}
                    <div
                        style={{
                            background: "rgba(255, 255, 255, 0.03)",
                            border: "1px solid rgba(255, 255, 255, 0.06)",
                            borderRadius: "10px",
                            padding: "14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                        }}
                    >
                        <span style={{ fontSize: "11px", color: "#94a3b8", textTransform: "uppercase" }}>
                            Personal Baseline Band
                        </span>
                        <strong style={{ fontSize: "20px", fontFamily: "monospace", color: "#009e73" }}>
                            {currentProfile.baseline_hr_low} – {currentProfile.baseline_high} bpm
                        </strong>
                        <span style={{ fontSize: "11px", color: "#70b6ff" }}>Calibrated to {currentProfile.gravity_g}G</span>
                    </div>
                </div>

                {/* Radiation Context & Diurnal Chronobiology */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                    <div
                        style={{
                            background: "rgba(0, 0, 0, 0.3)",
                            borderRadius: "10px",
                            padding: "14px",
                            border: "1px solid rgba(255, 255, 255, 0.05)",
                        }}
                    >
                        <strong style={{ fontSize: "12px", color: "#f8fafc", display: "block", marginBottom: "4px" }}>
                            🛡️ Radiation Shielding Context:
                        </strong>
                        <span style={{ fontSize: "12px", color: "#cbd5e1" }}>
                            {currentProfile.radiation_context}
                        </span>
                    </div>

                    <div
                        style={{
                            background: "rgba(0, 0, 0, 0.3)",
                            borderRadius: "10px",
                            padding: "14px",
                            border: "1px solid rgba(255, 255, 255, 0.05)",
                        }}
                    >
                        <strong style={{ fontSize: "12px", color: "#f8fafc", display: "block", marginBottom: "4px" }}>
                            ⏱️ Diurnal Chronobiology:
                        </strong>
                        <span style={{ fontSize: "12px", color: "#cbd5e1" }}>
                            {currentProfile.diurnal_cycle}
                        </span>
                    </div>
                </div>
            </div>

            {/* Offline-Tolerant Status Row */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "rgba(255, 255, 255, 0.02)",
                    borderRadius: "8px",
                    fontSize: "11px",
                    color: "#64748b",
                    fontFamily: "monospace",
                }}
            >
                <span>NASA Multilateral Environment Specification • Offline-Tolerant Cached</span>
                <span>Last Synced: {lastSynced}</span>
            </div>

            {/* Universal Footer (Global Rule 3) */}
            <DisclaimerFooter />
        </div>
    );
}
