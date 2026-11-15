"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface TeamStreakViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
    onNavigateToQuests?: () => void;
}

export default function TeamStreakView({
    alertLevel = "normal",
    gamificationEnabled = true,
    onToggleGamification,
}: TeamStreakViewProps) {
    const isAlertState = alertLevel === "watch" || alertLevel === "act" || alertLevel === "call_ground";
    const showCelebration = gamificationEnabled && !isAlertState;

    const [teamStreak, setTeamStreak] = useState<number>(13);
    const [freezeDaysTotal, setFreezeDaysTotal] = useState<number>(2);
    const [freezeDaysRemaining, setFreezeDaysRemaining] = useState<number>(1);
    const [currentHours, setCurrentHours] = useState<number>(30.8);
    const [targetHours, setTargetHours] = useState<number>(35.0);
    const [ringsClosed, setRingsClosed] = useState<number>(6);
    const [ringsTotal, setRingsTotal] = useState<number>(7);
    const [lastSynced, setLastSynced] = useState<string>("Just now");

    const goalPct = Math.min(100, Math.round((currentHours / targetHours) * 100));

    // Fetch live backend data
    useEffect(() => {
        let isMounted = true;
        const fetchTeam = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/team/streak");
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted) {
                        setTeamStreak(data.team_streak_sols);
                        setFreezeDaysTotal(data.freeze_days_total);
                        setFreezeDaysRemaining(data.freeze_days_remaining);
                        setCurrentHours(data.shared_goal_current_hours);
                        setTargetHours(data.shared_goal_target_hours);
                        setRingsClosed(data.rings_closed);
                        setRingsTotal(data.rings_total);
                        setLastSynced(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
                    }
                }
            } catch {
                // Offline tolerance
            }
        };

        fetchTeam();
        return () => {
            isMounted = false;
        };
    }, []);

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "22px", width: "100%" }}>
            {/* Header Banner */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: "14px",
                    background: "var(--surface)",
                    border: "1px solid var(--line)",
                    borderRadius: "2px",
                    padding: "20px 24px",
                }}
            >
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span
                            style={{
                                fontSize: "11px",
                                background: "var(--surface-2)",
                                padding: "4px 8px",
                                borderRadius: "2px",
                                border: "1px solid var(--line)",
                                fontFamily: "var(--font-mono)",
                                color: "var(--cool)",
                                textTransform: "uppercase",
                                letterSpacing: "0.12em",
                            }}
                        >
                            [SHARED TELEMETRY]
                        </span>
                        <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "-0.01em", color: "var(--text)", fontFamily: "var(--font-display), sans-serif" }}>
                            Crew Collective Streak & Shared Goals
                        </h2>
                        <span
                            style={{
                                padding: "2px 6px",
                                borderRadius: "2px",
                                fontSize: "10px",
                                fontWeight: 600,
                                fontFamily: "var(--font-mono)",
                                background: "transparent",
                                color: "var(--muted)",
                                border: "1px solid var(--line)",
                                textTransform: "uppercase",
                                letterSpacing: "0.1em",
                            }}
                        >
                            Non-Competitive · Zero Rankings
                        </span>
                    </div>
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--muted)", maxWidth: "680px", lineHeight: 1.6, fontFamily: "var(--font-mono)" }}>
                        Collective mission health milestone tracking. Focuses on shared habitat synchronization without individual comparison.
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <StatusBadge level="normal" label="Collective On Track" size="md" />
                    {onToggleGamification && (
                        <button
                            onClick={onToggleGamification}
                            style={{
                                background: "transparent",
                                border: "1px solid var(--line)",
                                color: gamificationEnabled ? "var(--text)" : "var(--muted)",
                                borderRadius: "2px",
                                padding: "6px 12px",
                                fontSize: "11px",
                                textTransform: "uppercase",
                                letterSpacing: "0.12em",
                                fontFamily: "var(--font-mono)",
                                cursor: "pointer",
                            }}
                        >
                            {gamificationEnabled ? "Streaks Visible" : "Minimalist View"}
                        </button>
                    )}
                </div>
            </div>

            {/* Streak & Freeze Days Row */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                    gap: "16px",
                }}
            >
                {/* 1. Team Streak Counter */}
                <div
                    style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                        borderRadius: "2px",
                        padding: "20px 24px",
                        display: "flex",
                        alignItems: "center",
                        gap: "18px",
                    }}
                >
                    <div>
                        <span style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "var(--font-mono)" }}>
                            Active Crew Streak
                        </span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
                            <span style={{ fontSize: "32px", fontWeight: 800, fontFamily: "var(--font-display)", color: "var(--text)" }}>
                                {teamStreak}
                            </span>
                            <span style={{ fontSize: "12px", color: "var(--accent)", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "var(--font-mono)" }}>Consecutive Sols</span>
                        </div>
                    </div>
                </div>

                {/* 2. Freeze Days Badge */}
                <div
                    style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                        borderRadius: "2px",
                        padding: "20px 24px",
                        display: "flex",
                        alignItems: "center",
                        gap: "18px",
                    }}
                >
                    <div>
                        <span style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "var(--font-mono)" }}>
                            Operational Freeze Buffer
                        </span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
                            <span style={{ fontSize: "32px", fontWeight: 800, fontFamily: "var(--font-display)", color: "var(--cool)" }}>
                                {freezeDaysRemaining} / {freezeDaysTotal}
                            </span>
                            <span style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "var(--font-mono)" }}>Freeze Sols Left</span>
                        </div>
                    </div>
                </div>

                {/* 3. Daily Rings Closed */}
                <div
                    style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                        borderRadius: "2px",
                        padding: "20px 24px",
                        display: "flex",
                        alignItems: "center",
                        gap: "18px",
                    }}
                >
                    <div>
                        <span style={{ fontSize: "10px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "var(--font-mono)" }}>
                            Weekly Countermeasure Rings
                        </span>
                        <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "4px" }}>
                            <span style={{ fontSize: "32px", fontWeight: 800, fontFamily: "var(--font-display)", color: "var(--text)" }}>
                                {ringsClosed} / {ringsTotal}
                            </span>
                            <span style={{ fontSize: "12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: "var(--font-mono)" }}>Rings Closed</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Shared Mission Goal Progress Bar */}
            <div
                style={{
                    background: "var(--surface)",
                    border: "1px solid var(--line)",
                    borderRadius: "2px",
                    padding: "24px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "16px",
                }}
            >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                    <div>
                        <span style={{ fontSize: "10px", color: "var(--cool)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.12em", fontFamily: "var(--font-mono)" }}>
                            Shared Mission Goal • Sol 35 to Sol 42
                        </span>
                        <h3 style={{ margin: "4px 0 0 0", fontSize: "15px", fontWeight: 800, textTransform: "uppercase", color: "var(--text)", fontFamily: "var(--font-display)" }}>
                            Expedition Weekly Aerobic & Resistance Target
                        </h3>
                    </div>

                    <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
                        <span style={{ fontSize: "24px", fontWeight: 800, fontFamily: "var(--font-mono)", color: "var(--accent)" }}>
                            {currentHours.toFixed(1)}
                        </span>
                        <span style={{ fontSize: "12px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>/ {targetHours.toFixed(1)} hrs</span>
                        <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--cool)", marginLeft: "6px", fontFamily: "var(--font-mono)" }}>
                            ({goalPct}%)
                        </span>
                    </div>
                </div>

                {/* Unified Progress Bar */}
                <div
                    style={{
                        height: "4px",
                        background: "var(--line)",
                        borderRadius: "1px",
                        overflow: "hidden",
                    }}
                >
                    <div
                        style={{
                            height: "100%",
                            width: `${goalPct}%`,
                            background: "var(--accent)",
                            transition: "width 0.4s ease",
                        }}
                    />
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                    <span>Progress: 30.8 hrs completed collectively across station ARED, T2 & CEVIS</span>
                    <span style={{ color: "var(--cool)" }}>4.2 hrs remaining to target</span>
                </div>
            </div>

            {/* Zero-Ranking Policy & Carries Over Rule (Global Rule 5) */}
            <div
                style={{
                    background: "var(--surface)",
                    border: "1px solid var(--line)",
                    borderRadius: "2px",
                    padding: "16px 20px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                }}
            >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <strong style={{ fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--cool)", fontFamily: "var(--font-mono)" }}>
                        [NASA Behavioral Health Policy] Non-Competitive Crew Dynamics
                    </strong>
                </div>
                <p style={{ margin: 0, fontSize: "12px", color: "var(--text)", lineHeight: 1.6, fontFamily: "var(--font-mono)", opacity: 0.85 }}>
                    This system enforces strictly zero leaderboards, peer rankings, or individual comparison tables.
                    Missed countermeasure sessions never produce failure warnings or red shame banners; incomplete tasks are automatically labeled
                    <strong> &ldquo;Carries over to Sol 42&rdquo;</strong> to preserve operational cohesion and psychological safety.
                </p>
            </div>

            {/* Offline-Tolerant Status Row */}
            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px 12px",
                    background: "transparent",
                    borderRadius: "2px",
                    fontSize: "11px",
                    color: "var(--muted)",
                    fontFamily: "var(--font-mono)",
                    borderTop: "1px solid var(--line)",
                }}
            >
                <span>NASA Crew Teamwork Engine • Offline-Tolerant Cached</span>
                <span>Last Synced: {lastSynced}</span>
            </div>
        </div>
    );
}
