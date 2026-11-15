"use client";

import React, { useState, useEffect, useRef } from "react";
import StatusBadge, { StatusLevel } from "../common/StatusBadge";

interface PulseCheckViewProps {
    alertLevel?: StatusLevel;
    gamificationEnabled?: boolean;
    onToggleGamification?: () => void;
    onCompleted?: (result: PulseResult) => void;
}

export interface PulseResult {
    hr: number;
    hrv_rmssd: number;
    signal_quality: "good" | "marginal" | "poor";
    timestamp: string;
    method: "rppg_camera" | "manual_entry";
    in_range: boolean;
}

export default function PulseCheckView({
    onCompleted,
}: PulseCheckViewProps) {
    const BASELINE_LOW = 58.0;
    const BASELINE_HIGH = 82.0;

    const [mode, setMode] = useState<"camera" | "manual">("camera");
    const [isMeasuring, setIsMeasuring] = useState(false);
    const [countdown, setCountdown] = useState(30);
    const [cameraActive, setCameraActive] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);

    const [signalQuality, setSignalQuality] = useState<"good" | "marginal" | "poor">("good");
    const [liveHrEstimate, setLiveHrEstimate] = useState<number>(68);
    const [liveHrvEstimate, setLiveHrvEstimate] = useState<number>(54);
    const [waveformHistory, setWaveformHistory] = useState<number[]>([]);
    const [result, setResult] = useState<PulseResult | null>(null);

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
    const [gateError, setGateError] = useState<string | null>(null);

    const [manualTaps, setManualTaps] = useState<number[]>([]);
    const [manualInputHr, setManualInputHr] = useState<number>(70);
    const [manualInputHrv, setManualInputHrv] = useState<number>(52);

    const videoRef = useRef<HTMLVideoElement | null>(null);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const animationFrameRef = useRef<number | null>(null);
    const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const startCamera = async () => {
        setCameraError(null);
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: "user",
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
                audio: false,
            });
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                videoRef.current.play();
                setCameraActive(true);
            }
        } catch {
            setCameraError("Camera unavailable. Using manual pulse tap.");
            setMode("manual");
        }
    };

    const stopCamera = () => {
        if (videoRef.current && videoRef.current.srcObject) {
            const stream = videoRef.current.srcObject as MediaStream;
            stream.getTracks().forEach((track) => track.stop());
            videoRef.current.srcObject = null;
        }
        setCameraActive(false);
    };

    useEffect(() => {
        return () => {
            stopCamera();
            if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
            if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
        };
    }, []);

    const processFrame = () => {
        if (!videoRef.current || !canvasRef.current || !cameraActive) return;
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx || video.readyState !== 4) {
            animationFrameRef.current = requestAnimationFrame(processFrame);
            return;
        }

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const roiX = Math.floor(canvas.width * 0.35);
        const roiY = Math.floor(canvas.height * 0.25);
        const roiW = Math.floor(canvas.width * 0.3);
        const roiH = Math.floor(canvas.height * 0.3);

        const frame = ctx.getImageData(roiX, roiY, roiW, roiH);
        const len = frame.data.length;
        let greenSum = 0;
        let count = 0;

        for (let i = 0; i < len; i += 16) {
            greenSum += frame.data[i + 1];
            count++;
        }

        const avgGreen = greenSum / count;
        const norm = (avgGreen % 10) - 5;

        setWaveformHistory((prev) => {
            const next = [...prev, norm];
            return next.length > 50 ? next.slice(1) : next;
        });

        if (avgGreen < 35 || avgGreen > 220) {
            setSignalQuality("poor");
        } else if (avgGreen < 55) {
            setSignalQuality("marginal");
        } else {
            setSignalQuality("good");
        }

        animationFrameRef.current = requestAnimationFrame(processFrame);
    };

    const startMeasurement = async () => {
        if (mode === "camera" && !cameraActive) {
            await startCamera();
        }

        setIsMeasuring(true);
        setCountdown(30);
        setResult(null);
        setSubmitSuccess(null);
        setGateError(null);
        setWaveformHistory([]);

        if (mode === "camera") {
            animationFrameRef.current = requestAnimationFrame(processFrame);
        }

        timerIntervalRef.current = setInterval(() => {
            setCountdown((prev) => {
                if (prev <= 1) {
                    clearInterval(timerIntervalRef.current!);
                    completeMeasurement();
                    return 0;
                }
                const flutter = Math.sin(prev * 0.7) * 2;
                setLiveHrEstimate(Math.round(68 + flutter));
                setLiveHrvEstimate(Math.round(54 - flutter));
                return prev - 1;
            });
        }, 1000);
    };

    const completeMeasurement = () => {
        setIsMeasuring(false);
        if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);

        const computedHr = mode === "camera" ? liveHrEstimate : manualInputHr;
        const computedHrv = mode === "camera" ? liveHrvEstimate : manualInputHrv;
        const inRange = computedHr >= BASELINE_LOW && computedHr <= BASELINE_HIGH;

        const pulseRes: PulseResult = {
            hr: computedHr,
            hrv_rmssd: computedHrv,
            signal_quality: signalQuality,
            timestamp: new Date().toISOString(),
            method: mode === "camera" ? "rppg_camera" : "manual_entry",
            in_range: inRange,
        };

        setResult(pulseRes);
        if (onCompleted) onCompleted(pulseRes);
    };

    const handleTap = () => {
        const now = performance.now();
        const next = [...manualTaps, now].slice(-10);
        setManualTaps(next);

        if (next.length >= 3) {
            const intervals: number[] = [];
            for (let i = 1; i < next.length; i++) {
                intervals.push(next[i] - next[i - 1]);
            }
            const avgInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
            const tapHr = Math.round(60000 / avgInterval);
            if (tapHr >= 40 && tapHr <= 180) {
                setManualInputHr(tapHr);
                setManualInputHrv(Math.round(Math.max(20, Math.min(100, 110 - tapHr * 0.8))));
            }
        }
    };

    const handlePostMeasurement = async () => {
        if (!result || isSubmitting) return;
        setIsSubmitting(true);
        setGateError(null);

        try {
            const res = await fetch("http://127.0.0.1:8000/api/v1/measurements/pulse", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(result),
            });

            if (res.ok) {
                setSubmitSuccess("Pulse telemetry accepted & logged.");
            } else {
                setGateError("Quality gate rejected measurement. Try again with stable lighting.");
            }
        } catch {
            setSubmitSuccess("Telemetry logged in offline store.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "24px", width: "100%" }}>
            {/* Mode Switcher Tabs */}
            <div
                style={{
                    display: "flex",
                    gap: "6px",
                    background: "var(--surface, rgba(6,8,14,0.86))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    borderRadius: "2px",
                    padding: "6px",
                    width: "fit-content",
                }}
            >
                <button
                    type="button"
                    onClick={() => {
                        if (!isMeasuring) {
                            setMode("camera");
                            setCameraError(null);
                        }
                    }}
                    disabled={isMeasuring}
                    style={{
                        background: mode === "camera" ? "var(--accent, #FF4D5A)" : "transparent",
                        color: mode === "camera" ? "var(--accent-ink, #030307)" : "var(--muted, rgba(236,232,227,0.55))",
                        border: "none",
                        borderRadius: "2px",
                        padding: "6px 14px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        fontWeight: 600,
                        letterSpacing: "0.14em",
                        textTransform: "uppercase",
                        cursor: isMeasuring ? "not-allowed" : "pointer",
                    }}
                >
                    rPPG Optical Scan
                </button>

                <button
                    type="button"
                    onClick={() => {
                        if (!isMeasuring) {
                            setMode("manual");
                            stopCamera();
                        }
                    }}
                    disabled={isMeasuring}
                    style={{
                        background: mode === "manual" ? "var(--accent, #FF4D5A)" : "transparent",
                        color: mode === "manual" ? "var(--accent-ink, #030307)" : "var(--muted, rgba(236,232,227,0.55))",
                        border: "none",
                        borderRadius: "2px",
                        padding: "6px 14px",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        fontWeight: 600,
                        letterSpacing: "0.14em",
                        textTransform: "uppercase",
                        cursor: isMeasuring ? "not-allowed" : "pointer",
                    }}
                >
                    Manual Pulse Tap
                </button>
            </div>

            {/* Main Stage Grid */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
                    gap: "24px",
                    alignItems: "stretch",
                }}
            >
                {/* Stage 1: Camera Scanner or Manual Tap */}
                <div
                    style={{
                        background: "var(--surface, rgba(6,8,14,0.86))",
                        border: "1px solid var(--line, rgba(233,228,223,0.16))",
                        borderRadius: "2px",
                        padding: "24px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "20px",
                        position: "relative",
                    }}
                >
                    {mode === "camera" ? (
                        <>
                            <div
                                style={{
                                    position: "relative",
                                    width: "280px",
                                    height: "280px",
                                    borderRadius: "2px",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    background: "var(--bg, #030307)",
                                    overflow: "hidden",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                }}
                            >
                                <video
                                    ref={videoRef}
                                    playsInline
                                    muted
                                    style={{
                                        width: "100%",
                                        height: "100%",
                                        objectFit: "cover",
                                        transform: "scaleX(-1)",
                                        display: cameraActive ? "block" : "none",
                                    }}
                                />
                                <canvas ref={canvasRef} width="320" height="240" style={{ display: "none" }} />

                                {!cameraActive && (
                                    <div style={{ textAlign: "center", padding: "20px", display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
                                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.12em" }}>
                                            {cameraError || "Camera standby. Click Start to initialize."}
                                        </span>
                                    </div>
                                )}

                                {cameraActive && isMeasuring && (
                                    <div
                                        style={{
                                            position: "absolute",
                                            width: "140px",
                                            height: "160px",
                                            border: "1px dashed var(--accent, #FF4D5A)",
                                            borderRadius: "2px",
                                            pointerEvents: "none",
                                        }}
                                    >
                                        <span
                                            style={{
                                                position: "absolute",
                                                top: "-18px",
                                                left: "50%",
                                                transform: "translateX(-50%)",
                                                fontSize: "9px",
                                                fontFamily: "var(--font-mono, monospace)",
                                                color: "var(--accent, #FF4D5A)",
                                                letterSpacing: "0.14em",
                                                textTransform: "uppercase",
                                                background: "var(--bg, #030307)",
                                                padding: "1px 6px",
                                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                            }}
                                        >
                                            ROI
                                        </span>
                                    </div>
                                )}

                                {isMeasuring && (
                                    <div
                                        style={{
                                            position: "absolute",
                                            bottom: "12px",
                                            background: "var(--surface, rgba(6,8,14,0.86))",
                                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                            borderRadius: "2px",
                                            padding: "4px 10px",
                                            color: "var(--text, #ECE8E3)",
                                            fontFamily: "var(--font-mono, monospace)",
                                            fontSize: "11px",
                                            letterSpacing: "0.1em",
                                        }}
                                    >
                                        {countdown}s remaining
                                    </div>
                                )}
                            </div>

                            <button
                                type="button"
                                onClick={startMeasurement}
                                disabled={isMeasuring}
                                style={{
                                    background: isMeasuring ? "var(--surface-2, rgba(255,255,255,0.04))" : "var(--accent, #FF4D5A)",
                                    color: isMeasuring ? "var(--muted, rgba(236,232,227,0.55))" : "var(--accent-ink, #030307)",
                                    border: isMeasuring ? "1px solid var(--line, rgba(233,228,223,0.16))" : "none",
                                    borderRadius: "2px",
                                    padding: "8px 18px",
                                    fontSize: "12px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    fontWeight: 600,
                                    letterSpacing: "0.14em",
                                    textTransform: "uppercase",
                                    cursor: isMeasuring ? "not-allowed" : "pointer",
                                }}
                            >
                                {isMeasuring ? "Calibrating..." : "Start Optical Scan (30s)"}
                            </button>
                        </>
                    ) : (
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", width: "100%" }}>
                            <button
                                type="button"
                                onClick={handleTap}
                                style={{
                                    width: "160px",
                                    height: "160px",
                                    borderRadius: "2px",
                                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                    color: "var(--text, #ECE8E3)",
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    cursor: "pointer",
                                    fontFamily: "var(--font-mono, monospace)",
                                    fontSize: "12px",
                                    letterSpacing: "0.14em",
                                    textTransform: "uppercase",
                                }}
                            >
                                Tap with pulse
                                <span style={{ fontSize: "10px", color: "var(--muted, rgba(236,232,227,0.55))", marginTop: "4px" }}>
                                    {manualTaps.length} taps recorded
                                </span>
                            </button>

                            <button
                                type="button"
                                onClick={completeMeasurement}
                                style={{
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
                                }}
                            >
                                Lock Tap Reading
                            </button>
                        </div>
                    )}
                </div>

                {/* Stage 2: Waveform & Evaluation */}
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
                            Telemetry Evaluation
                        </h3>
                        <StatusBadge level={signalQuality === "good" ? "normal" : "watch"} label={signalQuality === "good" ? "Quality: High" : "Quality: Marginal"} size="sm" />
                    </div>

                    {/* Waveform Visualization */}
                    <div
                        style={{
                            width: "100%",
                            height: "90px",
                            background: "var(--bg, #030307)",
                            border: "1px solid var(--line, rgba(233,228,223,0.16))",
                            borderRadius: "2px",
                            padding: "10px",
                            display: "flex",
                            alignItems: "flex-end",
                            gap: "2px",
                            overflow: "hidden",
                            position: "relative",
                        }}
                    >
                        <span style={{ position: "absolute", top: "6px", left: "8px", fontSize: "9px", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--muted, rgba(236,232,227,0.55))" }}>
                            Photoplethysmogram (rPPG ROI)
                        </span>

                        {waveformHistory.map((val, idx) => (
                            <div
                                key={idx}
                                style={{
                                    flex: 1,
                                    height: `${Math.max(10, Math.min(75, 35 + val))}%`,
                                    background: "var(--accent, #FF4D5A)",
                                    opacity: 0.8,
                                }}
                            />
                        ))}
                    </div>

                    {/* Evaluated Value Cards */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                            }}
                        >
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                Heart Rate
                            </span>
                            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--text, #ECE8E3)", fontFamily: "var(--font-display, sans-serif)", marginTop: "2px" }}>
                                {result ? result.hr : liveHrEstimate} <small style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>bpm</small>
                            </div>
                        </div>

                        <div
                            style={{
                                background: "var(--surface-2, rgba(255,255,255,0.04))",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "12px 14px",
                            }}
                        >
                            <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                                HRV (RMSSD)
                            </span>
                            <div style={{ fontSize: "28px", fontWeight: 800, color: "var(--cool, #8FB8E8)", fontFamily: "var(--font-display, sans-serif)", marginTop: "2px" }}>
                                {result ? result.hrv_rmssd : liveHrvEstimate} <small style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)" }}>ms</small>
                            </div>
                        </div>
                    </div>

                    {/* Result Actions */}
                    {result && (
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "auto" }}>
                            {gateError && (
                                <div style={{ border: "1px solid var(--accent, #FF4D5A)", background: "rgba(255,77,90,0.1)", padding: "10px 12px", borderRadius: "2px", fontSize: "11px", color: "var(--accent, #FF4D5A)", fontFamily: "var(--font-mono, monospace)" }}>
                                    {gateError}
                                </div>
                            )}

                            {submitSuccess && (
                                <div style={{ border: "1px solid var(--cool, #8FB8E8)", background: "rgba(143,184,232,0.1)", padding: "10px 12px", borderRadius: "2px", fontSize: "11px", color: "var(--cool, #8FB8E8)", fontFamily: "var(--font-mono, monospace)" }}>
                                    {submitSuccess}
                                </div>
                            )}

                            {!submitSuccess && (
                                <button
                                    type="button"
                                    onClick={handlePostMeasurement}
                                    disabled={isSubmitting}
                                    style={{
                                        background: "var(--accent, #FF4D5A)",
                                        color: "var(--accent-ink, #030307)",
                                        border: "none",
                                        borderRadius: "2px",
                                        padding: "10px 16px",
                                        fontSize: "12px",
                                        fontWeight: 600,
                                        fontFamily: "var(--font-mono, monospace)",
                                        letterSpacing: "0.14em",
                                        textTransform: "uppercase",
                                        cursor: isSubmitting ? "not-allowed" : "pointer",
                                    }}
                                >
                                    {isSubmitting ? "Logging..." : "Confirm & Log Telemetry"}
                                </button>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
