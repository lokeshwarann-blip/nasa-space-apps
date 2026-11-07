"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Manrope, Space_Grotesk } from "next/font/google";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ReferenceArea,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import styles from "./dashboard.module.css";

/* ---------- fonts ---------- */
const ui = Manrope({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const num = Space_Grotesk({ subsets: ["latin"], variable: "--font-num", display: "swap" });

/* ---------- types & data ---------- */
type Page = "Overview" | "Vital Signs" | "Health Trends" | "Assessments" | "Alerts";
type RangeKey = "24 Hours" | "7 Days" | "30 Days";
type MetricId = "hr" | "spo2" | "bp" | "temp";

interface Metric {
    id: MetricId;
    title: string;
    unit: string;
    description: string;
    icon: string;
    value: string;
    current: number;
    baseline: [number, number];
    base: number;
    amp: number;
    decimals: number;
}

interface AlertItem {
    id: string;
    title: string;
    crew: string;
    time: string;
    level: "critical" | "warning" | "info";
    status: "open" | "acknowledged";
    delayed: boolean;
}

const PAGES: { name: Page; icon: string; title: string; blurb: string }[] = [
    { name: "Overview", icon: "home", title: "Mission overview", blurb: "Your health at a glance" },
    { name: "Vital Signs", icon: "pulse", title: "Vital signs", blurb: "Current readings against your own baseline" },
    { name: "Health Trends", icon: "trend", title: "Health trends", blurb: "How your readings change over time" },
    { name: "Assessments", icon: "check", title: "Health assessments", blurb: "Review assessment records and their status" },
    { name: "Alerts", icon: "bell", title: "Health alerts", blurb: "Notifications from health monitoring" },
];

const METRICS: Metric[] = [
    { id: "hr", title: "Heart rate", unit: "bpm", description: "Beats per minute at rest and during activity.", icon: "heart", value: "72", current: 72, baseline: [58, 78], base: 72, amp: 5, decimals: 0 },
    { id: "spo2", title: "Oxygen saturation", unit: "%", description: "Share of oxygen carried in the blood.", icon: "drop", value: "96", current: 96, baseline: [97, 99], base: 97, amp: 1.2, decimals: 0 },
    { id: "bp", title: "Blood pressure", unit: "mmHg", description: "Systolic and diastolic pressure. Charts show systolic.", icon: "pulse", value: "118/76", current: 118, baseline: [100, 130], base: 118, amp: 5, decimals: 0 },
    { id: "temp", title: "Body temperature", unit: "°C", description: "Core temperature changes through the day.", icon: "thermo", value: "36.7", current: 36.7, baseline: [36.4, 37.1], base: 36.7, amp: 0.2, decimals: 1 },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const RANGES: Record<RangeKey, { n: number; label: (i: number) => string }> = {
    "24 Hours": { n: 12, label: (i) => `${String(i * 2).padStart(2, "0")}:00` },
    "7 Days": { n: 7, label: (i) => DAYS[i] },
    "30 Days": { n: 10, label: (i) => `Day ${i * 3 + 1}` },
};
const RANGE_KEYS = Object.keys(RANGES) as RangeKey[];

const INITIAL_ALERTS: AlertItem[] = [
    { id: "a1", title: "Blood oxygen below your baseline", crew: "Cdr. Reyes", time: "09:42 UTC", level: "warning", status: "open", delayed: false },
    { id: "a2", title: "Heart rate stayed elevated for 20 minutes", crew: "Cdr. Reyes", time: "08:15 UTC", level: "critical", status: "open", delayed: false },
    { id: "a3", title: "Temperature reading synced after signal loss", crew: "Cdr. Reyes", time: "06:03 UTC", level: "info", status: "acknowledged", delayed: true },
];

const INITIAL_TASKS = [
    { id: "t1", title: "Morning wellness check-in", time: "10:00", done: true },
    { id: "t2", title: "Blood pressure reading", time: "14:00", done: false },
    { id: "t3", title: "Symptom report", time: "20:00", done: false },
];

const ASSESSMENTS = [
    {
        id: "s1", title: "Cardiovascular review", status: "Partially assessed", tone: "warning", time: "Today, 06:00 UTC",
        summary: "Heart rate and blood pressure were assessed. Blood oxygen had too few recent readings.",
        details: ["Heart rate: compared with your personal baseline", "Blood pressure: compared with your personal baseline", "Blood oxygen: not enough recent readings to assess"],
    },
    {
        id: "s2", title: "Respiratory review", status: "Insufficient evidence", tone: "muted", time: "Yesterday, 18:00 UTC",
        summary: "There were not enough valid readings to reach a result. This is not the same as healthy.",
        details: ["Fewer than 10 readings available for a baseline", "Latest reading is older than the freshness limit"],
    },
];

/* ---------- helpers ---------- */
const cx = (...a: (string | false | undefined)[]) => a.filter(Boolean).join(" ");

function makeSeries(m: Metric, range: RangeKey) {
    const r = RANGES[range];
    return Array.from({ length: r.n }, (_, i) => {
        const v = m.base + m.amp * Math.sin(i * 1.3 + m.base) + m.amp * 0.4 * Math.cos(i * 0.7);
        return { label: r.label(i), value: Number(v.toFixed(m.decimals)) };
    });
}

function statusOf(m: Metric): { label: string; tone: "normal" | "warning" } {
    if (m.current < m.baseline[0]) return { label: "Below baseline", tone: "warning" };
    if (m.current > m.baseline[1]) return { label: "Above baseline", tone: "warning" };
    return { label: "Within baseline", tone: "normal" };
}

/* ---------- small components ---------- */
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
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
    close: <path d="M18 6L6 18M6 6l12 12" />,
    chevron: <path d="M6 9l6 6 6-6" />,
};

function Icon({ name }: { name: string }) {
    return (
        <svg className={styles.icon} viewBox="0 0 24 24" aria-hidden="true">
            {ICONS[name]}
        </svg>
    );
}

function Spark({ data }: { data: number[] }) {
    const w = 96, h = 36;
    const lo = Math.min(...data), span = Math.max(...data) - lo || 1;
    const pts = data.map((v, i) => `${((i * w) / (data.length - 1)).toFixed(1)},${(h - 3 - ((v - lo) / span) * (h - 6)).toFixed(1)}`);
    return (
        <svg viewBox={`0 0 ${w} ${h}`} className={styles.spark} aria-hidden="true">
            <polyline points={pts.join(" ")} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

function Gauge({ value, average, max }: { value: number; average: number; max: number }) {
    const ring = (r: number, n: number, filled: number, on: string) =>
        Array.from({ length: n }, (_, i) => {
            const a = (i / n) * Math.PI * 2 - Math.PI / 2;
            const p = (d: number) => (100 + d * Math.cos(a)).toFixed(1);
            const q = (d: number) => (100 + d * Math.sin(a)).toFixed(1);
            return (
                <line key={`${r}-${i}`} x1={p(r - 4)} y1={q(r - 4)} x2={p(r + 4)} y2={q(r + 4)}
                    strokeWidth="4" strokeLinecap="round" className={i < filled ? on : styles.segOff} />
            );
        });
    return (
        <svg viewBox="0 0 200 200" className={styles.gaugeSvg} role="img" aria-label={`Heart rate ${value} beats per minute`}>
            {ring(88, 56, Math.round((56 * value) / max), styles.segOn)}
            {ring(70, 44, Math.round((44 * average) / max), styles.segAvg)}
        </svg>
    );
}

function RangeBar({ m }: { m: Metric }) {
    const [lo, hi] = m.baseline;
    const pad = (hi - lo) * 0.7;
    const min = lo - pad, span = hi - lo + pad * 2;
    const pos = Math.min(100, Math.max(0, ((m.current - min) / span) * 100));
    return (
        <div className={styles.rangeBar} aria-hidden="true">
            <span className={styles.rangeBand} style={{ left: `${((lo - min) / span) * 100}%`, width: `${((hi - lo) / span) * 100}%` }} />
            <span className={styles.rangeDot} style={{ left: `${pos}%` }} />
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
    const [demo, setDemo] = useState(true);
    const [dark, setDark] = useState(true);
    const [alerts, setAlerts] = useState(INITIAL_ALERTS);
    const [alertFilter, setAlertFilter] = useState<"All" | "Open" | "Acknowledged">("All");
    const [tasks, setTasks] = useState(INITIAL_TASKS);
    const [openAssessment, setOpenAssessment] = useState<string | null>(null);
    const [modal, setModal] = useState(false);
    const [mood, setMood] = useState(4);
    const [fatigue, setFatigue] = useState(2);
    const [toast, setToast] = useState("");
    const [now, setNow] = useState("");
    const firstBtn = useRef<HTMLButtonElement>(null);

    const metric = METRICS.find((m) => m.id === metricId) ?? METRICS[0];
    const info = PAGES.find((p) => p.name === page) ?? PAGES[0];
    const series = useMemo(() => makeSeries(metric, range), [metric, range]);
    const values = series.map((s) => s.value);
    const openCount = demo ? alerts.filter((a) => a.status === "open").length : 0;
    const doneCount = tasks.filter((t) => t.done).length;
    const shownAlerts = alerts.filter((a) => alertFilter === "All" || (alertFilter === "Open" ? a.status === "open" : a.status === "acknowledged"));

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

    useEffect(() => {
        if (!modal) return;
        firstBtn.current?.focus();
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && setModal(false);
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [modal]);

    function acknowledge(id: string) {
        setAlerts((list) => list.map((a) => (a.id === id ? { ...a, status: "acknowledged" } : a)));
        setToast("Alert acknowledged (demo)");
    }

    function saveCheckIn() {
        setModal(false);
        setToast("Check-in recorded on this screen only. It is not sent to the backend yet.");
    }

    /* ----- reusable blocks ----- */
    const metricCards = (
        <div className={styles.metricGrid}>
            {METRICS.map((m) => {
                const st = statusOf(m);
                return (
                    <button key={m.id} type="button" onClick={() => setMetricId(m.id)} aria-pressed={metricId === m.id}
                        className={cx(styles.metricCard, metricId === m.id && styles.metricActive)}>
                        <span className={styles.metricTop}>
                            <span className={styles.metricIcon}><Icon name={m.icon} /></span>
                            <span className={styles.metricName}>{m.title}</span>
                        </span>
                        <span className={styles.metricValue}>
                            {demo ? m.value : "--"} <small>{m.unit}</small>
                        </span>
                        <span className={styles.metricBottom}>
                            {demo ? (
                                <>
                                    <span className={cx(styles.chip, styles[st.tone])}>{st.label}</span>
                                    <Spark data={makeSeries(m, "24 Hours").map((s) => s.value)} />
                                </>
                            ) : (
                                <span className={cx(styles.chip, styles.muted)}>Awaiting data</span>
                            )}
                        </span>
                    </button>
                );
            })}
        </div>
    );

    const rangePills = (
        <div className={styles.pills} role="group" aria-label="Time range">
            {RANGE_KEYS.map((r) => (
                <button key={r} type="button" aria-pressed={range === r} onClick={() => setRange(r)}
                    className={cx(styles.pill, range === r && styles.pillActive)}>{r}</button>
            ))}
        </div>
    );

    const lo = Math.min(...values, metric.baseline[0]);
    const hi = Math.max(...values, metric.baseline[1]);
    const pad = (hi - lo) * 0.15 || 1;
    const chart = demo ? (
        <div className={styles.chartBox}>
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
                    <defs>
                        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#8b7be8" stopOpacity={0.35} />
                            <stop offset="100%" stopColor="#8b7be8" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="rgba(138,138,153,0.22)" />
                    <ReferenceArea y1={metric.baseline[0]} y2={metric.baseline[1]} fill="#3fae7a" fillOpacity={0.09} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#8a8a99", fontSize: 12 }} />
                    <YAxis domain={[Number((lo - pad).toFixed(1)), Number((hi + pad).toFixed(1))]} tickLine={false} axisLine={false} width={44} tick={{ fill: "#8a8a99", fontSize: 12 }} />
                    <Tooltip content={<ChartTip unit={metric.unit} />} cursor={{ stroke: "#8b7be8", strokeDasharray: "4 4" }} />
                    <Area type="monotone" dataKey="value" stroke="#8b7be8" strokeWidth={3} fill="url(#trendFill)"
                        dot={{ r: 3, fill: "#8b7be8", strokeWidth: 0 }} activeDot={{ r: 6 }} />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    ) : (
        <Empty title="No readings yet" text="The chart appears here after the first synchronization with mission data." tag="AWAITING DATA" />
    );

    const alertRow = (a: AlertItem, withAction: boolean) => (
        <li key={a.id} className={styles.alertItem}>
            <i className={cx(styles.alertBar, styles[a.level])} />
            <div className={styles.alertBody}>
                <p className={styles.alertTitle}>{a.title}</p>
                <p className={styles.alertMeta}>
                    {a.time} · {a.status === "open" ? "Open" : "Acknowledged"}
                    {a.delayed && <span className={styles.badge}>Delayed sync</span>}
                </p>
            </div>
            {withAction && a.status === "open" && (
                <button type="button" className={styles.ackBtn} onClick={() => acknowledge(a.id)}>Acknowledge</button>
            )}
        </li>
    );

    return (
        <main className={cx(styles.dashboard, ui.variable, num.variable)} data-theme={dark ? "dark" : "light"}>
            <div className={styles.shell}>
                {/* SIDEBAR */}
                <aside className={styles.sidebar}>
                    <div className={styles.brand}>
                        <h2>Meliora</h2>
                    </div>
                    <nav aria-label="Main">
                        {PAGES.map((p) => (
                            <button key={p.name} type="button" onClick={() => setPage(p.name)}
                                aria-current={page === p.name ? "page" : undefined}
                                className={cx(styles.navItem, page === p.name && styles.active)}>
                                <Icon name={p.icon} />
                                {p.name}
                                {p.name === "Alerts" && openCount > 0 && <span className={styles.navBadge}>{openCount}</span>}
                            </button>
                        ))}
                    </nav>

                    <div className={styles.sidebarBottom}>
                        <b>Space mission 01</b>
                        <span>Engineering prototype. Not a certified medical device.</span>
                    </div>
                </aside>

                {/* MAIN */}
                <section className={styles.main}>
                    <header className={styles.header}>
                        <div>
                            <p className={styles.crumb}>Crew member portal</p>
                            <h2>{info.title}</h2>
                        </div>
                        <div className={styles.tools}>
                            <span className={styles.clock}>{now}</span>
                            <button type="button" role="switch" aria-checked={demo} onClick={() => setDemo(!demo)} className={cx(styles.switchBtn, demo && styles.switchOn)}>
                                <span className={styles.switchKnob} />
                                Demo data
                            </button>
                            <button type="button" className={styles.iconBtn} onClick={() => setDark(!dark)} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}>
                                <Icon name={dark ? "sun" : "moon"} />
                            </button>
                            <button type="button" className={styles.iconBtn} onClick={() => setPage("Alerts")} aria-label={`Alerts, ${openCount} open`}>
                                <Icon name="bell" />
                                {openCount > 0 && <span className={styles.dotBadge}>{openCount}</span>}
                            </button>
                            <div className={styles.profile}>
                                <div className={styles.avatar}>CR</div>
                                <span>Crew member</span>
                            </div>
                        </div>
                    </header>

                    <div className={styles.content} key={page}>
                        <div className={styles.hero}>
                            <div>
                                <h1>{page === "Overview" ? "Good day, Commander" : info.title}</h1>
                                <p>
                                    {page === "Overview"
                                        ? demo ? `${openCount} alert${openCount === 1 ? "" : "s"} to review. Showing demo data.` : "Waiting for the first synchronization with mission data."
                                        : info.blurb}
                                </p>
                            </div>
                            <button type="button" className={styles.cta} onClick={() => setModal(true)}>
                                <Icon name="plus" /> Log check-in
                            </button>
                        </div>

                        {page === "Overview" && (
                            <>
                                {metricCards}
                                <div className={styles.row2}>
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <div>
                                                <h3>{metric.title} trend</h3>
                                                <p>{demo ? "Demo data" : "No data"} · {metric.unit} · green band is your baseline</p>
                                            </div>
                                            {rangePills}
                                        </div>
                                        {chart}
                                    </section>
                                    <section className={styles.card}>
                                        <h3>Heart rate zone</h3>
                                        <div className={styles.legend}>
                                            <span className={styles.legendAvg}>Average</span>
                                            <span className={styles.legendNow}>Current</span>
                                        </div>
                                        <div className={styles.gauge}>
                                            <Gauge value={demo ? 72 : 0} average={demo ? 68 : 0} max={180} />
                                            <div className={styles.gaugeCenter}>
                                                <b>{demo ? "72" : "--"}</b>
                                                <small>beats / min</small>
                                            </div>
                                        </div>
                                    </section>
                                </div>
                                <div className={styles.row3}>
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <h3>Latest alerts</h3>
                                            <button type="button" className={styles.linkBtn} onClick={() => setPage("Alerts")}>View all</button>
                                        </div>
                                        {demo ? <ul className={styles.alertList}>{alerts.slice(0, 2).map((a) => alertRow(a, false))}</ul>
                                            : <p className={styles.quiet}>No alerts. Notifications appear here when alert data is received.</p>}
                                    </section>
                                    <section className={styles.card}>
                                        <div className={styles.cardHead}>
                                            <h3>Today’s tasks</h3>
                                            <span className={styles.chip}>{doneCount} of {tasks.length} done</span>
                                        </div>
                                        <div className={styles.progress} aria-hidden="true"><span style={{ width: `${(doneCount / tasks.length) * 100}%` }} /></div>
                                        <ul className={styles.tasks}>
                                            {tasks.map((t) => (
                                                <li key={t.id}>
                                                    <label className={cx(styles.task, t.done && styles.taskDone)}>
                                                        <input type="checkbox" checked={t.done}
                                                            onChange={() => setTasks((l) => l.map((x) => (x.id === t.id ? { ...x, done: !x.done } : x)))} />
                                                        <span className={styles.taskBox} />
                                                        <span>{t.title}</span>
                                                        <time>{t.time}</time>
                                                    </label>
                                                </li>
                                            ))}
                                        </ul>
                                    </section>
                                </div>
                            </>
                        )}

                        {page === "Vital Signs" && (
                            <div className={styles.vitalGrid}>
                                {METRICS.map((m) => {
                                    const st = statusOf(m);
                                    return (
                                        <article key={m.id} className={styles.card}>
                                            <div className={styles.metricTop}>
                                                <span className={styles.metricIcon}><Icon name={m.icon} /></span>
                                                <span className={styles.metricName}>{m.title}</span>
                                                {demo && <span className={cx(styles.chip, styles[st.tone], styles.push)}>{st.label}</span>}
                                            </div>
                                            <p className={styles.metricValue}>{demo ? m.value : "--"} <small>{m.unit}</small></p>
                                            <p className={styles.quiet}>{m.description}</p>
                                            {demo ? (
                                                <>
                                                    <RangeBar m={m} />
                                                    <p className={styles.rangeLabel}>Your baseline {m.baseline[0]}-{m.baseline[1]} {m.unit}</p>
                                                </>
                                            ) : (
                                                <span className={cx(styles.chip, styles.muted)}>Awaiting data</span>
                                            )}
                                            <button type="button" className={styles.linkBtn} onClick={() => { setMetricId(m.id); setPage("Health Trends"); }}>
                                                See trend
                                            </button>
                                        </article>
                                    );
                                })}
                            </div>
                        )}

                        {page === "Health Trends" && (
                            <>
                                <div className={styles.pills} role="group" aria-label="Choose a measurement">
                                    {METRICS.map((m) => (
                                        <button key={m.id} type="button" aria-pressed={metricId === m.id} onClick={() => setMetricId(m.id)}
                                            className={cx(styles.pill, metricId === m.id && styles.pillActive)}>{m.title}</button>
                                    ))}
                                </div>
                                <section className={styles.card}>
                                    <div className={styles.cardHead}>
                                        <div>
                                            <h3>{metric.title}</h3>
                                            <p>{demo ? "Demo data" : "No data"} · {metric.unit}</p>
                                        </div>
                                        {rangePills}
                                    </div>
                                    {chart}
                                </section>
                                <div className={styles.statRow}>
                                    {[
                                        ["Lowest", demo ? Math.min(...values) : "--"],
                                        ["Average", demo ? Number((values.reduce((a, b) => a + b, 0) / values.length).toFixed(metric.decimals)) : "--"],
                                        ["Highest", demo ? Math.max(...values) : "--"],
                                    ].map(([label, v]) => (
                                        <div key={label} className={styles.stat}>
                                            <span>{label}</span>
                                            <b>{v} <small>{demo ? metric.unit : ""}</small></b>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}

                        {page === "Assessments" && (
                            demo ? (
                                <div className={styles.acc}>
                                    {ASSESSMENTS.map((a) => {
                                        const open = openAssessment === a.id;
                                        return (
                                            <div key={a.id} className={cx(styles.accItem, open && styles.accOpen)}>
                                                <button type="button" className={styles.accHead} aria-expanded={open}
                                                    onClick={() => setOpenAssessment(open ? null : a.id)}>
                                                    <span>
                                                        <b>{a.title}</b>
                                                        <small>{a.time}</small>
                                                    </span>
                                                    <span className={cx(styles.chip, styles[a.tone])}>{a.status}</span>
                                                    <span className={styles.chev}><Icon name="chevron" /></span>
                                                </button>
                                                {open && (
                                                    <div className={styles.accBody}>
                                                        <p>{a.summary}</p>
                                                        <ul>{a.details.map((d) => <li key={d}>{d}</li>)}</ul>
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                    <p className={styles.quiet}>Demo layout only. These are not medical results.</p>
                                </div>
                            ) : (
                                <Empty title="No assessments available" text="Assessment records appear here once they are synchronized with mission data." tag="AWAITING DATA" />
                            )
                        )}

                        {page === "Alerts" && (
                            <>
                                <div className={styles.pills} role="group" aria-label="Filter alerts">
                                    {(["All", "Open", "Acknowledged"] as const).map((f) => (
                                        <button key={f} type="button" aria-pressed={alertFilter === f} onClick={() => setAlertFilter(f)}
                                            className={cx(styles.pill, alertFilter === f && styles.pillActive)}>{f}</button>
                                    ))}
                                </div>
                                {demo ? (
                                    shownAlerts.length ? (
                                        <section className={styles.card}>
                                            <ul className={styles.alertList}>{shownAlerts.map((a) => alertRow(a, true))}</ul>
                                        </section>
                                    ) : (
                                        <Empty title="Nothing in this filter" text="Try another filter to see the rest of your alerts." tag="ALL CLEAR" />
                                    )
                                ) : (
                                    <Empty title="No new alerts" text="Health monitoring notifications appear here when alert data is received." tag="AWAITING DATA" />
                                )}
                            </>
                        )}
                    </div>
                </section>
            </div>

            {/* CHECK-IN MODAL */}
            {modal && (
                <div className={styles.overlay} onClick={() => setModal(false)}>
                    <div className={styles.modal} role="dialog" aria-modal="true" aria-labelledby="ci-title" onClick={(e) => e.stopPropagation()}>
                        <div className={styles.modalHead}>
                            <h3 id="ci-title">How are you today?</h3>
                            <button type="button" className={styles.iconBtn} onClick={() => setModal(false)} aria-label="Close"><Icon name="close" /></button>
                        </div>
                        {([["Mood", mood, setMood], ["Fatigue", fatigue, setFatigue]] as const).map(([label, val, set], row) => (
                            <div key={label} className={styles.scaleRow}>
                                <span>{label} <small>1 low, 5 high</small></span>
                                <div className={styles.scale} role="group" aria-label={label}>
                                    {[1, 2, 3, 4, 5].map((n) => (
                                        <button key={n} type="button" ref={row === 0 && n === 1 ? firstBtn : undefined}
                                            aria-pressed={val === n} onClick={() => set(n)}
                                            className={cx(styles.scaleBtn, val === n && styles.scaleOn)}>{n}</button>
                                    ))}
                                </div>
                            </div>
                        ))}
                        <div className={styles.modalActions}>
                            <button type="button" className={styles.ghostBtn} onClick={() => setModal(false)}>Cancel</button>
                            <button type="button" className={styles.cta} onClick={saveCheckIn}>Save check-in</button>
                        </div>
                    </div>
                </div>
            )}

            {toast && <div className={styles.toast} role="status">{toast}</div>}
        </main>
    );
}
