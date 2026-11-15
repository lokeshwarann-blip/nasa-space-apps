"use client";

import React, { useState } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

export interface AlertData {
    id: string;
    level: StatusLevel;
    title: string;
    reason: string;
    nextStep: string;
    timestamp: string;
}

interface AlertBannerProps {
    alert: AlertData | null;
    onCallGround?: () => void;
}

export default function AlertBanner({ alert, onCallGround }: AlertBannerProps) {
    const [callInitiated, setCallInitiated] = useState(false);

    if (!alert || alert.level === "normal") {
        return null;
    }

    const showCallGround = alert.level === "act" || alert.level === "call_ground";

    const handleCall = () => {
        setCallInitiated(true);
        if (onCallGround) onCallGround();
    };

    const accentColor = alert.level === "watch" ? "var(--warn, #FFB84D)" : "var(--accent, #FF4D5A)";

    return (
        <section
            aria-live="assertive"
            style={{
                borderRadius: "2px",
                padding: "16px 20px",
                marginBottom: "20px",
                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                borderLeft: `3px solid ${accentColor}`,
                backgroundColor: "var(--surface, rgba(6,8,14,0.86))",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
            }}
        >
            <div style={{ display: "flex", alignItems: "flex-start", gap: "14px", flex: "1 1 320px" }}>
                <StatusBadge level={alert.level} size="md" />

                <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
                        <h4 style={{ margin: 0, fontSize: "13px", fontWeight: 700, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                            {alert.title}
                        </h4>
                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>
                            {alert.timestamp}
                        </span>
                    </div>

                    <p style={{ margin: "0 0 6px 0", fontSize: "12px", color: "var(--muted, rgba(236,232,227,0.55))", lineHeight: 1.6, fontFamily: "var(--font-mono, monospace)" }}>
                        {alert.reason}
                    </p>

                    <div style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", display: "flex", alignItems: "center", gap: "6px", fontFamily: "var(--font-mono, monospace)" }}>
                        <strong style={{ color: "var(--text, #ECE8E3)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Next step:</strong>
                        <span>{alert.nextStep}</span>
                    </div>
                </div>
            </div>

            {showCallGround && (
                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                    <button
                        type="button"
                        onClick={handleCall}
                        disabled={callInitiated}
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "8px",
                            backgroundColor: callInitiated ? "var(--surface-2, rgba(255,255,255,0.04))" : "var(--accent, #FF4D5A)",
                            color: callInitiated ? "var(--muted, rgba(236,232,227,0.55))" : "var(--accent-ink, #030307)",
                            border: callInitiated ? "1px solid var(--line, rgba(233,228,223,0.16))" : "none",
                            borderRadius: "2px",
                            padding: "8px 14px",
                            fontFamily: "var(--font-mono, monospace)",
                            fontSize: "12px",
                            fontWeight: 600,
                            letterSpacing: "0.14em",
                            textTransform: "uppercase",
                            cursor: callInitiated ? "default" : "pointer",
                        }}
                    >
                        <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                            <polygon points="5,1.5 11,1.5 14.5,5 14.5,11 11,14.5 5,14.5 1.5,11 1.5,5" fill="none" stroke="currentColor" strokeWidth="1.8" />
                        </svg>
                        {callInitiated ? "Flight Surgeon Alerted" : "Call Ground"}
                    </button>
                </div>
            )}
        </section>
    );
}
