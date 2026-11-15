"use client";

import React from "react";

interface DisclaimerFooterProps {
    lastSynced?: string;
    isOffline?: boolean;
    className?: string;
}

export default function DisclaimerFooter({
    lastSynced = "Just now",
    isOffline = false,
    className = "",
}: DisclaimerFooterProps) {
    return (
        <footer
            className={className}
            style={{
                marginTop: "auto",
                padding: "18px 24px",
                borderTop: "1px solid var(--line, rgba(233,228,223,0.16))",
                background: "transparent",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
                fontSize: "11px",
                color: "var(--muted, rgba(236,232,227,0.55))",
                fontFamily: "var(--font-mono, monospace)",
                textTransform: "uppercase",
                letterSpacing: "0.12em",
            }}
        >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                    style={{
                        display: "inline-block",
                        width: "6px",
                        height: "6px",
                        borderRadius: "1px",
                        backgroundColor: isOffline ? "var(--warn, #FFB84D)" : "var(--cool, #8FB8E8)",
                    }}
                />
                <span>
                    {isOffline ? "Telemetry Degraded (Cache Active)" : "Telemetry Active"}
                    {" · "}
                    Synced: <strong style={{ color: "var(--text, #ECE8E3)", fontWeight: 600 }}>{lastSynced}</strong>
                </span>
            </div>

            <div
                style={{
                    padding: "3px 8px",
                    borderRadius: "2px",
                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    color: "var(--muted, rgba(236,232,227,0.55))",
                    fontSize: "11px",
                    letterSpacing: "0.14em",
                }}
            >
                Simulated data. Decision support, not a medical device.
            </div>
        </footer>
    );
}
