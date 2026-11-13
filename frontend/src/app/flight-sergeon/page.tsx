"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
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
import styles from "./flight-surgeon.module.css";

/* ---------- fonts (same as crew and admin) ---------- */
const ui = Manrope({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const num = Space_Grotesk({ subsets: ["latin"], variable: "--font-num", display: "swap" });

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "meliora_access_token";
const IDENTITY_KEY = "meliora_identity";

/* ---------- types ---------- */
type Page = "Overview" | "Crew monitoring" | "Alerts" | "Assessments" | "Task assignment";
type RangeKey = "24 Hours" | "7 Days" | "30 Days";
type MetricId = "hr" | "spo2" | "bp" | "temp";
type Tone = "ok" | "warn" | "crit" | "neutral";

type Identity = { username: string; role: string; assigned_crew_ids: string[] };

type Measurement = {
    id: string;
    measurement_type: string;
    value_numeric: number | null;
    value_structured?: unknown;
    unit: string;
    measured_at: string;
    quality_status: string;
};

type Alert = {
    id: string;
    alert_identifier: string;
    crew_member_id: string;
    summary: string;
    priority: "INFO" | "CAUTION" | "CRITICAL" | "EMERGENCY";
    status: string;
    event_time: string;
    is_delayed: boolean;
};

type Assessment = {
    id: string;
    assessed_at: string;
    assessment_status: string;
    status_reason?: string | null;
    findings?: unknown[];
    input_evaluation?: {
        available_inputs?: string[];
        missing_inputs?: string[];
        invalid_inputs?: string[];
        stale_inputs?: string[];
    };
};

type ApiList<T> = { items: T[]; total: number };
type AssignedTask = { id: string; title: string; category: string; dueEnd: string; crew: string };

const PAGES: { name: Page; short: string; icon: string; title: string; blurb: string }[] = [
    { name: "Overview", short: "Overview", icon: "home", title: "Mission overview", blurb: "Triage assigned crew and review their latest readings" },
    { name: "Crew monitoring", short: "Crew", icon: "pulse", title: "Crew monitoring", blurb: "Recorded measurements for the selected crew member" },
    { name: "Alerts", short: "Alerts", icon: "bell", title: "Health alerts", blurb: "Notifications and events that need your attention" },
    { name: "Assessments", short: "Assess", icon: "check", title: "Health assessments", blurb: "Recorded evaluation status, inputs and findings" },
    { name: "Task assignment", short: "Tasks", icon: "plus", title: "Task assignment", blurb: "Create follow-up tasks for the selected crew member" },
];

const METRICS: { id: MetricId; title: string; unit: string; icon: string; type: string }[] = [
    { id: "hr", title: "Heart rate", unit: "bpm", icon: "heart", type: "heart_rate" },
    { id: "spo2", title: "Oxygen saturation", unit: "%", icon: "drop", type: "spo2" },
    { id: "bp", title: "Blood pressure", unit: "mmHg", icon: "pulse", type: "blood_pressure_systolic" },
    { id: "temp", title: "Body temperature", unit: "°C", icon: "thermo", type: "body_temperature" },
];

const RANGE_MS: Record<RangeKey, number> = {
    "24 Hours": 24 * 3600 * 1000,
    "7 Days": 7 * 24 * 3600 * 1000,
    "30 Days": 30 * 24 * 3600 * 1000,
};
const RANGE_KEYS = Object.keys(RANGE_MS) as RangeKey[];

const PRIORITY_RANK: Record<Alert["priority"], number> = { EMERGENCY: 4, CRITICAL: 3, CAUTION: 2, INFO: 1 };
const CATEGORIES = [
    { value: "WELLNESS_CHECK_IN", label: "Wellness check-in" },
    { value: "MEASUREMENT_REMINDER", label: "Measurement reminder" },
    { value: "FOLLOW_UP_ACTION", label: "Follow-up action" },
    { value: "GENERAL", label: "General" },
];

/* ---------- helpers ---------- */
const cx = (...a: (string | false | undefined)[]) => a.filter(Boolean).join(" ");

function formatDate(value?: string) {
    if (!value) return "—";
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? "—" : d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function words(value: string) {
    const s = value.replaceAll("_", " ").toLowerCase();
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function crewLabel(id: string, index: number) {
    return `Crew member ${index + 1} · ${id.slice(0, 8)}`;
}

function displayValue(m: Measurement) {
    if (m.value_numeric !== null && m.value_numeric !== undefined) return `${m.value_numeric} ${m.unit || ""}`.trim();
    if (m.value_structured !== undefined) return JSON.stringify(m.value_structured);
    return "No numeric value";
}

function alertLevel(p: Alert["priority"]): "critical" | "warning" | "info" {
    return p === "CRITICAL" || p === "EMERGENCY" ? "critical" : p === "CAUTION" ? "warning" : "info";
}

function qualityTone(q: string): Tone {
    const s = q.toLowerCase();
    if (s.includes("valid") && !s.includes("invalid")) return "ok";
    if (s.includes("invalid") || s.includes("reject")) return "crit";
    return "neutral";
}

function assessmentTone(status: string): { tone: Tone; label: string } {
    if (status === "assessed_no_findings") return { tone: "ok", label: "Assessed, no findings" };
    if (status === "needs_review") return { tone: "warn", label: "Needs review" };
    return { tone: "neutral", label: words(status) };
}

function toLocalInput(d: Date) {
    const p = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

/* ---------- icons ---------- */
const ICONS: Record<string, ReactNode> = {
    home: <><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M9 22V12h6v10" /></>,
    pulse: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></>,
    check: <><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>,
    plus: <path d="M12 5v14M5 12h14" />,
    heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z" />,
    drop: <path d="M12 2.7l5.7 5.7a8 8 0 1 1-11.4 0z" />,
    thermo: <path d="M14 14.8V4a2 2 0 0 0-4 0v10.8a4 4 0 1 0 4 0z" />,
    users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" /></>,
    refresh: <><path d="M23 4v6h-6M1 20v-6h6" /><path d="M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></>,
    chevron: <path d="M6 9l6 6 6-6" />,
};

function Icon({ name }: { name: string }) {
    return (
        <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true">
            {ICONS[name]}
        </svg>
    );
}

function Chip({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
    return <span className={cx(styles.chip, styles[tone])}>{children}</span>;
}

function Empty({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
    return (
        <div className={styles.empty}>
            <h3>{title}</h3>
            <p>{text}</p>
            {action}
        </div>
    );
}

function ChartTip({ active, payload, label, unit }: { active?: boolean; payload?: { value?: number }[]; label?: string | number; unit: string }) {
    if (!active || !payload?.length) return null;
    return (
        <div className={styles.tip}>
            <span>{label}</span>
            <b>{payload[0].value} {unit}</b>
        </div>
    );
}

/* ---------- page ---------- */
export default function FlightSurgeonPage() {
    const router = useRouter();

    const [page, setPage] = useState<Page>("Overview");
    const [dark, setDark] = useState(true);
    const [identity, setIdentity] = useState<Identity | null>(null);
    const [token, setToken] = useState("");
    const [selectedCrew, setSelectedCrew] = useState("");

    const [measurements, setMeasurements] = useState<Measurement[]>([]);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [assessments, setAssessments] = useState<Assessment[]>([]);
    const [roster, setRoster] = useState<Record<string, number | null>>({});

    const [loading, setLoading] = useState(false);
    const [pageError, setPageError] = useState("");
    const [dataErrors, setDataErrors] = useState<string[]>([]);
    const [acknowledging, setAcknowledging] = useState("");
    const [auto, setAuto] = useState(false);
    const [now, setNow] = useState("");
    const [toast, setToast] = useState("");

    const [metricId, setMetricId] = useState<MetricId>("hr");
    const [range, setRange] = useState<RangeKey>("7 Days");
    const [typeFilter, setTypeFilter] = useState("All");
    const [rowLimit, setRowLimit] = useState(12);
    const [alertFilter, setAlertFilter] = useState<"All" | "Needs action" | "Acknowledged" | "Closed">("All");
    const [openAssessment, setOpenAssessment] = useState<string | null>(null);

    const [taskTitle, setTaskTitle] = useState("");
    const [taskCategory, setTaskCategory] = useState("WELLNESS_CHECK_IN");
    const [dueStart, setDueStart] = useState("");
    const [dueEnd, setDueEnd] = useState("");
    const [creatingTask, setCreatingTask] = useState(false);
    const [taskMessage, setTaskMessage] = useState<{ ok: boolean; text: string } | null>(null);
    const [assigned, setAssigned] = useState<AssignedTask[]>([]);

    const crewIds = useMemo(() => identity?.assigned_crew_ids ?? [], [identity]);
    const info = PAGES.find((p) => p.name === page) ?? PAGES[0];

    /* ----- session ----- */
    const logout = useCallback(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(IDENTITY_KEY);
        router.replace("/login");
    }, [router]);

    useEffect(() => {
        const savedToken = sessionStorage.getItem(TOKEN_KEY);
        const savedIdentity = sessionStorage.getItem(IDENTITY_KEY);

        if (!savedToken || !savedIdentity) {
            router.replace("/login");
            return;
        }

        try {
            const parsed = JSON.parse(savedIdentity) as Identity;
            if (parsed.role !== "FLIGHT_SURGEON") {
                router.replace("/login");
                return;
            }
            const ids = Array.isArray(parsed.assigned_crew_ids) ? parsed.assigned_crew_ids : [];
            setToken(savedToken);
            setIdentity({ ...parsed, assigned_crew_ids: ids });
            if (ids.length > 0) setSelectedCrew(ids[0]);
        } catch {
            router.replace("/login");
        }
    }, [router]);

    /* ----- requests ----- */
    const request = useCallback(
        async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
            const response = await fetch(`${API_URL}/api/v1${path}`, {
                ...options,
                headers: {
                    Authorization: `Bearer ${token}`,
                    ...(options.body ? { "Content-Type": "application/json" } : {}),
                    ...options.headers,
                },
            });

            if (response.status === 401) {
                logout();
                throw new Error("Session expired. Please sign in again.");
            }

            if (!response.ok) {
                let message = `Request failed (${response.status})`;
                try {
                    const body = await response.json();
                    if (typeof body?.detail === "string") message = body.detail;
                    else if (Array.isArray(body?.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
                } catch {
                    /* keep the default message */
                }
                throw new Error(message);
            }

            if (response.status === 204) return null as T;
            return response.json() as Promise<T>;
        },
        [token, logout]
    );

    const loadCrewData = useCallback(async () => {
        if (!selectedCrew || !token) return;

        setLoading(true);
        setPageError("");

        const crew = encodeURIComponent(selectedCrew);
        const [m, a, s] = await Promise.allSettled([
            request<ApiList<Measurement>>(`/measurements?crew_id=${crew}&limit=100`),
            request<ApiList<Alert>>(`/alerts?crew_member_id=${crew}&limit=50`),
            request<ApiList<Assessment>>(`/assessments?crew_id=${crew}&limit=30`),
        ]);

        const errors: string[] = [];
        if (m.status === "fulfilled") setMeasurements(m.value.items ?? []);
        else { setMeasurements([]); errors.push("Measurements could not be loaded."); }

        if (a.status === "fulfilled") setAlerts(a.value.items ?? []);
        else { setAlerts([]); errors.push("Alerts could not be loaded."); }

        if (s.status === "fulfilled") setAssessments(s.value.items ?? []);
        else { setAssessments([]); errors.push("Assessments could not be loaded."); }

        setDataErrors(errors);
        setLoading(false);
    }, [request, selectedCrew, token]);

    const loadRoster = useCallback(async () => {
        if (!token || crewIds.length === 0) return;

        const ids = crewIds.slice(0, 12);
        const results = await Promise.allSettled(
            ids.map((id) => request<ApiList<Alert>>(`/alerts?crew_member_id=${encodeURIComponent(id)}&limit=50`))
        );

        const next: Record<string, number | null> = {};
        ids.forEach((id, i) => {
            const r = results[i];
            next[id] = r.status === "fulfilled" ? (r.value.items ?? []).filter((x) => x.status === "open" || x.status === "assigned").length : null;
        });
        setRoster(next);
    }, [request, token, crewIds]);

    useEffect(() => {
        loadCrewData();
    }, [loadCrewData]);

    useEffect(() => {
        loadRoster();
    }, [loadRoster]);

    useEffect(() => {
        setRowLimit(12);
        setTypeFilter("All");
        setOpenAssessment(null);
    }, [selectedCrew]);

    useEffect(() => {
        if (!auto) return;
        const id = setInterval(() => {
            loadCrewData();
            loadRoster();
        }, 30000);
        return () => clearInterval(id);
    }, [auto, loadCrewData, loadRoster]);

    useEffect(() => {
        const tick = () => setNow(new Date().toISOString().slice(11, 19) + " UTC");
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, []);

    useEffect(() => {
        if (!toast) return;
        const id = setTimeout(() => setToast(""), 3200);
        return () => clearTimeout(id);
    }, [toast]);

    async function refreshAll() {
        await Promise.all([loadCrewData(), loadRoster()]);
        setToast("Data refreshed");
    }

    async function acknowledgeAlert(alertId: string) {
        setAcknowledging(alertId);
        setPageError("");
        try {
            await request(`/alerts/${alertId}/acknowledge`, { method: "POST", body: JSON.stringify({}) });
            await Promise.all([loadCrewData(), loadRoster()]);
            setToast("Alert acknowledged");
        } catch (error) {
            setPageError(error instanceof Error ? error.message : "Could not acknowledge alert.");
        } finally {
            setAcknowledging("");
        }
    }

    function quickWindow(hours: number) {
        const start = new Date();
        setDueStart(toLocalInput(start));
        setDueEnd(toLocalInput(new Date(start.getTime() + hours * 3600 * 1000)));
    }

    async function createTask(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setTaskMessage(null);

        if (!selectedCrew) {
            setTaskMessage({ ok: false, text: "Select an assigned crew member first." });
            return;
        }
        if (!taskTitle.trim()) {
            setTaskMessage({ ok: false, text: "Enter a task title." });
            return;
        }
        if (new Date(dueEnd) <= new Date(dueStart)) {
            setTaskMessage({ ok: false, text: "The due end must be later than the due start." });
            return;
        }

        setCreatingTask(true);
        try {
            await request("/tasks", {
                method: "POST",
                body: JSON.stringify({
                    crew_member_id: selectedCrew,
                    title: taskTitle.trim(),
                    category: taskCategory,
                    due_start: new Date(dueStart).toISOString(),
                    due_end: new Date(dueEnd).toISOString(),
                    task_definition_id: null,
                }),
            });

            const index = crewIds.indexOf(selectedCrew);
            setAssigned((cur) => [
                { id: String(Date.now()), title: taskTitle.trim(), category: taskCategory, dueEnd, crew: crewLabel(selectedCrew, index) },
                ...cur,
            ].slice(0, 6));
            setTaskTitle("");
            setTaskMessage({ ok: true, text: "Task assigned successfully." });
            setToast("Task assigned");
        } catch (error) {
            setTaskMessage({ ok: false, text: error instanceof Error ? error.message : "Could not assign task." });
        } finally {
            setCreatingTask(false);
        }
    }

    /* ----- derived data ----- */
    const sortedAlerts = useMemo(
        () =>
            [...alerts].sort(
                (a, b) =>
                    PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority] ||
                    new Date(b.event_time).getTime() - new Date(a.event_time).getTime()
            ),
        [alerts]
    );
    const openAlerts = alerts.filter((a) => a.status === "open" || a.status === "assigned");
    const delayedCount = alerts.filter((a) => a.is_delayed).length;
    const topAlert = [...openAlerts].sort((a, b) => PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority])[0];

    const shownAlerts = sortedAlerts.filter((a) => {
        if (alertFilter === "All") return true;
        if (alertFilter === "Needs action") return a.status === "open" || a.status === "assigned";
        if (alertFilter === "Acknowledged") return a.status === "acknowledged";
        return a.status === "resolved" || a.status === "dismissed";
    });

    const sortedMeasurements = useMemo(
        () => [...measurements].sort((a, b) => new Date(b.measured_at).getTime() - new Date(a.measured_at).getTime()),
        [measurements]
    );
    const typesPresent = useMemo(() => Array.from(new Set(measurements.map((m) => m.measurement_type))).sort(), [measurements]);
    const filteredMeasurements = sortedMeasurements.filter((m) => typeFilter === "All" || m.measurement_type === typeFilter);

    const latestByType = useMemo(() => {
        const latest: Record<string, Measurement> = {};
        for (const m of sortedMeasurements) {
            if (m.value_numeric !== null && !latest[m.measurement_type]) latest[m.measurement_type] = m;
        }
        return latest;
    }, [sortedMeasurements]);

    const metric = METRICS.find((m) => m.id === metricId) ?? METRICS[0];

    const series = useMemo(() => {
        const cutoff = Date.now() - RANGE_MS[range];
        return measurements
            .filter((m) => m.measurement_type === metric.type && m.value_numeric !== null && new Date(m.measured_at).getTime() >= cutoff)
            .sort((a, b) => new Date(a.measured_at).getTime() - new Date(b.measured_at).getTime())
            .map((m) => ({ label: formatDate(m.measured_at), value: m.value_numeric as number }));
    }, [measurements, metric, range]);

    const latestAssessment = [...assessments].sort(
        (a, b) => new Date(b.assessed_at).getTime() - new Date(a.assessed_at).getTime()
    )[0];

    function metricValue(id: MetricId) {
        const find = (t: string) => latestByType[t]?.value_numeric;
        if (id === "hr") return find("heart_rate")?.toFixed(0) ?? "--";
        if (id === "spo2") return find("spo2")?.toFixed(0) ?? "--";
        if (id === "temp") return find("body_temperature")?.toFixed(1) ?? "--";
        const s = find("blood_pressure_systolic");
        const d = find("blood_pressure_diastolic");
        return s != null && d != null ? `${s.toFixed(0)}/${d.toFixed(0)}` : s != null ? s.toFixed(0) : "--";
    }

    /* ----- reusable blocks ----- */
    const crewPicker = (
        <section className={styles.pickBar} aria-label="Crew selection">
            <label htmlFor="crew-select">Viewing crew member</label>
            {crewIds.length > 0 ? (
                <select id="crew-select" className={styles.select} value={selectedCrew} onChange={(e) => setSelectedCrew(e.target.value)}>
                    {crewIds.map((id, i) => (
                        <option key={id} value={id}>{crewLabel(id, i)}</option>
                    ))}
                </select>
            ) : (
                <span className={styles.pickNone}>No crew assigned</span>
            )}
            <Chip>{crewIds.length} assigned</Chip>
        </section>
    );

    const rangePills = (
        <div className={styles.pills} role="group" aria-label="Time range">
            {RANGE_KEYS.map((r) => (
                <button key={r} type="button" aria-pressed={range === r} onClick={() => setRange(r)} className={cx(styles.pill, range === r && styles.pillActive)}>
                    {r}
                </button>
            ))}
        </div>
    );

    const chart =
        loading && measurements.length === 0 ? (
            <Empty title="Loading readings" text="Retrieving measurements for this crew member." />
        ) : series.length < 2 ? (
            <Empty title="Not enough readings" text="At least two readings in this time range are needed to draw a trend." />
        ) : (
            <div className={styles.chartBox}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={series} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                        <defs>
                            <linearGradient id="fsFill" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="#00695F" stopOpacity={0.3} />
                                <stop offset="100%" stopColor="#00695F" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid vertical={false} stroke="rgba(58,88,87,0.2)" />
                        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#3A5857", fontSize: 12 }} minTickGap={28} />
                        <YAxis domain={["auto", "auto"]} tickLine={false} axisLine={false} width={46} tick={{ fill: "#3A5857", fontSize: 12 }} />
                        <Tooltip content={<ChartTip unit={metric.unit} />} cursor={{ stroke: "#00695F", strokeDasharray: "4 4" }} />
                        <Area type="monotone" dataKey="value" stroke="#00695F" strokeWidth={3} fill="url(#fsFill)" dot={{ r: 3, fill: "#00695F", strokeWidth: 0 }} activeDot={{ r: 6 }} />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        );

    const alertRow = (a: Alert, withAction: boolean) => (
        <li key={a.id} className={styles.alertItem}>
            <i className={cx(styles.alertBar, styles[alertLevel(a.priority)])} />
            <div className={styles.alertBody}>
                <p className={styles.alertTitle}>{a.summary}</p>
                <p className={styles.alertMeta}>
                    {formatDate(a.event_time)} · {words(a.status)}
                    <Chip tone={alertLevel(a.priority) === "critical" ? "crit" : alertLevel(a.priority) === "warning" ? "warn" : "neutral"}>{a.priority}</Chip>
                    {a.is_delayed && <Chip>Delayed sync</Chip>}
                </p>
                <p className={styles.alertId}>{a.alert_identifier}</p>
            </div>
            {withAction && a.status === "open" && (
                <button type="button" className={styles.ackBtn} onClick={() => acknowledgeAlert(a.id)} disabled={acknowledging !== ""}>
                    {acknowledging === a.id ? "Saving..." : "Acknowledge"}
                </button>
            )}
        </li>
    );

    const initials = (identity?.username ?? "FS").slice(0, 2).toUpperCase();

    if (!identity) {
        return (
            <main className={cx(styles.dashboard, ui.variable, num.variable)} data-theme="dark">
                <div className={styles.loadingScreen}>
                    <div className={styles.loader} />
                    <p>Opening flight surgeon workspace...</p>
                </div>
            </main>
        );
    }

    return (
        <main className={cx(styles.dashboard, ui.variable, num.variable)} data-theme={dark ? "dark" : "light"}>
            <div className={styles.shell}>
                {/* SIDEBAR */}
                <aside className={styles.sidebar}>
                    <div className={styles.brand}>
                        <h2>Meliora</h2>
                        <span>Flight surgeon</span>
                    </div>

                    <nav aria-label="Main">
                        {PAGES.map((p) => (
                            <button
                                key={p.name}
                                type="button"
                                onClick={() => setPage(p.name)}
                                aria-current={page === p.name ? "page" : undefined}
                                className={cx(styles.navItem, page === p.name && styles.active)}
                            >
                                <Icon name={p.icon} />
                                <span className={styles.navFull}>{p.name}</span>
                                <span className={styles.navShort}>{p.short}</span>
                                {p.name === "Alerts" && openAlerts.length > 0 && <span className={styles.navBadge}>{openAlerts.length}</span>}
                            </button>
                        ))}
                    </nav>

                    <div className={styles.sidebarBottom}>
                        <b>{identity.username}</b>
                        <span>Flight surgeon</span>
                        <span>Engineering prototype. Not a certified medical device.</span>
                        <button type="button" className={styles.logout} onClick={logout}>
                            <Icon name="logout" /> Sign out
                        </button>
                    </div>
                </aside>

                {/* MAIN */}
                <section className={styles.main}>
                    <header className={styles.header}>
                        <div>
                            <p className={styles.crumb}>Flight surgeon portal</p>
                            <h2>{info.title}</h2>
                        </div>
                        <div className={styles.tools}>
                            <span className={styles.clock}>{now}</span>
                            <button type="button" role="switch" aria-checked={auto} aria-label="Auto refresh" onClick={() => setAuto(!auto)} className={cx(styles.switchBtn, auto && styles.switchOn)}>
                                <span className={styles.switchKnob} />
                                <span className={styles.switchLabel}>Auto refresh</span>
                            </button>
                            <button type="button" className={cx(styles.iconBtn, loading && styles.spinning)} onClick={refreshAll} disabled={loading || !selectedCrew} aria-label="Refresh data">
                                <Icon name="refresh" />
                            </button>
                            <button type="button" className={styles.iconBtn} onClick={() => setDark(!dark)} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
                                <Icon name={dark ? "sun" : "moon"} />
                            </button>
                            <button type="button" className={cx(styles.iconBtn, styles.mobileOnly)} onClick={logout} aria-label="Sign out">
                                <Icon name="logout" />
                            </button>
                            <div className={styles.profile}>
                                <div className={styles.avatar}>{initials}</div>
                                <span>Flight surgeon</span>
                            </div>
                        </div>
                    </header>

                    <div className={styles.content} key={page}>
                        <div className={styles.hero}>
                            <div>
                                <h1>{page === "Overview" ? "Flight surgeon dashboard" : info.title}</h1>
                                <p>{info.blurb}</p>
                            </div>
                            <span className={styles.liveTag}>Live API</span>
                        </div>

                        {pageError && <div className={styles.error} role="alert">{pageError}</div>}
                        {dataErrors.length > 0 && <div className={styles.warningBanner} role="status">Some records could not be loaded: {dataErrors.join(" ")}</div>}

                        {crewPicker}

                        {crewIds.length === 0 ? (
                            <Empty title="No crew assigned" text="No crew members are assigned to this account. Ask an administrator to configure your crew access." />
                        ) : (
                            <>
                                {/* ===== OVERVIEW ===== */}
                                {page === "Overview" && (
                                    <>
                                        <section className={styles.card}>
                                            <div className={styles.cardHead}>
                                                <div>
                                                    <h3>Crew roster</h3>
                                                    <p>Open alerts per crew member. Select one to review.</p>
                                                </div>
                                            </div>
                                            <div className={styles.roster}>
                                                {crewIds.slice(0, 12).map((id, i) => {
                                                    const count = roster[id];
                                                    return (
                                                        <button key={id} type="button" aria-pressed={selectedCrew === id} onClick={() => setSelectedCrew(id)}
                                                            className={cx(styles.rosterCard, selectedCrew === id && styles.rosterActive)}>
                                                            <span className={styles.rosterIcon}><Icon name="users" /></span>
                                                            <span className={styles.rosterText}>
                                                                <b>Crew member {i + 1}</b>
                                                                <small>{id.slice(0, 8)}</small>
                                                            </span>
                                                            {count === undefined ? <Chip>Checking</Chip> : count === null ? <Chip>Unavailable</Chip> : count > 0 ? <Chip tone="warn">{count} open</Chip> : <Chip tone="ok">No open alerts</Chip>}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        </section>

                                        <div className={styles.metricGrid}>
                                            {METRICS.map((m) => (
                                                <button key={m.id} type="button" aria-pressed={metricId === m.id} onClick={() => setMetricId(m.id)}
                                                    className={cx(styles.metricCard, metricId === m.id && styles.metricActive)}>
                                                    <span className={styles.metricTop}>
                                                        <span className={styles.metricIcon}><Icon name={m.icon} /></span>
                                                        <span className={styles.metricName}>{m.title}</span>
                                                    </span>
                                                    <span className={styles.metricValue}>{metricValue(m.id)} <small>{m.unit}</small></span>
                                                    <Chip>{metricValue(m.id) === "--" ? "No reading" : "Latest reading"}</Chip>
                                                </button>
                                            ))}
                                        </div>

                                        <div className={styles.row2}>
                                            <section className={styles.card}>
                                                <div className={styles.cardHead}>
                                                    <div>
                                                        <h3>{metric.title} trend</h3>
                                                        <p>Recorded readings · {metric.unit}</p>
                                                    </div>
                                                    {rangePills}
                                                </div>
                                                {chart}
                                            </section>

                                            <section className={styles.card}>
                                                <h3>Triage summary</h3>
                                                <dl className={styles.kv}>
                                                    <div><dt>Open alerts</dt><dd>{openAlerts.length}</dd></div>
                                                    <div>
                                                        <dt>Highest priority</dt>
                                                        <dd>{topAlert ? <Chip tone={alertLevel(topAlert.priority) === "critical" ? "crit" : alertLevel(topAlert.priority) === "warning" ? "warn" : "neutral"}>{topAlert.priority}</Chip> : "None"}</dd>
                                                    </div>
                                                    <div><dt>Delayed syncs</dt><dd>{delayedCount}</dd></div>
                                                    <div><dt>Measurements loaded</dt><dd>{measurements.length}</dd></div>
                                                    <div>
                                                        <dt>Latest assessment</dt>
                                                        <dd>{latestAssessment ? <Chip tone={assessmentTone(latestAssessment.assessment_status).tone}>{assessmentTone(latestAssessment.assessment_status).label}</Chip> : "None"}</dd>
                                                    </div>
                                                </dl>
                                                <button type="button" className={styles.linkBtn} onClick={() => setPage("Alerts")}>Review alerts</button>
                                            </section>
                                        </div>

                                        <section className={styles.card}>
                                            <div className={styles.cardHead}>
                                                <h3>Alerts needing action</h3>
                                                <button type="button" className={styles.linkBtn} onClick={() => setPage("Alerts")}>View all</button>
                                            </div>
                                            {openAlerts.length === 0 ? (
                                                <p className={styles.quiet}>No open alerts for this crew member.</p>
                                            ) : (
                                                <ul className={styles.alertList}>
                                                    {[...openAlerts].sort((a, b) => PRIORITY_RANK[b.priority] - PRIORITY_RANK[a.priority]).slice(0, 3).map((a) => alertRow(a, true))}
                                                </ul>
                                            )}
                                        </section>
                                    </>
                                )}

                                {/* ===== CREW MONITORING ===== */}
                                {page === "Crew monitoring" && (
                                    <>
                                        <section className={styles.card}>
                                            <div className={styles.cardHead}>
                                                <div>
                                                    <h3>{metric.title}</h3>
                                                    <p>Pick a measurement to chart</p>
                                                </div>
                                                {rangePills}
                                            </div>
                                            <div className={styles.pills} role="group" aria-label="Choose a measurement">
                                                {METRICS.map((m) => (
                                                    <button key={m.id} type="button" aria-pressed={metricId === m.id} onClick={() => setMetricId(m.id)} className={cx(styles.pill, metricId === m.id && styles.pillActive)}>
                                                        {m.title}
                                                    </button>
                                                ))}
                                            </div>
                                            {chart}
                                        </section>

                                        <section className={styles.card}>
                                            <div className={styles.cardHead}>
                                                <div>
                                                    <h3>Recent measurements</h3>
                                                    <p>Readings are shown as recorded. They are not diagnoses.</p>
                                                </div>
                                                <Chip>{filteredMeasurements.length} records</Chip>
                                            </div>

                                            {typesPresent.length > 0 && (
                                                <div className={styles.pills} role="group" aria-label="Filter by type">
                                                    {["All", ...typesPresent].map((t) => (
                                                        <button key={t} type="button" aria-pressed={typeFilter === t} onClick={() => { setTypeFilter(t); setRowLimit(12); }} className={cx(styles.pill, typeFilter === t && styles.pillActive)}>
                                                            {t === "All" ? "All types" : words(t)}
                                                        </button>
                                                    ))}
                                                </div>
                                            )}

                                            {loading && measurements.length === 0 ? (
                                                <p className={styles.quiet}>Loading measurements...</p>
                                            ) : filteredMeasurements.length === 0 ? (
                                                <Empty title="No measurements" text="No measurement records are available for this crew member." />
                                            ) : (
                                                <>
                                                    <div className={styles.tableWrap}>
                                                        <table className={styles.dataTable}>
                                                            <thead>
                                                                <tr><th>Measurement</th><th>Value</th><th>Measured at</th><th>Quality</th></tr>
                                                            </thead>
                                                            <tbody>
                                                                {filteredMeasurements.slice(0, rowLimit).map((item) => (
                                                                    <tr key={item.id}>
                                                                        <td data-label="Measurement">{words(item.measurement_type)}</td>
                                                                        <td className={styles.value} data-label="Value">{displayValue(item)}</td>
                                                                        <td data-label="Measured at">{formatDate(item.measured_at)}</td>
                                                                        <td data-label="Quality"><Chip tone={qualityTone(item.quality_status)}>{words(item.quality_status)}</Chip></td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    {filteredMeasurements.length > rowLimit && (
                                                        <button type="button" className={styles.ghost} onClick={() => setRowLimit((n) => n + 12)}>
                                                            Show more ({filteredMeasurements.length - rowLimit} left)
                                                        </button>
                                                    )}
                                                </>
                                            )}
                                        </section>
                                    </>
                                )}

                                {/* ===== ALERTS ===== */}
                                {page === "Alerts" && (
                                    <>
                                        <div className={styles.pills} role="group" aria-label="Filter alerts">
                                            {(["All", "Needs action", "Acknowledged", "Closed"] as const).map((f) => (
                                                <button key={f} type="button" aria-pressed={alertFilter === f} onClick={() => setAlertFilter(f)} className={cx(styles.pill, alertFilter === f && styles.pillActive)}>
                                                    {f}
                                                </button>
                                            ))}
                                        </div>
                                        {loading && alerts.length === 0 ? (
                                            <Empty title="Loading alerts" text="Retrieving notifications for this crew member." />
                                        ) : shownAlerts.length === 0 ? (
                                            <Empty title={alerts.length === 0 ? "No alerts" : "Nothing in this filter"} text={alerts.length === 0 ? "No alerts are available for this crew member." : "Try another filter to see the rest of the alerts."} />
                                        ) : (
                                            <section className={styles.card}>
                                                <ul className={styles.alertList}>{shownAlerts.map((a) => alertRow(a, true))}</ul>
                                                <p className={styles.note}>Sorted by priority, then by event time. Delayed syncs are historical events, not new emergencies.</p>
                                            </section>
                                        )}
                                    </>
                                )}

                                {/* ===== ASSESSMENTS ===== */}
                                {page === "Assessments" && (
                                    loading && assessments.length === 0 ? (
                                        <Empty title="Loading assessments" text="Retrieving evaluation records for this crew member." />
                                    ) : assessments.length === 0 ? (
                                        <Empty title="No assessments" text="No assessment records are available for this crew member." />
                                    ) : (
                                        <div className={styles.acc}>
                                            {assessments.map((a) => {
                                                const t = assessmentTone(a.assessment_status);
                                                const open = openAssessment === a.id;
                                                const ev = a.input_evaluation;
                                                const groups: [string, string[] | undefined][] = [
                                                    ["Available inputs", ev?.available_inputs],
                                                    ["Missing inputs", ev?.missing_inputs],
                                                    ["Invalid inputs", ev?.invalid_inputs],
                                                    ["Stale inputs", ev?.stale_inputs],
                                                ];
                                                return (
                                                    <div key={a.id} className={cx(styles.accItem, open && styles.accOpen)}>
                                                        <button type="button" className={styles.accHead} aria-expanded={open} onClick={() => setOpenAssessment(open ? null : a.id)}>
                                                            <span><b>{formatDate(a.assessed_at)}</b><small>{a.findings?.length ?? 0} findings</small></span>
                                                            <Chip tone={t.tone}>{t.label}</Chip>
                                                            <span className={styles.chev}><Icon name="chevron" /></span>
                                                        </button>
                                                        {open && (
                                                            <div className={styles.accBody}>
                                                                <p>{a.status_reason || "No additional status explanation provided."}</p>
                                                                {groups.map(([label, list]) => (
                                                                    <div key={label} className={styles.inputGroup}>
                                                                        <span>{label}</span>
                                                                        <div className={styles.tags}>
                                                                            {list && list.length ? list.map((x) => <span key={x} className={styles.tag}>{words(x)}</span>) : <em>None</em>}
                                                                        </div>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                            <p className={styles.note}>Status and findings reflect the backend’s recorded evaluation. Statistical flags are not medical diagnoses, and “no findings” is not a clinical clearance.</p>
                                        </div>
                                    )
                                )}

                                {/* ===== TASK ASSIGNMENT ===== */}
                                {page === "Task assignment" && (
                                    <div className={styles.row2}>
                                        <section className={styles.card}>
                                            <div className={styles.cardHead}>
                                                <div>
                                                    <h3>Assign a crew task</h3>
                                                    <p>For {selectedCrew ? crewLabel(selectedCrew, crewIds.indexOf(selectedCrew)) : "the selected crew member"}</p>
                                                </div>
                                            </div>
                                            <form className={styles.taskForm} onSubmit={createTask}>
                                                <label>
                                                    Task title
                                                    <input value={taskTitle} onChange={(e) => setTaskTitle(e.target.value)} placeholder="e.g. Complete wellness check-in" required maxLength={200} />
                                                </label>
                                                <label>
                                                    Category
                                                    <select value={taskCategory} onChange={(e) => setTaskCategory(e.target.value)}>
                                                        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                                                    </select>
                                                </label>
                                                <div className={styles.quick}>
                                                    <span>Quick window from now</span>
                                                    {[1, 4, 24].map((h) => (
                                                        <button key={h} type="button" className={styles.pill} onClick={() => quickWindow(h)}>{h} {h === 1 ? "hour" : "hours"}</button>
                                                    ))}
                                                </div>
                                                <div className={styles.dateGrid}>
                                                    <label>
                                                        Due start
                                                        <input type="datetime-local" value={dueStart} onChange={(e) => setDueStart(e.target.value)} required />
                                                    </label>
                                                    <label>
                                                        Due end
                                                        <input type="datetime-local" value={dueEnd} onChange={(e) => setDueEnd(e.target.value)} required />
                                                    </label>
                                                </div>
                                                <button className={styles.cta} type="submit" disabled={creatingTask || !selectedCrew}>
                                                    {creatingTask ? "Assigning..." : "Assign task"}
                                                </button>
                                                {taskMessage && (
                                                    <p className={cx(styles.formMessage, taskMessage.ok ? styles.msgOk : styles.msgBad)} role="status">{taskMessage.text}</p>
                                                )}
                                            </form>
                                        </section>

                                        <section className={styles.card}>
                                            <h3>Assigned this session</h3>
                                            {assigned.length === 0 ? (
                                                <p className={styles.quiet}>Tasks you assign appear here until you leave this page.</p>
                                            ) : (
                                                <ul className={styles.assignedList}>
                                                    {assigned.map((t) => (
                                                        <li key={t.id}>
                                                            <b>{t.title}</b>
                                                            <small>{t.crew}</small>
                                                            <small>{CATEGORIES.find((c) => c.value === t.category)?.label} · due {formatDate(t.dueEnd)}</small>
                                                        </li>
                                                    ))}
                                                </ul>
                                            )}
                                        </section>
                                    </div>
                                )}
                            </>
                        )}

                        <footer className={styles.footer}>Meliora · Astronaut health monitoring · Flight surgeon workspace</footer>
                    </div>
                </section>
            </div>

            {toast && <div className={styles.toast} role="status">{toast}</div>}
        </main>
    );
}
