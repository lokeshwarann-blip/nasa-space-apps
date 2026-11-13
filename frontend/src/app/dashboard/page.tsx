
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Manrope, Space_Grotesk } from "next/font/google";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import styles from "./dashboard.module.css";

/* ---------- fonts ---------- */
const ui = Manrope({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const num = Space_Grotesk({ subsets: ["latin"], variable: "--font-num", display: "swap" });

const API_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/* ---------- types ---------- */
type Page = "Overview" | "Vital Signs" | "Health Trends" | "Assessments" | "Alerts";
type RangeKey = "24 Hours" | "7 Days" | "30 Days";
type MetricId = "hr" | "spo2" | "bp" | "temp";

interface Metric {
    id: MetricId;
    title: string;
    unit: string;
    description: string;
    icon: string;
}

interface Measurement {
    id: string;
    measurement_type: string;
    value_numeric: number | null;
    unit: string;
    measured_at: string;
    quality_status: string;
}

interface MeasurementResponse {
    items: Measurement[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

interface CheckIn {
    id: string;
    check_in_type: "WELLNESS" | "SYMPTOM";
    crew_member_id: string;
    recorded_at: string;
    timestamp: string;
    details: Record<string, unknown>;
    provenance: Record<string, unknown>;
}

interface CheckInResponse {
    items: CheckIn[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

interface LiveAlert {
    id: string;
    alert_identifier: string;
    crew_member_id: string;
    summary: string;
    priority: "INFO" | "CAUTION" | "CRITICAL" | "EMERGENCY";
    status: "open" | "acknowledged" | "assigned" | "resolved" | "dismissed";
    event_time: string;
    is_delayed: boolean;
}

interface AlertResponse {
    items: LiveAlert[];
    total: number;
    limit: number;
    offset: number;
}

interface LiveTask {
    id: string;
    title: string;
    category: "MEASUREMENT_REMINDER" | "WELLNESS_CHECK_IN" | "FOLLOW_UP_ACTION" | "GENERAL";
    status: "PENDING" | "COMPLETED" | "CANCELLED" | "MISSED";
    due_start: string;
    due_end: string;
    completed_at: string | null;
}

interface TaskResponse {
    items: LiveTask[];
    total: number;
    limit: number;
    offset: number;
}

/* ---------- navigation and metrics ---------- */
const PAGES: { name: Page; icon: string; title: string; blurb: string }[] = [
    { name: "Overview", icon: "home", title: "Mission overview", blurb: "Your health at a glance" },
    { name: "Vital Signs", icon: "pulse", title: "Vital signs", blurb: "Your latest recorded health measurements" },
    { name: "Health Trends", icon: "trend", title: "Health trends", blurb: "How your readings change over time" },
    { name: "Assessments", icon: "check", title: "Health assessments", blurb: "Review assessment records and their status" },
    { name: "Alerts", icon: "bell", title: "Health alerts", blurb: "Notifications from health monitoring" },
];

const METRICS: Metric[] = [
    {
        id: "hr",
        title: "Heart rate",
        unit: "bpm",
        description: "Beats per minute at rest and during activity.",
        icon: "heart",
    },
    {
        id: "spo2",
        title: "Oxygen saturation",
        unit: "%",
        description: "Share of oxygen carried in the blood.",
        icon: "drop",
    },
    {
        id: "bp",
        title: "Blood pressure",
        unit: "mmHg",
        description: "Systolic and diastolic pressure.",
        icon: "pulse",
    },
    {
        id: "temp",
        title: "Body temperature",
        unit: "°C",
        description: "Core temperature changes through the day.",
        icon: "thermo",
    },
];

const RANGE_KEYS: RangeKey[] = ["24 Hours", "7 Days", "30 Days"];

/* ---------- helpers ---------- */
const cx = (...a: (string | false | undefined)[]) => a.filter(Boolean).join(" ");

function getMeasurementType(metricId: MetricId): string {
    const types: Record<MetricId, string> = {
        hr: "heart_rate",
        spo2: "spo2",
        bp: "blood_pressure_systolic",
        temp: "body_temperature",
    };

    return types[metricId];
}

function formatMeasurementDate(date: string): string {
    return new Date(date).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

/* ---------- icons ---------- */
const ICONS: Record<string, ReactNode> = {
    home: <><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M9 22V12h6v10" /></>,
    pulse: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
    trend: <><path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" /></>,
    check: <><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></>,
    heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z" />,
    drop: <path d="M12 2.7l5.7 5.7a8 8 0 1 1-11.4 0z" />,
    thermo: <path d="M14 14.8V4a2 2 0 0 0-4 0v10.8a4 4 0 1 0 4 0z" />,
    plus: <path d="M12 5v14M5 12h14" />,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4-1.4" /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
    close: <path d="M18 6L6 18M6 6l12 12" />,
};

function Icon({ name }: { name: string }) {
    return (
        <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true">
            {ICONS[name]}
        </svg>
    );
}

/* ---------- reusable components ---------- */
function Gauge({ value, average, max }: { value: number; average: number; max: number }) {
    const ring = (r: number, n: number, filled: number, on: string) =>
        Array.from({ length: n }, (_, i) => {
            const a = (i / n) * Math.PI * 2 - Math.PI / 2;
            const p = (d: number) => (100 + d * Math.cos(a)).toFixed(1);
            const q = (d: number) => (100 + d * Math.sin(a)).toFixed(1);

            return (
                <line
                    key={`${r}-${i}`}
                    x1={p(r - 4)}
                    y1={q(r - 4)}
                    x2={p(r + 4)}
                    y2={q(r + 4)}
                    strokeWidth="4"
                    strokeLinecap="round"
                    className={i < filled ? on : styles.segOff}
                />
            );
        });

    return (
        <svg
            viewBox="0 0 200 200"
            className={styles.gaugeSvg}
            role="img"
            aria-label={`Heart rate ${value} beats per minute`}
        >
            {ring(88, 56, Math.round((56 * value) / max), styles.segOn)}
            {ring(70, 44, Math.round((44 * average) / max), styles.segAvg)}
        </svg>
    );
}

function ChartTip({
    active,
    payload,
    label,
    unit,
}: {
    active?: boolean;
    payload?: { value?: number }[];
    label?: string | number;
    unit: string;
}) {
    if (!active || !payload?.length) return null;

    return (
        <div className={styles.tip}>
            <span>{label}</span>
            <b>{payload[0].value} {unit}</b>
        </div>
    );
}

function Empty({ title, text, tag }: { title: string; text: string; tag: string }) {
    return (
        <div className={styles.emptyState}>
            <div className={styles.emptyIcon}><Icon name="check" /></div>
            <h3>{title}</h3>
            <p>{text}</p>
            <span>{tag}</span>
        </div>
    );
}

/* ---------- page ---------- */
export default function Dashboard() {
    const [page, setPage] = useState<Page>("Overview");
    const [range, setRange] = useState<RangeKey>("7 Days");
    const [metricId, setMetricId] = useState<MetricId>("hr");
    const [dark, setDark] = useState(true);

    const [alertFilter, setAlertFilter] =
        useState<"All" | "Open" | "Acknowledged">("All");

    const [liveAlerts, setLiveAlerts] = useState<LiveAlert[]>([]);
    const [alertsLoading, setAlertsLoading] = useState(false);
    const [alertError, setAlertError] = useState("");
    const [acknowledgingAlert, setAcknowledgingAlert] = useState<string | null>(null);

    const [liveTasks, setLiveTasks] = useState<LiveTask[]>([]);
    const [tasksLoading, setTasksLoading] = useState(false);
    const [tasksError, setTasksError] = useState("");
    const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);

    const [modal, setModal] = useState(false);
    const [mood, setMood] = useState(4);
    const [fatigue, setFatigue] = useState(2);
    const [sleepDuration, setSleepDuration] = useState("8");
    const [sleepQuality, setSleepQuality] = useState(4);
    const [stress, setStress] = useState(2);
    const [savingCheckIn, setSavingCheckIn] = useState(false);
    const [toast, setToast] = useState("");
    const [now, setNow] = useState("");

    const router = useRouter();
    const [username, setUsername] = useState("Crew member");

    const [measurements, setMeasurements] = useState<Measurement[]>([]);
    const [measurementsLoading, setMeasurementsLoading] = useState(true);
    const [measurementError, setMeasurementError] = useState("");

    const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
    const [checkInsLoading, setCheckInsLoading] = useState(true);
    const [checkInsError, setCheckInsError] = useState("");

    const firstBtn = useRef<HTMLButtonElement>(null);

    const metric = METRICS.find((m) => m.id === metricId) ?? METRICS[0];
    const info = PAGES.find((p) => p.name === page) ?? PAGES[0];

    useEffect(() => {
        try {
            const raw = sessionStorage.getItem("meliora_identity");

            if (raw) {
                const saved = JSON.parse(raw);

                if (typeof saved?.username === "string") {
                    setUsername(saved.username);
                }
            }
        } catch {
            /* keep the default name */
        }
    }, []);

    function logout() {
        sessionStorage.removeItem("meliora_access_token");
        sessionStorage.removeItem("meliora_identity");
        router.replace("/login");
    }

    const openCount = liveAlerts.filter(
        (a) => a.status === "open" || a.status === "assigned"
    ).length;

    const taskTotal = liveTasks.length;

    const doneCount = liveTasks.filter(
        (task) => task.status === "COMPLETED"
    ).length;

    const shownLiveAlerts = liveAlerts.filter((a) => {
        if (alertFilter === "All") return true;
        if (alertFilter === "Open") {
            return a.status === "open" || a.status === "assigned";
        }
        return a.status === "acknowledged";
    });

    /* ---------- load check-ins ---------- */
    async function loadCheckIns() {
        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setCheckInsError("Please log in to view your check-in history.");
            setCheckInsLoading(false);
            return;
        }

        setCheckInsLoading(true);

        try {
            const response = await fetch(
                `${API_URL}/api/v1/check-ins?check_in_type=ALL&limit=50`,
                {
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`Check-in history request failed (${response.status})`);
            }

            const data: CheckInResponse = await response.json();

            setCheckIns(data.items ?? []);
            setCheckInsError("");
        } catch (error) {
            setCheckInsError(
                error instanceof Error
                    ? error.message
                    : "Unable to load check-in history."
            );
        } finally {
            setCheckInsLoading(false);
        }
    }

    /* ---------- load alerts ---------- */
    async function loadAlerts() {
        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setAlertError("Please log in to view alerts.");
            setAlertsLoading(false);
            return;
        }

        setAlertsLoading(true);
        setAlertError("");

        try {
            const response = await fetch(`${API_URL}/api/v1/alerts?limit=50`, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                throw new Error(`Alerts request failed (${response.status})`);
            }

            const data: AlertResponse = await response.json();

            setLiveAlerts(data.items ?? []);
        } catch (error) {
            setAlertError(
                error instanceof Error
                    ? error.message
                    : "Unable to load alerts."
            );
        } finally {
            setAlertsLoading(false);
        }
    }

    /* ---------- load today's tasks ---------- */
    async function loadTasks() {
        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setTasksError("Please log in to view your tasks.");
            setTasksLoading(false);
            return;
        }

        setTasksLoading(true);
        setTasksError("");

        try {
            const today = new Date();

            const startOfDay = new Date(today);
            startOfDay.setHours(0, 0, 0, 0);

            const endOfDay = new Date(today);
            endOfDay.setHours(23, 59, 59, 999);

            const params = new URLSearchParams({
                due_from: startOfDay.toISOString(),
                due_to: endOfDay.toISOString(),
                limit: "100",
            });

            const response = await fetch(
                `${API_URL}/api/v1/tasks?${params.toString()}`,
                {
                    method: "GET",
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            );

            if (!response.ok) {
                throw new Error(`Tasks request failed (${response.status})`);
            }

            const data: TaskResponse = await response.json();

            setLiveTasks(data.items ?? []);
        } catch (error) {
            setTasksError(
                error instanceof Error
                    ? error.message
                    : "Unable to load today's tasks."
            );
        } finally {
            setTasksLoading(false);
        }
    }

    /* ---------- complete a task ---------- */
    async function completeTask(taskId: string) {
        if (completingTaskId !== null) return;

        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setTasksError("Please log in again to complete this task.");
            return;
        }

        setCompletingTaskId(taskId);
        setTasksError("");

        try {
            const response = await fetch(
                `${API_URL}/api/v1/tasks/${taskId}/complete`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        completion_source: "CREW_PORTAL",
                    }),
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);

                const message =
                    typeof errorData?.detail === "string"
                        ? errorData.detail
                        : `Task completion failed (${response.status}).`;

                throw new Error(message);
            }

            const completedTask: LiveTask = await response.json();

            setLiveTasks((current) =>
                current.map((task) =>
                    task.id === taskId ? completedTask : task
                )
            );

            setToast("Task completed successfully.");
        } catch (error) {
            setTasksError(
                error instanceof Error
                    ? error.message
                    : "Unable to complete this task."
            );
        } finally {
            setCompletingTaskId(null);
        }
    }

    /* ---------- initial API requests ---------- */
    useEffect(() => {
        loadTasks();
        loadAlerts();
        loadCheckIns();
    }, []);

    /* ---------- load measurements ---------- */
    useEffect(() => {
        const controller = new AbortController();

        async function loadMeasurements() {
            const token = sessionStorage.getItem("meliora_access_token");

            if (!token) {
                setMeasurementError("Please log in to view your readings.");
                setMeasurementsLoading(false);
                return;
            }

            try {
                const response = await fetch(
                    `${API_URL}/api/v1/measurements?limit=100`,
                    {
                        method: "GET",
                        headers: {
                            Authorization: `Bearer ${token}`,
                        },
                        signal: controller.signal,
                    }
                );

                if (!response.ok) {
                    throw new Error(`Measurements request failed (${response.status})`);
                }

                const data: MeasurementResponse = await response.json();

                setMeasurements(data.items ?? []);
                setMeasurementError("");
            } catch (error) {
                if (error instanceof Error && error.name === "AbortError") {
                    return;
                }

                setMeasurementError(
                    error instanceof Error
                        ? error.message
                        : "Unable to load measurements."
                );
            } finally {
                if (!controller.signal.aborted) {
                    setMeasurementsLoading(false);
                }
            }
        }

        loadMeasurements();

        return () => controller.abort();
    }, []);

    /* ---------- latest measurement for each type ---------- */
    const latestByType = useMemo(() => {
        const sorted = [...measurements].sort(
            (a, b) =>
                new Date(b.measured_at).getTime() -
                new Date(a.measured_at).getTime()
        );

        const latest: Record<string, Measurement> = {};

        for (const item of sorted) {
            if (
                item.value_numeric !== null &&
                !latest[item.measurement_type]
            ) {
                latest[item.measurement_type] = item;
            }
        }

        return latest;
    }, [measurements]);

    const systolic = latestByType.blood_pressure_systolic;
    const diastolic = latestByType.blood_pressure_diastolic;

    const realMetricValues: Record<MetricId, string> = {
        hr: latestByType.heart_rate?.value_numeric?.toFixed(0) ?? "--",
        spo2: latestByType.spo2?.value_numeric?.toFixed(0) ?? "--",
        bp:
            systolic?.value_numeric != null &&
                diastolic?.value_numeric != null
                ? `${systolic.value_numeric.toFixed(0)}/${diastolic.value_numeric.toFixed(0)}`
                : "--",
        temp: latestByType.body_temperature?.value_numeric?.toFixed(1) ?? "--",
    };

    /* ---------- real trend data ---------- */
    const realSeries = useMemo(() => {
        const rangeMs: Record<RangeKey, number> = {
            "24 Hours": 24 * 60 * 60 * 1000,
            "7 Days": 7 * 24 * 60 * 60 * 1000,
            "30 Days": 30 * 24 * 60 * 60 * 1000,
        };

        const matching = measurements
            .filter((item) => {
                return (
                    item.measurement_type === getMeasurementType(metricId) &&
                    item.value_numeric !== null &&
                    Number.isFinite(new Date(item.measured_at).getTime())
                );
            })
            .sort(
                (a, b) =>
                    new Date(a.measured_at).getTime() -
                    new Date(b.measured_at).getTime()
            );

        if (matching.length === 0) return [];

        const latestTime = new Date(
            matching[matching.length - 1].measured_at
        ).getTime();

        const cutoff = latestTime - rangeMs[range];

        return matching
            .filter((item) => {
                const timestamp = new Date(item.measured_at).getTime();
                return timestamp >= cutoff && timestamp <= latestTime;
            })
            .map((item) => ({
                label: formatMeasurementDate(item.measured_at),
                value: item.value_numeric as number,
            }));
    }, [measurements, metricId, range]);
    /* ---------- clock ---------- */
    useEffect(() => {
        const tick = () =>
            setNow(new Date().toISOString().slice(11, 19) + " UTC");

        tick();

        const id = setInterval(tick, 1000);

        return () => clearInterval(id);
    }, []);

    /* ---------- toast ---------- */
    useEffect(() => {
        if (!toast) return;

        const id = setTimeout(() => setToast(""), 3200);

        return () => clearTimeout(id);
    }, [toast]);

    /* ---------- modal keyboard handling ---------- */
    useEffect(() => {
        if (!modal) return;

        firstBtn.current?.focus();

        const onKey = (e: KeyboardEvent) => {
            if (e.key === "Escape") setModal(false);
        };

        window.addEventListener("keydown", onKey);

        return () => window.removeEventListener("keydown", onKey);
    }, [modal]);

    /* ---------- acknowledge live alert ---------- */
    async function acknowledgeLiveAlert(id: string) {
        if (acknowledgingAlert) return;

        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setToast("Session expired. Please log in again.");
            return;
        }

        setAcknowledgingAlert(id);

        try {
            const response = await fetch(
                `${API_URL}/api/v1/alerts/${id}/acknowledge`,
                {
                    method: "POST",
                    headers: {
                        Authorization: `Bearer ${token}`,
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({}),
                }
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);

                const message =
                    typeof errorData?.detail === "string"
                        ? errorData.detail
                        : `Could not acknowledge alert (${response.status}).`;

                throw new Error(message);
            }

            await loadAlerts();

            setToast("Alert acknowledged successfully.");
        } catch (error) {
            setToast(
                error instanceof Error
                    ? error.message
                    : "Unable to acknowledge alert."
            );
        } finally {
            setAcknowledgingAlert(null);
        }
    }

    /* ---------- save wellness check-in ---------- */
    async function saveCheckIn() {
        if (savingCheckIn) return;

        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            setToast("Session expired. Please log in again.");
            return;
        }

        const sleepHours = Number(sleepDuration);

        if (
            !Number.isFinite(sleepHours) ||
            sleepHours < 0 ||
            sleepHours > 24
        ) {
            setToast("Sleep duration must be between 0 and 24 hours.");
            return;
        }

        setSavingCheckIn(true);

        try {
            const response = await fetch(`${API_URL}/api/v1/check-ins`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    check_in_type: "WELLNESS",
                    sleep_duration_hours: sleepHours,
                    sleep_quality: sleepQuality,
                    mood,
                    stress,
                    fatigue,
                    measured_at: new Date().toISOString(),
                    provenance: { source: "MELIORA_WEB_APP" },
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);

                const message =
                    typeof errorData?.detail === "string"
                        ? errorData.detail
                        : `Server rejected the check-in (${response.status}).`;

                setToast(message);
                return;
            }

            setModal(false);

            await loadCheckIns();

            setToast("Wellness check-in submitted successfully.");
        } catch {
            setToast(
                "Could not reach the backend. Check that the server is running."
            );
        } finally {
            setSavingCheckIn(false);
        }
    }

    /* ---------- metric cards ---------- */
    const metricCards = (
        <div className={styles.metricGrid}>
            {METRICS.map((m) => {
                const realValue = realMetricValues[m.id];

                return (
                    <button
                        key={m.id}
                        type="button"
                        onClick={() => setMetricId(m.id)}
                        aria-pressed={metricId === m.id}
                        className={cx(
                            styles.metricCard,
                            metricId === m.id && styles.metricActive
                        )}
                    >
                        <span className={styles.metricTop}>
                            <span className={styles.metricIcon}>
                                <Icon name={m.icon} />
                            </span>

                            <span className={styles.metricName}>
                                {m.title}
                            </span>
                        </span>

                        <span className={styles.metricValue}>
                            {realValue} <small>{m.unit}</small>
                        </span>

                        <span className={styles.metricBottom}>
                            <span className={cx(styles.chip, styles.muted)}>
                                {measurementsLoading
                                    ? "Loading..."
                                    : realValue !== "--"
                                        ? "Latest reading"
                                        : "No reading"}
                            </span>
                        </span>
                    </button>
                );
            })}
        </div>
    );

    /* ---------- time range controls ---------- */
    const rangePills = (
        <div className={styles.pills} role="group" aria-label="Time range">
            {RANGE_KEYS.map((r) => (
                <button
                    key={r}
                    type="button"
                    aria-pressed={range === r}
                    onClick={() => setRange(r)}
                    className={cx(
                        styles.pill,
                        range === r && styles.pillActive
                    )}
                >
                    {r}
                </button>
            ))}
        </div>
    );

    /* ---------- chart ---------- */
    const chart = measurementsLoading ? (
        <Empty
            title="Loading readings"
            text="Retrieving measurements from the mission data service."
            tag="LOADING"
        />
    ) : measurementError ? (
        <Empty
            title="Unable to load readings"
            text={measurementError}
            tag="API ERROR"
        />
    ) : realSeries.length === 0 ? (
        <Empty
            title="No readings in this range"
            text="No measurements were returned for this metric and time range."
            tag="NO READINGS"
        />
    ) : (
        <div className={styles.chartBox}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={realSeries}
                    margin={{ top: 8, right: 8, left: -8, bottom: 0 }}
                >
                    <defs>
                        <linearGradient
                            id="realTrendFill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                        >
                            <stop
                                offset="0%"
                                stopColor="#8b7be8"
                                stopOpacity={0.35}
                            />
                            <stop
                                offset="100%"
                                stopColor="#8b7be8"
                                stopOpacity={0}
                            />
                        </linearGradient>
                    </defs>

                    <CartesianGrid
                        vertical={false}
                        stroke="rgba(138,138,153,0.22)"
                    />

                    <XAxis
                        dataKey="label"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fill: "#8a8a99", fontSize: 12 }}
                    />

                    <YAxis
                        domain={["auto", "auto"]}
                        tickLine={false}
                        axisLine={false}
                        width={44}
                        tick={{ fill: "#8a8a99", fontSize: 12 }}
                    />

                    <Tooltip
                        content={<ChartTip unit={metric.unit} />}
                        cursor={{
                            stroke: "#8b7be8",
                            strokeDasharray: "4 4",
                        }}
                    />

                    <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#8b7be8"
                        strokeWidth={3}
                        fill="url(#realTrendFill)"
                        dot={{
                            r: 3,
                            fill: "#8b7be8",
                            strokeWidth: 0,
                        }}
                        activeDot={{ r: 6 }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );

    /* ---------- live alert row ---------- */
    const liveAlertRow = (a: LiveAlert, withAction: boolean) => {
        const level =
            a.priority === "CRITICAL" || a.priority === "EMERGENCY"
                ? "critical"
                : a.priority === "CAUTION"
                    ? "warning"
                    : "info";

        const canAcknowledge =
            a.status === "open" || a.status === "assigned";

        return (
            <li key={a.id} className={styles.alertItem}>
                <i className={cx(styles.alertBar, styles[level])} />

                <div className={styles.alertBody}>
                    <p className={styles.alertTitle}>{a.summary}</p>

                    <p className={styles.alertMeta}>
                        {formatMeasurementDate(a.event_time)} ·{" "}
                        {a.status.replaceAll("_", " ")}

                        <span className={styles.badge}>
                            {a.priority}
                        </span>

                        {a.is_delayed && (
                            <span className={styles.badge}>
                                Delayed sync
                            </span>
                        )}
                    </p>

                    <p className={styles.alertMeta}>
                        {a.alert_identifier}
                    </p>
                </div>

                {withAction && canAcknowledge && (
                    <button
                        type="button"
                        className={styles.ackBtn}
                        onClick={() => acknowledgeLiveAlert(a.id)}
                        disabled={acknowledgingAlert !== null}
                    >
                        {acknowledgingAlert === a.id
                            ? "Saving..."
                            : "Acknowledge"}
                    </button>
                )}
            </li>
        );
    };

    /* ---------- render ---------- */
    return (
        <main
            className={cx(styles.dashboard, ui.variable, num.variable)}
            data-theme={dark ? "dark" : "light"}
        >
            <div className={styles.shell}>
                {/* SIDEBAR */}
                <aside className={styles.sidebar}>
                    <div className={styles.brand}>
                        <h2>Meliora</h2>
                    </div>

                    <nav aria-label="Main">
                        {PAGES.map((p) => (
                            <button
                                key={p.name}
                                type="button"
                                onClick={() => setPage(p.name)}
                                aria-current={
                                    page === p.name ? "page" : undefined
                                }
                                className={cx(
                                    styles.navItem,
                                    page === p.name && styles.active
                                )}
                            >
                                <Icon name={p.icon} />

                                {p.name}

                                {p.name === "Alerts" && openCount > 0 && (
                                    <span className={styles.navBadge}>
                                        {openCount}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>

                    <div className={styles.sidebarBottom}>
                        <b>{username}</b>
                        <span>Crew member</span>
                        <span>
                            Engineering prototype. Not a certified medical device.
                        </span>

                        <button
                            type="button"
                            className={styles.logout}
                            onClick={logout}
                        >
                            Sign out
                        </button>
                    </div>
                </aside>

                {/* MAIN */}
                <section className={styles.main}>
                    <header className={styles.header}>
                        <div>
                            <p className={styles.crumb}>
                                Crew member portal
                            </p>

                            <h2>{info.title}</h2>
                        </div>

                        <div className={styles.tools}>
                            <span className={styles.clock}>{now}</span>

                            <button
                                type="button"
                                className={styles.iconBtn}
                                onClick={() => setDark(!dark)}
                                aria-label={
                                    dark
                                        ? "Switch to light theme"
                                        : "Switch to dark theme"
                                }
                            >
                                <Icon name={dark ? "sun" : "moon"} />
                            </button>

                            <button
                                type="button"
                                className={styles.iconBtn}
                                onClick={() => setPage("Alerts")}
                                aria-label={`Alerts, ${openCount} open`}
                            >
                                <Icon name="bell" />

                                {openCount > 0 && (
                                    <span className={styles.dotBadge}>
                                        {openCount}
                                    </span>
                                )}
                            </button>

                            <div className={styles.avatar}>
                                {username.slice(0, 2).toUpperCase()}
                            </div>

                            <span>{username}</span>
                        </div>
                    </header>

                    <div className={styles.content} key={page}>
                        <div className={styles.hero}>
                            <div>
                                <h1>
                                    {page === "Overview"
                                        ? "Good day, Commander"
                                        : info.title}
                                </h1>

                                <p>
                                    {page === "Overview"
                                        ? alertsLoading
                                            ? "Synchronizing mission alerts..."
                                            : alertError
                                                ? alertError
                                                : `${measurements.length} measurement records received from the mission data service.`
                                        : info.blurb}
                                </p>
                            </div>

                            <button
                                type="button"
                                className={styles.cta}
                                onClick={() => setModal(true)}
                            >
                                <Icon name="plus" /> Log check-in
                            </button>
                        </div>

                        {/* OVERVIEW */}
                        {page === "Overview" && (
                            <>
                                {metricCards}

                                <div className={styles.row2}>
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <div>
                                                <h3>{metric.title} trend</h3>
                                                <p>
                                                    Mission data · {metric.unit}
                                                </p>
                                            </div>

                                            {rangePills}
                                        </div>

                                        {chart}
                                    </section>

                                    <section className={styles.card}>
                                        <h3>Heart rate zone</h3>

                                        <div className={styles.legend}>
                                            <span className={styles.legendAvg}>
                                                Average
                                            </span>
                                            <span className={styles.legendNow}>
                                                Current
                                            </span>
                                        </div>

                                        <div className={styles.gauge}>
                                            <Gauge
                                                value={
                                                    latestByType.heart_rate
                                                        ?.value_numeric ?? 0
                                                }
                                                average={
                                                    latestByType.heart_rate
                                                        ?.value_numeric ?? 0
                                                }
                                                max={180}
                                            />

                                            <div className={styles.gaugeCenter}>
                                                <b>{realMetricValues.hr}</b>
                                                <small>beats / min</small>
                                            </div>
                                        </div>
                                    </section>
                                </div>

                                <div className={styles.row3}>
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <h3>Latest alerts</h3>

                                            <button
                                                type="button"
                                                className={styles.linkBtn}
                                                onClick={() => setPage("Alerts")}
                                            >
                                                View all
                                            </button>
                                        </div>

                                        {alertsLoading ? (
                                            <p className={styles.quiet}>
                                                Loading alerts...
                                            </p>
                                        ) : alertError ? (
                                            <p className={styles.quiet}>
                                                {alertError}
                                            </p>
                                        ) : liveAlerts.length === 0 ? (
                                            <p className={styles.quiet}>
                                                No alert records are currently connected to this dashboard.
                                            </p>
                                        ) : (
                                            <ul className={styles.alertList}>
                                                {liveAlerts
                                                    .slice(0, 2)
                                                    .map((a) =>
                                                        liveAlertRow(a, false)
                                                    )}
                                            </ul>
                                        )}
                                    </section>

                                    {/* TODAY'S TASKS */}
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <h3>Today’s tasks</h3>

                                            <span className={styles.chip}>
                                                {doneCount} of {taskTotal} done
                                            </span>
                                        </div>

                                        <div
                                            className={styles.progress}
                                            aria-hidden="true"
                                        >
                                            <span
                                                style={{
                                                    width: `${taskTotal > 0
                                                        ? (doneCount / taskTotal) * 100
                                                        : 0
                                                        }%`,
                                                }}
                                            />
                                        </div>

                                        {tasksLoading ? (
                                            <p className={styles.quiet}>
                                                Loading today's tasks...
                                            </p>
                                        ) : tasksError ? (
                                            <p className={styles.quiet}>
                                                {tasksError}
                                            </p>
                                        ) : liveTasks.length === 0 ? (
                                            <p className={styles.quiet}>
                                                No tasks scheduled for today.
                                            </p>
                                        ) : (
                                            <ul className={styles.tasks}>
                                                {liveTasks.map((task) => {
                                                    const isCompleted =
                                                        task.status === "COMPLETED";

                                                    const canComplete =
                                                        task.status === "PENDING";

                                                    return (
                                                        <li key={task.id}>
                                                            <label
                                                                className={cx(
                                                                    styles.task,
                                                                    isCompleted &&
                                                                    styles.taskDone
                                                                )}
                                                            >
                                                                <input
                                                                    type="checkbox"
                                                                    checked={isCompleted}
                                                                    disabled={
                                                                        !canComplete ||
                                                                        completingTaskId !== null
                                                                    }
                                                                    onChange={() =>
                                                                        completeTask(task.id)
                                                                    }
                                                                />

                                                                <span
                                                                    className={styles.taskBox}
                                                                />

                                                                <span>
                                                                    {task.title}
                                                                </span>

                                                                <time>
                                                                    {isCompleted
                                                                        ? "Completed"
                                                                        : canComplete
                                                                            ? formatMeasurementDate(task.due_start)
                                                                            : task.status}
                                                                </time>
                                                            </label>
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        )}
                                    </section>
                                </div>
                            </>
                        )}

                        {/* VITAL SIGNS */}
                        {page === "Vital Signs" && (
                            <div className={styles.vitalGrid}>
                                {METRICS.map((m) => {
                                    const realValue = realMetricValues[m.id];

                                    return (
                                        <article
                                            key={m.id}
                                            className={styles.card}
                                        >
                                            <div className={styles.metricTop}>
                                                <span className={styles.metricIcon}>
                                                    <Icon name={m.icon} />
                                                </span>

                                                <span className={styles.metricName}>
                                                    {m.title}
                                                </span>
                                            </div>

                                            <p className={styles.metricValue}>
                                                {realValue} <small>{m.unit}</small>
                                            </p>

                                            <p className={styles.quiet}>
                                                {m.description}
                                            </p>

                                            <span
                                                className={cx(
                                                    styles.chip,
                                                    styles.muted
                                                )}
                                            >
                                                {measurementsLoading
                                                    ? "Loading..."
                                                    : realValue !== "--"
                                                        ? "Latest reading"
                                                        : "No reading"}
                                            </span>

                                            <button
                                                type="button"
                                                className={styles.linkBtn}
                                                onClick={() => {
                                                    setMetricId(m.id);
                                                    setPage("Health Trends");
                                                }}
                                            >
                                                See trend
                                            </button>
                                        </article>
                                    );
                                })}
                            </div>
                        )}

                        {/* HEALTH TRENDS */}
                        {page === "Health Trends" && (
                            <>
                                <div
                                    className={styles.pills}
                                    role="group"
                                    aria-label="Choose a measurement"
                                >
                                    {METRICS.map((m) => (
                                        <button
                                            key={m.id}
                                            type="button"
                                            aria-pressed={metricId === m.id}
                                            onClick={() => setMetricId(m.id)}
                                            className={cx(
                                                styles.pill,
                                                metricId === m.id &&
                                                styles.pillActive
                                            )}
                                        >
                                            {m.title}
                                        </button>
                                    ))}
                                </div>

                                <section className={styles.card}>
                                    <div className={styles.cardHead}>
                                        <div>
                                            <h3>{metric.title}</h3>
                                            <p>
                                                Mission data · {metric.unit}
                                            </p>
                                        </div>

                                        {rangePills}
                                    </div>

                                    {chart}
                                </section>

                                <div className={styles.statRow}>
                                    {[
                                        [
                                            "Lowest",
                                            realSeries.length
                                                ? Math.min(
                                                    ...realSeries.map((s) => s.value)
                                                )
                                                : "--",
                                        ],
                                        [
                                            "Average",
                                            realSeries.length
                                                ? Number(
                                                    (
                                                        realSeries.reduce(
                                                            (a, b) => a + b.value,
                                                            0
                                                        ) / realSeries.length
                                                    ).toFixed(2)
                                                )
                                                : "--",
                                        ],
                                        [
                                            "Highest",
                                            realSeries.length
                                                ? Math.max(
                                                    ...realSeries.map((s) => s.value)
                                                )
                                                : "--",
                                        ],
                                    ].map(([label, value]) => (
                                        <div key={label} className={styles.stat}>
                                            <span>{label}</span>

                                            <b>
                                                {value}{" "}
                                                <small>
                                                    {realSeries.length
                                                        ? metric.unit
                                                        : ""}
                                                </small>
                                            </b>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}

                        {/* ASSESSMENTS */}
                        {page === "Assessments" && (
                            <div className={styles.acc}>
                                {checkInsLoading ? (
                                    <Empty
                                        title="Loading check-in history"
                                        text="Retrieving your submitted wellness and symptom records."
                                        tag="LOADING"
                                    />
                                ) : checkInsError ? (
                                    <Empty
                                        title="Could not load check-ins"
                                        text={checkInsError}
                                        tag="ERROR"
                                    />
                                ) : checkIns.length === 0 ? (
                                    <Empty
                                        title="No check-ins yet"
                                        text="Your submitted wellness and symptom check-ins will appear here."
                                        tag="NO RECORDS"
                                    />
                                ) : (
                                    <>
                                        {checkIns.map((item) => (
                                            <div
                                                key={item.id}
                                                className={styles.accItem}
                                            >
                                                <div className={styles.accHead}>
                                                    <span>
                                                        <b>
                                                            {item.check_in_type === "WELLNESS"
                                                                ? "Wellness check-in"
                                                                : "Symptom report"}
                                                        </b>

                                                        <small>
                                                            {new Date(
                                                                item.recorded_at
                                                            ).toLocaleString()}
                                                        </small>
                                                    </span>

                                                    <span className={styles.chip}>
                                                        {item.check_in_type}
                                                    </span>
                                                </div>

                                                <div className={styles.accBody}>
                                                    <ul>
                                                        {Object.entries(
                                                            item.details
                                                        ).map(([key, value]) => (
                                                            <li key={key}>
                                                                <strong>
                                                                    {key.replaceAll("_", " ")}:
                                                                </strong>{" "}

                                                                {Array.isArray(value)
                                                                    ? value.join(", ")
                                                                    : value !== null &&
                                                                        typeof value === "object"
                                                                        ? JSON.stringify(value)
                                                                        : String(value)}
                                                            </li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            </div>
                                        ))}

                                        <p className={styles.quiet}>
                                            Showing {checkIns.length} of your latest check-in records.
                                            These are self-reported records, not medical diagnoses.
                                        </p>
                                    </>
                                )}
                            </div>
                        )}

                        {/* ALERTS */}
                        {page === "Alerts" && (
                            <>
                                <div
                                    className={styles.pills}
                                    role="group"
                                    aria-label="Filter alerts"
                                >
                                    {(
                                        ["All", "Open", "Acknowledged"] as const
                                    ).map((f) => (
                                        <button
                                            key={f}
                                            type="button"
                                            aria-pressed={alertFilter === f}
                                            onClick={() => setAlertFilter(f)}
                                            className={cx(
                                                styles.pill,
                                                alertFilter === f &&
                                                styles.pillActive
                                            )}
                                        >
                                            {f}
                                        </button>
                                    ))}
                                </div>

                                {alertsLoading ? (
                                    <Empty
                                        title="Loading alerts"
                                        text="Retrieving notifications from the mission alert service."
                                        tag="LOADING"
                                    />
                                ) : alertError ? (
                                    <Empty
                                        title="Unable to load alerts"
                                        text={alertError}
                                        tag="API ERROR"
                                    />
                                ) : shownLiveAlerts.length > 0 ? (
                                    <section className={styles.card}>
                                        <ul className={styles.alertList}>
                                            {shownLiveAlerts.map((a) =>
                                                liveAlertRow(a, true)
                                            )}
                                        </ul>
                                    </section>
                                ) : liveAlerts.length === 0 ? (
                                    <Empty
                                        title="No alerts yet"
                                        text="Health monitoring notifications will appear here when alert data is received."
                                        tag="NO ALERTS"
                                    />
                                ) : (
                                    <Empty
                                        title="Nothing in this filter"
                                        text="Try another filter to see the rest of your alerts."
                                        tag="ALL CLEAR"
                                    />
                                )}
                            </>
                        )}
                    </div>
                </section>
            </div>

            {/* CHECK-IN MODAL */}
            {modal && (
                <div
                    className={styles.overlay}
                    onClick={() =>
                        !savingCheckIn && setModal(false)
                    }
                >
                    <div
                        className={styles.modal}
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="ci-title"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className={styles.modalHead}>
                            <h3 id="ci-title">How are you today?</h3>

                            <button
                                type="button"
                                className={styles.iconBtn}
                                onClick={() =>
                                    !savingCheckIn && setModal(false)
                                }
                                aria-label="Close"
                            >
                                <Icon name="close" />
                            </button>
                        </div>

                        <div className={styles.scaleRow}>
                            <label htmlFor="sleep-duration">
                                Sleep duration <small>(hours, 0–24)</small>
                            </label>

                            <input
                                id="sleep-duration"
                                type="number"
                                min="0"
                                max="24"
                                step="0.5"
                                value={sleepDuration}
                                onChange={(e) =>
                                    setSleepDuration(e.target.value)
                                }
                                className={styles.sleepInput}
                            />
                        </div>

                        {(
                            [
                                ["Mood", mood, setMood],
                                ["Sleep quality", sleepQuality, setSleepQuality],
                                ["Stress", stress, setStress],
                                ["Fatigue", fatigue, setFatigue],
                            ] as const
                        ).map(([label, val, set], row) => (
                            <div key={label} className={styles.scaleRow}>
                                <span>
                                    {label} <small>1 low, 5 high</small>
                                </span>

                                <div
                                    className={styles.scale}
                                    role="group"
                                    aria-label={label}
                                >
                                    {[1, 2, 3, 4, 5].map((n) => (
                                        <button
                                            key={n}
                                            type="button"
                                            ref={
                                                row === 0 && n === 1
                                                    ? firstBtn
                                                    : undefined
                                            }
                                            aria-pressed={val === n}
                                            onClick={() => set(n)}
                                            className={cx(
                                                styles.scaleBtn,
                                                val === n && styles.scaleOn
                                            )}
                                        >
                                            {n}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}

                        <div className={styles.modalActions}>
                            <button
                                type="button"
                                className={styles.ghostBtn}
                                onClick={() => setModal(false)}
                                disabled={savingCheckIn}
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                className={styles.cta}
                                onClick={saveCheckIn}
                                disabled={savingCheckIn}
                            >
                                {savingCheckIn
                                    ? "Submitting..."
                                    : "Save check-in"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {toast && (
                <div className={styles.toast} role="status">
                    {toast}
                </div>
            )}
        </main>
    );
}
