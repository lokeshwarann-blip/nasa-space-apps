"use client";

import React from "react";

export type StatusLevel = "normal" | "watch" | "act" | "call_ground";

interface StatusBadgeProps {
    level: StatusLevel;
    label?: string;
    size?: "sm" | "md" | "lg";
    className?: string;
    style?: React.CSSProperties;
}

export const STATUS_CONFIG: Record<
    StatusLevel,
    {
        label: string;
        color: string;
        bg: string;
        border: string;
        shapeName: string;
        iconSvg: React.ReactNode;
    }
> = {
    normal: {
        label: "Ready",
        color: "var(--cool, #8FB8E8)",
        bg: "transparent",
        border: "1px solid var(--cool, #8FB8E8)",
        shapeName: "Circle-Check",
        iconSvg: (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="8" cy="8" r="7" />
                <path d="M5 8.5L7 10.5L11 6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        ),
    },
    watch: {
        label: "Watch",
        color: "var(--warn, #FFB84D)",
        bg: "rgba(255, 184, 77, 0.12)",
        border: "1px solid var(--warn, #FFB84D)",
        shapeName: "Triangle",
        iconSvg: (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M8 2L15 14H1L8 2Z" strokeLinejoin="round" />
                <line x1="8" y1="6.5" x2="8" y2="9.5" strokeLinecap="round" />
                <circle cx="8" cy="12" r="0.9" fill="currentColor" stroke="none" />
            </svg>
        ),
    },
    act: {
        label: "Act",
        color: "var(--accent-ink, #030307)",
        bg: "var(--accent, #FF4D5A)",
        border: "1px solid var(--accent, #FF4D5A)",
        shapeName: "Diamond",
        iconSvg: (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M8 1.5L14.5 8L8 14.5L1.5 8L8 1.5Z" strokeLinejoin="round" fill="none" />
                <line x1="8" y1="5.5" x2="8" y2="8.5" strokeLinecap="round" />
                <circle cx="8" cy="11" r="0.9" fill="currentColor" stroke="none" />
            </svg>
        ),
    },
    call_ground: {
        label: "Call Ground",
        color: "var(--accent-ink, #030307)",
        bg: "var(--accent, #FF4D5A)",
        border: "1px solid var(--accent, #FF4D5A)",
        shapeName: "Diamond",
        iconSvg: (
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <polygon points="5,1.5 11,1.5 14.5,5 14.5,11 11,14.5 5,14.5 1.5,11 1.5,5" />
                <line x1="8" y1="5.5" x2="8" y2="9.5" strokeLinecap="round" />
                <circle cx="8" cy="12" r="0.9" fill="currentColor" stroke="none" />
            </svg>
        ),
    },
};

export default function StatusBadge({
    level,
    label,
    size = "md",
    className = "",
    style = {},
}: StatusBadgeProps) {
    const cfg = STATUS_CONFIG[level] || STATUS_CONFIG.normal;
    const text = label || cfg.label;

    const fontSizes = { sm: "11px", md: "11px", lg: "13px" };
    const paddings = { sm: "2px 6px", md: "3px 8px", lg: "4px 10px" };

    return (
        <span
            className={className}
            style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: paddings[size],
                borderRadius: "2px",
                backgroundColor: cfg.bg,
                color: cfg.color,
                border: cfg.border,
                fontFamily: "var(--font-mono, monospace)",
                fontSize: fontSizes[size],
                fontWeight: 500,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                lineHeight: 1,
                whiteSpace: "nowrap",
                ...style,
            }}
            title={`Status: ${text} (${cfg.shapeName})`}
        >
            <span style={{ display: "inline-flex" }}>
                {cfg.iconSvg}
            </span>
            <span>{text}</span>
        </span>
    );
}
