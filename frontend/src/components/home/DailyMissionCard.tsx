"use client";

import React, { useState, useEffect } from "react";
import { StatusLevel } from "../common/StatusBadge";

export interface Quest {
    id: string;
    title: string;
    targetText: string;
    currentValue: number;
    targetValue: number;
    unit: string;
    consequence: string;
    xp: number;
    evidence: "established" | "emerging";
    isCarriedOver?: boolean;
    isCompleted?: boolean;
}

interface DailyMissionCardProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onViewAllQuests?: () => void;
    className?: string;
}

export default function DailyMissionCard({
    alertLevel = "normal",
    gamificationEnabled = true,
    onViewAllQuests,
    className = "",
}: DailyMissionCardProps) {
    const isAlertState = alertLevel === "watch" || alertLevel === "act" || alertLevel === "call_ground";
    const showCelebration = gamificationEnabled && !isAlertState;

    const [quests, setQuests] = useState<Quest[]>([
        {
            id: "ared_exercise",
            title: "ARED Resistance Training",
            targetText: "2.5 / 2.5 h this week",
            currentValue: 2.5,
            targetValue: 2.5,
            unit: "hours",
            consequence: "Essential to prevent 1% monthly bone mineral loss in zero-G.",
            xp: 50,
            evidence: "established",
            isCompleted: true,
        },
        {
            id: "hydration_target",
            title: "Electrolyte Hydration Intake",
            targetText: "2.8 / 3.0 L today",
            currentValue: 2.8,
            targetValue: 3.0,
            unit: "liters",
            consequence: "Counteracts cephalad fluid shift and prevents renal stone formation.",
            xp: 30,
            evidence: "established",
            isCompleted: false,
        },
        {
            id: "cognitive_vigilance",
            title: "PVT Cognitive Reaction Test",
            targetText: "Carries over from Sol 40",
            currentValue: 0.5,
            targetValue: 1.0,
            unit: "session",
            consequence: "Verifies high-speed mental response before orbital hatch EVA.",
            xp: 40,
            evidence: "emerging",
            isCarriedOver: true,
            isCompleted: false,
        },
    ]);

    const [loggingId, setLoggingId] = useState<string | null>(null);

    useEffect(() => {
        const fetchQuests = async () => {
            try {
                const res = await fetch("http://127.0.0.1:8000/api/v1/quests");
                if (res.ok) {
                    const data = await res.json();
                    setQuests(
                        data.map((d: any) => ({
                            id: d.id,
                            title: d.title,
                            targetText: d.target_text,
                            currentValue: d.current_value,
                            targetValue: d.target_value,
                            unit: d.unit,
                            consequence: d.consequence,
                            xp: d.xp,
                            evidence: d.evidence,
                            isCarriedOver: d.is_carried_over,
                            isCompleted: d.is_completed,
                        }))
                    );
                }
            } catch {
                // Keep local cache
            }
        };
        fetchQuests();
    }, []);

    const handleLog = async (questId: string) => {
        if (loggingId) return;
        setLoggingId(questId);

        try {
            const res = await fetch(`http://127.0.0.1:8000/api/v1/quests/${questId}/log`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({}),
            });

            if (res.ok) {
                const data = await res.json();
                setQuests((prev) =>
                    prev.map((q) =>
                        q.id === questId
                            ? {
                                  ...q,
                                  currentValue: data.current_value,
                                  isCompleted: data.ring_closed,
                              }
                            : q
                    )
                );
            }
        } catch {
            setQuests((prev) =>
                prev.map((q) => (q.id === questId ? { ...q, isCompleted: true, currentValue: q.targetValue } : q))
            );
        } finally {
            setLoggingId(null);
        }
    };

    const completedCount = quests.filter((q) => q.isCompleted).length;

    return (
        <section
            className={className}
            style={{
                background: "var(--surface, rgba(6,8,14,0.86))",
                borderRadius: "2px",
                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                gap: "24px",
                boxShadow: "none",
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                    <h3 style={{ margin: 0, fontSize: "16px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "-0.01em" }}>
                        Daily Mission Quests
                    </h3>
                    <p style={{ margin: "2px 0 0 0", fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", letterSpacing: "0.06em" }}>
                        Countermeasure routines · 3 active objectives
                    </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    {showCelebration && (
                        <span
                            style={{
                                fontSize: "11px",
                                fontFamily: "var(--font-mono, monospace)",
                                letterSpacing: "0.08em",
                                textTransform: "uppercase",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                color: "var(--cool, #8FB8E8)",
                                padding: "3px 8px",
                                borderRadius: "2px",
                                fontWeight: 500,
                            }}
                        >
                            +120 XP
                        </span>
                    )}

                    {onViewAllQuests && (
                        <button
                            type="button"
                            onClick={onViewAllQuests}
                            style={{
                                background: "transparent",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                color: "var(--text, #ECE8E3)",
                                fontSize: "11px",
                                fontFamily: "var(--font-mono, monospace)",
                                letterSpacing: "0.14em",
                                textTransform: "uppercase",
                                cursor: "pointer",
                                padding: "4px 8px",
                                borderRadius: "2px",
                            }}
                        >
                            View All →
                        </button>
                    )}
                </div>
            </div>

            {/* Overall Missions Progress Bar */}
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                    <span style={{ color: "var(--muted, rgba(236,232,227,0.55))" }}>Daily Completion</span>
                    <span style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>
                        {completedCount} of {quests.length} completed
                    </span>
                </div>
                <div style={{ width: "100%", height: "3px", background: "var(--line, rgba(233,228,223,0.16))" }}>
                    <div
                        style={{
                            width: `${(completedCount / Math.max(1, quests.length)) * 100}%`,
                            height: "100%",
                            background: "var(--accent, #FF4D5A)",
                            transition: "width 0.4s ease",
                        }}
                    />
                </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {quests.map((q) => {
                    const pct = Math.min(100, Math.round((q.currentValue / q.targetValue) * 100));
                    const isLogging = loggingId === q.id;

                    return (
                        <div
                            key={q.id}
                            style={{
                                padding: "14px 16px",
                                borderRadius: "2px",
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                display: "flex",
                                alignItems: "center",
                                gap: "16px",
                            }}
                        >
                            {/* Quest Progress Indicator */}
                            <div style={{ width: "42px", height: "42px", flexShrink: 0, display: "grid", placeItems: "center", border: "1px solid var(--line, rgba(233,228,223,0.16))", borderRadius: "2px", background: "var(--bg, #030307)" }}>
                                <span style={{ fontSize: "11px", fontWeight: 700, color: q.isCompleted ? "var(--cool, #8FB8E8)" : "var(--accent, #FF4D5A)", fontFamily: "var(--font-mono, monospace)" }}>
                                    {pct}%
                                </span>
                            </div>

                            {/* Quest Details */}
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
                                    <h4 style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.06em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                        {q.title}
                                    </h4>

                                    {showCelebration && (
                                        <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                            +{q.xp} XP
                                        </span>
                                    )}
                                </div>

                                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "4px" }}>
                                    <span style={{ fontSize: "11px", color: q.isCarriedOver ? "var(--warn, #FFB84D)" : "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                                        {q.currentValue} / {q.targetValue} {q.unit}
                                    </span>
                                    {q.isCarriedOver && !q.isCompleted && (
                                        <span style={{ fontSize: "10px", border: "1px solid var(--warn, #FFB84D)", color: "var(--warn, #FFB84D)", padding: "1px 5px", borderRadius: "2px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                            Carries over
                                        </span>
                                    )}
                                    {q.isCompleted && (
                                        <span style={{ fontSize: "10px", border: "1px solid var(--cool, #8FB8E8)", color: "var(--cool, #8FB8E8)", padding: "1px 5px", borderRadius: "2px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                                            Completed
                                        </span>
                                    )}
                                </div>

                                <p style={{ margin: "6px 0 0 0", fontSize: "12px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.5, fontFamily: "var(--font-mono, monospace)" }}>
                                    {q.consequence}
                                </p>
                            </div>

                            {/* Primary button: solid coral with near-black text, 2px radius, uppercase mono 12px */}
                            <button
                                type="button"
                                onClick={() => handleLog(q.id)}
                                disabled={q.isCompleted || isLogging}
                                style={{
                                    padding: "8px 14px",
                                    borderRadius: "2px",
                                    border: q.isCompleted ? "1px solid var(--line, rgba(233,228,223,0.16))" : "none",
                                    background: q.isCompleted ? "transparent" : "var(--accent, #FF4D5A)",
                                    color: q.isCompleted ? "var(--cool, #8FB8E8)" : "var(--accent-ink, #030307)",
                                    fontSize: "12px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    fontWeight: 600,
                                    letterSpacing: "0.14em",
                                    textTransform: "uppercase",
                                    cursor: q.isCompleted || isLogging ? "default" : "pointer",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {isLogging ? "Logging..." : q.isCompleted ? "Logged" : "Log it"}
                            </button>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}
