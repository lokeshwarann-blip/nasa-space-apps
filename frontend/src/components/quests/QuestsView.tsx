"use client";

import React, { useState, useEffect } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

export interface Quest {
    id: string;
    title: string;
    category: string;
    target_text: string;
    current_value: number;
    target_value: number;
    unit: string;
    consequence: string;
    xp: number;
    evidence: "established" | "emerging" | "illustrative";
    is_carried_over: boolean;
    is_completed: boolean;
}

export interface WeeklySummary {
    rings_closed: number;
    rings_total: number;
    team_streak_sols: number;
    freeze_days_remaining: number;
    shared_goal_pct: number;
}

interface QuestsViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
}

export default function QuestsView({
    alertLevel = "normal",
    gamificationEnabled = true,
    onToggleGamification,
}: QuestsViewProps) {
    const isAlertState = alertLevel === "watch" || alertLevel === "act" || alertLevel === "call_ground";
    // Suppress celebratory effects during alert states (Global Rule 4)
    const showCelebration = gamificationEnabled && !isAlertState;

    const [quests, setQuests] = useState<Quest[]>([
        {
            id: "ared_exercise",
            title: "ARED Resistance Training",
            category: "Musculoskeletal",
            target_text: "2.5 / 2.5 h this week",
            current_value: 2.5,
            target_value: 2.5,
            unit: "hours",
            consequence: "Protects L3–L5 trabecular bone density and reduces 1% monthly calcium loss in zero-G.",
            xp: 50,
            evidence: "established",
            is_carried_over: false,
            is_completed: true,
        },
        {
            id: "hydration_target",
            title: "Electrolyte Hydration Intake",
            category: "Vascular",
            target_text: "2.8 / 3.0 L today",
            current_value: 2.8,
            target_value: 3.0,
            unit: "liters",
            consequence: "Maintains plasma volume and prevents renal stone formation under cephalad fluid shift.",
            xp: 30,
            evidence: "established",
            is_carried_over: false,
            is_completed: false,
        },
        {
            id: "cognitive_vigilance",
            title: "PVT Cognitive Reaction Test",
            category: "Neuro",
            target_text: "Carries over from Sol 40",
            current_value: 0.5,
            target_value: 1.0,
            unit: "session",
            consequence: "Verifies high-speed psychomotor vigilance (PVT) reaction time before suited orbital EVA.",
            xp: 40,
            evidence: "emerging",
            is_carried_over: true,
            is_completed: false,
        },
    ]);

    const [summary, setSummary] = useState<WeeklySummary>({
        rings_closed: 6,
        rings_total: 7,
        team_streak_sols: 13,
        freeze_days_remaining: 1,
        shared_goal_pct: 88,
    });

    const [loggingId, setLoggingId] = useState<string | null>(null);
    const [rewardToast, setRewardToast] = useState<{
        message: string;
        xpGained: number;
        unlockedTitle?: string;
    } | null>(null);

    // Fetch live quests from API on mount
    useEffect(() => {
        const fetchQuests = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/quests");
                if (res.ok) {
                    const data = await res.json();
                    setQuests(data);
                }
                const sumRes = await fetch("http://127.0.0.1:8000/api/v1/quests/summary");
                if (sumRes.ok) {
                    const sumData = await sumRes.json();
                    setSummary(sumData);
                }
            } catch {
                // Keep resilient offline cache
            }
        };
        fetchQuests();
    }, []);

    // Idempotent Log Quest Handler
    const handleLogQuest = async (questId: string) => {
        if (loggingId) return; // Prevent concurrent requests
        setLoggingId(questId);

        try {
            const res = await fetch(`http://127.0.0.1:8000/api/v1/quests/${questId}/log`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });

            if (res.ok) {
                const data = await res.json();

                // Update local quest state
                setQuests((prev) =>
                    prev.map((q) => {
                        if (q.id === questId) {
                            return {
                                ...q,
                                current_value: data.current_value,
                                is_completed: data.ring_closed,
                            };
                        }
                        return q;
                    })
                );

                if (data.ring_closed) {
                    setSummary((prev) => ({
                        ...prev,
                        rings_closed: Math.min(prev.rings_total, prev.rings_closed + 1),
                        team_streak_sols: data.team_streak,
                        shared_goal_pct: Math.min(100, prev.shared_goal_pct + 6),
                    }));
                }

                if (data.xp_gained > 0 && showCelebration) {
                    setRewardToast({
                        message: data.message,
                        xpGained: data.xp_gained,
                        unlockedTitle: data.unlocked_title,
                    });
                    setTimeout(() => setRewardToast(null), 5000);
                }
            }
        } catch {
            // Offline fallback
            setQuests((prev) =>
                prev.map((q) => (q.id === questId ? { ...q, is_completed: true, current_value: q.target_value } : q))
            );
        } finally {
            setLoggingId(null);
        }
    };

    const evidenceBadges = {
        established: { label: "Established (NASA HRP)", color: "var(--cool)" },
        emerging: { label: "Emerging Research", color: "var(--accent)" },
        illustrative: { label: "Illustrative Flight Model", color: "var(--warn)" },
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Header with Gamification Settings Toggle */}
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
                <div>
                    <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "-0.01em", color: "var(--text)", fontFamily: "var(--font-display), sans-serif" }}>
                        Mission Quests & Countermeasures
                    </h2>
                    <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono), monospace" }}>
                        Active countermeasures · Evidence-graded physiological protocols
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    {onToggleGamification && (
                        <button
                            type="button"
                            onClick={onToggleGamification}
                            style={{
                                background: gamificationEnabled ? "var(--surface-2)" : "transparent",
                                color: gamificationEnabled ? "var(--text)" : "var(--muted)",
                                border: "1px solid var(--line)",
                                padding: "6px 12px",
                                borderRadius: "2px",
                                fontSize: "11px",
                                textTransform: "uppercase",
                                letterSpacing: "0.12em",
                                fontFamily: "var(--font-mono, monospace)",
                                cursor: "pointer",
                            }}
                        >
                            {gamificationEnabled ? "Gamification: ON" : "Gamification: OFF (Quiet Mode)"}
                        </button>
                    )}
                </div>
            </div>

            {/* Instant Reward Banner (Rule 4: Suppressed in alert state) */}
            {rewardToast && showCelebration && (
                <div
                    role="alert"
                    style={{
                        padding: "12px 18px",
                        borderRadius: "2px",
                        background: "var(--surface)",
                        border: "1px solid var(--accent)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span style={{ color: "var(--accent)", fontSize: "14px", fontWeight: 700 }}>[QUEST COMPLETED]</span>
                        <div>
                            <strong style={{ color: "var(--text)", fontSize: "13px", fontFamily: "var(--font-mono)" }}>
                                {rewardToast.message}
                            </strong>
                            {rewardToast.unlockedTitle && (
                                <div style={{ fontSize: "11px", color: "var(--cool)", marginTop: "2px", fontFamily: "var(--font-mono)" }}>
                                    Unlocked in Codex: <strong>{rewardToast.unlockedTitle}</strong>
                                </div>
                            )}
                        </div>
                    </div>

                    <span
                        style={{
                            fontSize: "13px",
                            fontWeight: 700,
                            color: "var(--accent)",
                            fontFamily: "var(--font-mono, monospace)",
                        }}
                    >
                        +{rewardToast.xpGained} XP
                    </span>
                </div>
            )}

            {/* WEEKLY SUMMARY (Rings Closed + Shared Team Streak, Strictly No Individual Rankings) */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "16px",
                }}
            >
                {/* Rings Closed */}
                <div
                    style={{
                        background: "var(--surface)",
                        borderRadius: "2px",
                        border: "1px solid var(--line)",
                        padding: "18px 20px",
                        display: "flex",
                        alignItems: "center",
                        gap: "18px",
                    }}
                >
                    {/* Ring progress graphic */}
                    <div style={{ position: "relative", width: "56px", height: "56px", flexShrink: 0, display: "grid", placeItems: "center" }}>
                        <svg width="56" height="56" viewBox="0 0 56 56" style={{ transform: "rotate(-90deg)" }}>
                            <circle cx="28" cy="28" r="22" fill="none" stroke="var(--line)" strokeWidth="4" />
                            <circle
                                cx="28"
                                cy="28"
                                r="22"
                                fill="none"
                                stroke="var(--cool)"
                                strokeWidth="4"
                                strokeDasharray={2 * Math.PI * 22}
                                strokeDashoffset={2 * Math.PI * 22 * (1 - summary.rings_closed / summary.rings_total)}
                                strokeLinecap="round"
                            />
                        </svg>
                        <span style={{ position: "absolute", fontSize: "13px", fontWeight: 800, color: "var(--text)", fontFamily: "var(--font-mono, monospace)" }}>
                            {summary.rings_closed}/{summary.rings_total}
                        </span>
                    </div>

                    <div>
                        <h4 style={{ margin: 0, fontSize: "13px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text)" }}>
                            Weekly Rings Closed
                        </h4>
                        <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                            {summary.rings_closed} of {summary.rings_total} countermeasure cycles completed
                        </p>
                    </div>
                </div>

                {/* Team Streak (Shared Goal, No Individual Rankings) */}
                <div
                    style={{
                        background: "var(--surface)",
                        borderRadius: "2px",
                        border: "1px solid var(--line)",
                        padding: "18px 20px",
                        display: "flex",
                        flexDirection: "column",
                        gap: "10px",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <strong style={{ fontSize: "13px", textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text)" }}>
                                Mission Team Streak: {summary.team_streak_sols} Sols
                            </strong>
                        </div>
                        <span style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono, monospace)" }}>
                            {summary.freeze_days_remaining} freeze day remaining
                        </span>
                    </div>

                    {/* Shared Progress Bar */}
                    <div style={{ width: "100%", height: "4px", background: "var(--line)", borderRadius: "1px", overflow: "hidden" }}>
                        <div
                            style={{
                                width: `${summary.shared_goal_pct}%`,
                                height: "100%",
                                background: "var(--accent)",
                            }}
                        />
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                        <span>Collective expedition target</span>
                        <span>{summary.shared_goal_pct}% of mission goal</span>
                    </div>
                </div>
            </div>

            {/* QUESTS LIST */}
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text)" }}>
                    Active Expedition Objectives
                </h3>

                {quests.map((q) => {
                    const pct = Math.min(100, Math.round((q.current_value / q.target_value) * 100));
                    const radius = 22;
                    const circ = 2 * Math.PI * radius;
                    const offset = circ - (pct / 100) * circ;
                    const isLogging = loggingId === q.id;
                    const ev = evidenceBadges[q.evidence] || evidenceBadges.established;

                    return (
                        <div
                            key={q.id}
                            style={{
                                background: "var(--surface)",
                                borderRadius: "2px",
                                border: q.is_completed
                                    ? "1px solid var(--line)"
                                    : q.is_carried_over
                                    ? "1px solid var(--warn)"
                                    : "1px solid var(--line)",
                                padding: "18px 20px",
                                display: "flex",
                                flexWrap: "wrap",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: "16px",
                            }}
                        >
                            <div style={{ display: "flex", alignItems: "center", gap: "18px", flex: "1 1 360px" }}>
                                {/* Big Progress Ring */}
                                <div style={{ position: "relative", width: "50px", height: "50px", flexShrink: 0, display: "grid", placeItems: "center" }}>
                                    <svg width="50" height="50" viewBox="0 0 50 50" style={{ transform: "rotate(-90deg)" }}>
                                        <circle cx="25" cy="25" r={radius} fill="none" stroke="var(--line)" strokeWidth="3" />
                                        <circle
                                            cx="25"
                                            cy="25"
                                            r={radius}
                                            fill="none"
                                            stroke={q.is_completed ? "var(--cool)" : q.is_carried_over ? "var(--warn)" : "var(--accent)"}
                                            strokeWidth="3"
                                            strokeDasharray={circ}
                                            strokeDashoffset={offset}
                                            strokeLinecap="round"
                                            style={{ transition: "stroke-dashoffset 0.6s ease" }}
                                        />
                                    </svg>
                                    <span style={{ position: "absolute", fontSize: "11px", fontWeight: 800, color: "var(--text)", fontFamily: "var(--font-mono, monospace)" }}>
                                        {pct}%
                                    </span>
                                </div>

                                {/* Quest Meta & Consequence */}
                                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                                    <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px" }}>
                                        <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>
                                            {q.title}
                                        </h4>

                                        <span
                                            style={{
                                                fontSize: "10px",
                                                fontFamily: "var(--font-mono, monospace)",
                                                padding: "2px 6px",
                                                borderRadius: "2px",
                                                border: `1px solid ${ev.color}`,
                                                color: ev.color,
                                                textTransform: "uppercase",
                                                letterSpacing: "0.08em",
                                            }}
                                        >
                                            {ev.label}
                                        </span>

                                        {q.is_carried_over && !q.is_completed && (
                                            <span style={{ fontSize: "10px", border: "1px solid var(--warn)", color: "var(--warn)", padding: "2px 6px", borderRadius: "2px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                                Carries over
                                            </span>
                                        )}

                                        {q.is_completed && (
                                            <span style={{ fontSize: "10px", border: "1px solid var(--cool)", color: "var(--cool)", padding: "2px 6px", borderRadius: "2px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                                Ring Closed ✓
                                            </span>
                                        )}
                                    </div>

                                    <div style={{ fontSize: "11px", color: "var(--muted)", fontFamily: "var(--font-mono, monospace)" }}>
                                        Progress: {q.current_value} / {q.target_value} {q.unit}
                                    </div>

                                    <p style={{ margin: 0, fontSize: "12px", color: "var(--text)", lineHeight: 1.5, opacity: 0.85 }}>
                                        {q.consequence}
                                    </p>
                                </div>
                            </div>

                            {/* Action & XP */}
                            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                                {showCelebration && (
                                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--accent)", fontFamily: "var(--font-mono, monospace)" }}>
                                        +{q.xp} XP
                                    </span>
                                )}

                                <button
                                    type="button"
                                    onClick={() => handleLogQuest(q.id)}
                                    disabled={q.is_completed || isLogging}
                                    style={{
                                        padding: "6px 14px",
                                        borderRadius: "2px",
                                        border: q.is_completed ? "1px solid var(--line)" : "none",
                                        background: q.is_completed ? "transparent" : "var(--accent)",
                                        color: q.is_completed ? "var(--muted)" : "var(--accent-ink)",
                                        fontSize: "11px",
                                        fontFamily: "var(--font-mono, monospace)",
                                        fontWeight: 600,
                                        textTransform: "uppercase",
                                        letterSpacing: "0.12em",
                                        cursor: q.is_completed || isLogging ? "default" : "pointer",
                                        transition: "opacity 0.15s ease",
                                    }}
                                >
                                    {isLogging ? "Logging..." : q.is_completed ? "Logged ✓" : "Log it"}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
