
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import dynamic from "next/dynamic";
import styles from "./dashboard.module.css";
import AlertBanner, { type AlertData } from "@/components/home/AlertBanner";
import { StatusLevel } from "@/components/common/StatusBadge";
import ReadinessRing from "@/components/home/ReadinessRing";
import ReadinessDrawer from "@/components/home/ReadinessDrawer";
import DailyMissionCard from "@/components/home/DailyMissionCard";
import DisclaimerFooter from "@/components/common/DisclaimerFooter";
import QuestsView from "@/components/quests/QuestsView";
import CodexView from "@/components/codex/CodexView";
import PulseCheckView from "@/components/pulse/PulseCheckView";
import CountermeasureLabView from "@/components/countermeasures/CountermeasureLabView";
import SolClockView from "@/components/circadian/SolClockView";
import ImmuneShieldView from "@/components/immune/ImmuneShieldView";
import TeamStreakView from "@/components/team/TeamStreakView";
import ScenarioPanelView from "@/components/scenarios/ScenarioPanelView";
import EnvironmentProfileView from "@/components/environment/EnvironmentProfileView";
import SettingsView from "@/components/settings/SettingsView";

const HumanBody = dynamic(() => import("../../components/HumanBody"), {
    ssr: false,
});

const EtchedAccretion = dynamic(() => import("@/components/ui/etched-accretion"), {
    ssr: false,
});

const API_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/* ---------- types ---------- */
type Page = "Overview" | "Missions" | "Vitals" | "Lab" | "Library" | "Alerts" | "Settings";
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
    { name: "Overview", icon: "home", title: "Mission overview", blurb: "EVA clearance, daily objectives & 3D anatomical focus" },
    { name: "Missions", icon: "check", title: "Missions & Quests", blurb: "Daily countermeasure objectives and shared team streak progress" },
    { name: "Vitals", icon: "pulse", title: "Vital Signs & Trends", blurb: "Select a vital sign to review telemetry trends, pulse check and immune status" },
    { name: "Lab", icon: "flask", title: "Countermeasure & Circadian Lab", blurb: "What-if physiological forecast modeling and circadian Sol clock realignment" },
    { name: "Library", icon: "book", title: "Flight Science Codex", blurb: "Peer-reviewed space biology briefings & unlockable knowledge cards" },
    { name: "Alerts", icon: "bell", title: "Alerts & Diagnostics", blurb: "Active health monitoring notifications, clinical check-ins and demo scenarios" },
    { name: "Settings", icon: "gear", title: "Settings & Profile", blurb: "Mission accessibility, sound, contrast and planetary environment switcher" },
];

const PAGE_H1: Record<Page, { title: string; script: string }> = {
    Overview: { title: "MISSION OVERVIEW", script: "Commander" },
    Missions: { title: "DAILY QUESTS", script: "Missions" },
    Vitals: { title: "VITAL TELEMETRY", script: "Signals" },
    Lab: { title: "COUNTERMEASURES", script: "Forecast" },
    Library: { title: "SCIENCE CODEX", script: "Library" },
    Alerts: { title: "SYSTEM ADVISORIES", script: "Alerts" },
    Settings: { title: "SYSTEM PROFILE", script: "Console" },
};

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
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></>,
    flask: <path d="M10 2v7.31L4.1 18.2a2 2 0 0 0 1.66 3.8h12.48a2 2 0 0 0 1.66-3.8L14 9.31V2" />,
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    gear: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" /></>,
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
    const [cosmicBg, setCosmicBg] = useState<"crimson" | "ember" | "glacier" | "ash" | "orchid" | "off">("crimson");
    // -------------------------------------------------------------
    // READINESS SCORE:
    // If backend /api/v1/readiness provides score, use it. Otherwise compute
    // client-side from latest vitals and mission completion.
    // -------------------------------------------------------------
    const [readinessScore, setReadinessScore] = useState<number>(94);
    const [readinessLevel, setReadinessLevel] = useState<StatusLevel>("normal");
    const [readinessDrawerOpen, setReadinessDrawerOpen] = useState(false);
    const [activeAlert, setActiveAlert] = useState<AlertData | null>({
        id: "alert_shoulder_strain",
        level: "watch",
        title: "Musculoskeletal Advisory",
        reason: "Mild left shoulder impingement context recorded after Sol 41 orbital hatch docking.",
        nextStep: "Complete 10-min rotator cuff resistance band stretch before next EVA. Check with flight surgeon if pain escalates.",
        timestamp: "Sol 41 12:40 UTC",
    });
    const [gamificationEnabled, setGamificationEnabled] = useState(true);

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

    /* ---------- readiness score (backend fetch with client fallback) ---------- */
    useEffect(() => {
        let isMounted = true;
        async function fetchReadiness() {
            try {
                const token = sessionStorage.getItem("meliora_access_token");
                const res = await fetch(`${API_URL}/api/v1/readiness`, {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted && typeof data.readiness_score === "number") {
                        setReadinessScore(data.readiness_score);
                        const lvl: StatusLevel =
                            data.readiness_score >= 85 ? "normal" : data.readiness_score >= 70 ? "watch" : "act";
                        setReadinessLevel(lvl);
                        return;
                    }
                }
            } catch {
                // If backend endpoint is unavailable, compute client-side
            }

            // Client-side computation fallback:
            // Base readiness (88) + HR stability (-6 to +4) + SpO2 nominal factor (+2)
            // Evaluated client-side from real telemetry and mission completion
            if (isMounted) {
                const hrNum = parseFloat(realMetricValues.hr);
                const spo2Num = parseFloat(realMetricValues.spo2);
                let computed = 88;
                if (!isNaN(hrNum)) {
                    if (hrNum >= 60 && hrNum <= 80) computed += 4;
                    else if (hrNum > 85) computed -= 6;
                }
                if (!isNaN(spo2Num)) {
                    if (spo2Num >= 97) computed += 2;
                    else if (spo2Num < 95) computed -= 8;
                }
                const finalScore = Math.max(50, Math.min(99, computed));
                setReadinessScore(finalScore);
                setReadinessLevel(finalScore >= 85 ? "normal" : finalScore >= 70 ? "watch" : "act");
            }
        }
        fetchReadiness();
        return () => {
            isMounted = false;
        };
    }, [realMetricValues.hr, realMetricValues.spo2]);

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
                    <CartesianGrid
                        vertical={false}
                        stroke="rgba(233, 228, 223, 0.08)"
                    />

                    <XAxis
                        dataKey="label"
                        tickLine={false}
                        axisLine={false}
                        tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                    />

                    <YAxis
                        domain={["auto", "auto"]}
                        tickLine={false}
                        axisLine={false}
                        width={44}
                        tick={{ fill: "var(--muted)", fontSize: 11, fontFamily: "var(--font-mono)" }}
                    />

                    <Tooltip
                        content={<ChartTip unit={metric.unit} />}
                        cursor={{
                            stroke: "rgba(233, 228, 223, 0.25)",
                            strokeDasharray: "3 3",
                        }}
                    />

                    <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#FF4D5A"
                        strokeWidth={2}
                        fill="none"
                        dot={{
                            r: 3,
                            fill: "#FF4D5A",
                            strokeWidth: 0,
                        }}
                        activeDot={{ r: 5, fill: "#FF4D5A", stroke: "#030307", strokeWidth: 2 }}
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
            className={styles.dashboard}
            data-theme="dark"
        >
            {/* Ambient Procedural WebGL2 Etched Accretion Deep Space Background */}
            {cosmicBg !== "off" && (
                <div
                    style={{
                        position: "fixed",
                        inset: 0,
                        zIndex: 0,
                        pointerEvents: "none",
                        opacity: 0.85,
                        overflow: "hidden",
                    }}
                    aria-hidden="true"
                >
                    <EtchedAccretion
                        height="100vh"
                        preset={cosmicBg}
                        interactive={false}
                        params={{
                            exposure: 1.25,
                            vignette: 0.6,
                        }}
                    />
                </div>
            )}

            {/* 1. HORIZONTAL TOP BAR */}
            <header className={styles.crewTopBar}>
                <div className={styles.crewTopBarRow1}>
                    <div className={styles.crewTopBarLeft}>
                        <div className={styles.crewBrandLogo}>
                            <h2>Meliora</h2>
                        </div>
                    </div>

                    <div className={styles.crewTopActions}>
                        <span className={styles.crewClock}>{now}</span>

                        <div className={styles.avatar} title={`Logged in as ${username}`}>
                            {username.slice(0, 2).toUpperCase()}
                        </div>

                        <button
                            type="button"
                            className={styles.crewLogoutBtn}
                            onClick={logout}
                            aria-label="Sign out of mission console"
                        >
                            <Icon name="close" /> Sign out
                        </button>
                    </div>
                </div>

                <nav className={styles.crewTabsContainer} aria-label="Main Navigation">
                    {PAGES.map((p) => {
                        const isActive = page === p.name;
                        return (
                            <button
                                key={p.name}
                                type="button"
                                onClick={() => setPage(p.name)}
                                aria-current={isActive ? "page" : undefined}
                                className={cx(
                                    styles.crewTab,
                                    isActive && styles.crewTabActive
                                )}
                            >
                                <Icon name={p.icon} />
                                <span>{p.name}</span>
                                {p.name === "Alerts" && openCount > 0 && (
                                    <span className={styles.crewTabBadge} aria-label={`${openCount} open alerts`}>
                                        {openCount}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </nav>
            </header>

            {/* 2. CREW DASHBOARD SHELL */}
            <div className={styles.crewShell}>
                {/* Clean Page Heading (Moonlight stacked display H1 with Out of Nowhere cursive accent) */}
                <div className={styles.crewPageHeading}>
                    <div>
                        <div className={styles.stackedH1Container}>
                            <span className={styles.echoH1_1} aria-hidden="true">{PAGE_H1[page].title}</span>
                            <span className={styles.echoH1_2} aria-hidden="true">{PAGE_H1[page].title}</span>
                            <h1 className={styles.frontH1}>
                                {PAGE_H1[page].title}{" "}
                                <span className={styles.scriptAccent}>{PAGE_H1[page].script}</span>
                            </h1>
                        </div>
                        <p>{info.blurb}</p>
                    </div>

                    <button
                        type="button"
                        className={styles.cta}
                        onClick={() => setModal(true)}
                    >
                        <Icon name="plus" /> Log check-in
                    </button>
                </div>

                {/* Watch / Act Advisory Banner (Overview and Alerts tabs only) */}
                {activeAlert && (page === "Overview" || page === "Alerts") && (
                    <div style={{ width: "100%", marginBottom: "4px" }}>
                        <AlertBanner
                            alert={activeAlert}
                            onCallGround={() => setToast("Ground support link requested.")}
                        />
                    </div>
                )}

                {/* 3. CONTENT (7 MERGED TABS) */}
                <div className={styles.content} key={page}>
                    {/* TAB 1: OVERVIEW (EVA Readiness Ring + Daily Missions (Left) & 3D Anatomy Model (Right) ONLY) */}
                    {page === "Overview" && (
                        <div className={styles.overviewGrid}>
                            <div className={styles.overviewLeft}>
                                <div className={styles.sectionLabel}>
                                    <span className={styles.sectionLabelIndex}>01</span>
                                    <span className={styles.sectionLabelTitle}>EVA READINESS TELEMETRY</span>
                                    <span className={styles.sectionLabelRule} />
                                </div>
                                <ReadinessRing
                                    score={readinessScore}
                                    level={readinessLevel}
                                    confidence="high"
                                    onOpenDrawer={() => setReadinessDrawerOpen(true)}
                                />
                                <div className={styles.sectionLabel} style={{ marginTop: "8px" }}>
                                    <span className={styles.sectionLabelIndex}>02</span>
                                    <span className={styles.sectionLabelTitle}>DAILY OPERATIONAL OBJECTIVES</span>
                                    <span className={styles.sectionLabelRule} />
                                </div>
                                <DailyMissionCard
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onViewAllQuests={() => setPage("Missions")}
                                />
                            </div>

                            <div className={styles.overviewRight}>
                                <div className={styles.sectionLabel}>
                                    <span className={styles.sectionLabelIndex}>03</span>
                                    <span className={styles.sectionLabelTitle}>3D PHYSIOLOGICAL ANATOMY</span>
                                    <span className={styles.sectionLabelRule} />
                                </div>
                                <div className={cx(styles.cardBox, styles.cornerTicks)}>
                                    <span className={styles.cornerTickTL} />
                                    <span className={styles.cornerTickTR} />
                                    <span className={styles.cornerTickBL} />
                                    <span className={styles.cornerTickBR} />
                                    <div className={styles.cardHead}>
                                        <div>
                                            <h3>3D Anatomical Telemetry</h3>
                                            <p>Interactive physiological layer inspection & organ focus</p>
                                        </div>
                                    </div>
                                    <HumanBody height={520} />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 2: MISSIONS (Quests + Team Streak) */}
                    {page === "Missions" && (
                        <div className={styles.tabSectionStack}>
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Daily Countermeasure Quests</h3>
                                        <p>Physical & operational countermeasure targets with evidence-based progression</p>
                                    </div>
                                </div>
                                <QuestsView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                />
                            </div>

                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Shared Crew Team Streak</h3>
                                        <p>Shared goal completion and protective streak freeze day status</p>
                                    </div>
                                </div>
                                <TeamStreakView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                    onNavigateToQuests={() => setPage("Missions")}
                                />
                            </div>
                        </div>
                    )}

                    {/* TAB 3: VITALS (Vital Signs + Health Trends + Pulse Check + Immune Shield) */}
                    {page === "Vitals" && (
                        <div className={styles.tabSectionStack}>
                            {/* Section 1: Selectable Vital Signs Grid */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Vital Signs Telemetry</h3>
                                        <p>Select any vital sign below to update the telemetry chart below</p>
                                    </div>
                                </div>
                                <div className={styles.metricGrid}>
                                    {METRICS.map((m) => {
                                        const realValue = realMetricValues[m.id];
                                        const isSelected = metricId === m.id;
                                        return (
                                            <button
                                                key={m.id}
                                                type="button"
                                                onClick={() => setMetricId(m.id)}
                                                className={cx(
                                                    styles.vitalCardSelectable,
                                                    isSelected && styles.vitalCardSelected
                                                )}
                                                aria-pressed={isSelected}
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

                                                <span className={cx(styles.chip, isSelected ? styles.chipNormal : styles.muted)}>
                                                    {isSelected ? "● Viewing Trend" : "Tap to view trend"}
                                                </span>
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Section 2: Health Trends AreaChart */}
                            <div className={cx(styles.cardBox, styles.cornerTicks)}>
                                <span className={styles.cornerTickTL} />
                                <span className={styles.cornerTickTR} />
                                <span className={styles.cornerTickBL} />
                                <span className={styles.cornerTickBR} />
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>{metric.title} Health Trend</h3>
                                        <p>Personal baseline range band with 30-Sol forecast cone · {metric.unit}</p>
                                    </div>
                                    {rangePills}
                                </div>

                                {chart}

                                <div className={styles.statRow}>
                                    {[
                                        [
                                            "Lowest",
                                            realSeries.length
                                                ? Math.min(...realSeries.map((s) => s.value))
                                                : "--",
                                        ],
                                        [
                                            "Average",
                                            realSeries.length
                                                ? Number((realSeries.reduce((a, b) => a + b.value, 0) / realSeries.length).toFixed(2))
                                                : "--",
                                        ],
                                        [
                                            "Highest",
                                            realSeries.length
                                                ? Math.max(...realSeries.map((s) => s.value))
                                                : "--",
                                        ],
                                    ].map(([label, value]) => (
                                        <div key={label} className={styles.stat}>
                                            <span>{label}</span>
                                            <b>
                                                {value}{" "}
                                                <small>{realSeries.length ? metric.unit : ""}</small>
                                            </b>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Section 3: Pulse Check Mini-Game */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Optical Pulse Check</h3>
                                        <p>Zero-upload in-browser green-channel rPPG webcam heart rate and HRV measurement</p>
                                    </div>
                                </div>
                                <PulseCheckView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                />
                            </div>

                            {/* Section 4: Immune Shield */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Immune Shield Defense Meter</h3>
                                        <p>Multi-factor spaceflight physiological stress context (decision support, not a diagnosis)</p>
                                    </div>
                                </div>
                                <ImmuneShieldView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                    onNavigateToQuests={() => setPage("Missions")}
                                />
                            </div>
                        </div>
                    )}

                    {/* TAB 4: LAB (Countermeasure Lab + Sol Clock) */}
                    {page === "Lab" && (
                        <div className={styles.tabSectionStack}>
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Countermeasure Forecast Lab</h3>
                                        <p>What-if simulation: adjust sleep, resistance and fluid intake to forecast 7-Sol resilience</p>
                                    </div>
                                </div>
                                <CountermeasureLabView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                />
                            </div>

                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Circadian Sol Clock</h3>
                                        <p>Dual-overlaid habitat vs predicted body clock with blue photic shifting and realignment Sol countdown</p>
                                    </div>
                                </div>
                                <SolClockView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                />
                            </div>
                        </div>
                    )}

                    {/* TAB 5: LIBRARY (Codex) */}
                    {page === "Library" && (
                        <div className={styles.tabSectionStack}>
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Flight Science Codex</h3>
                                        <p>Peer-reviewed NASA HRP research cards, DOI sources and unlocked space biology knowledge</p>
                                    </div>
                                </div>
                                <CodexView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                    onNavigateToQuest={() => setPage("Missions")}
                                />
                            </div>
                        </div>
                    )}

                    {/* TAB 6: ALERTS (Alerts + Assessments + Scenario Panel) */}
                    {page === "Alerts" && (
                        <div className={styles.tabSectionStack}>
                            {/* Active Alerts */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Active Telemetry Alerts</h3>
                                        <p>Automated threshold notifications and fault-gate status</p>
                                    </div>
                                    <div className={styles.pills} role="group" aria-label="Filter alerts">
                                        {(["All", "Open", "Acknowledged"] as const).map((f) => (
                                            <button
                                                key={f}
                                                type="button"
                                                aria-pressed={alertFilter === f}
                                                onClick={() => setAlertFilter(f)}
                                                className={cx(styles.pill, alertFilter === f && styles.pillActive)}
                                            >
                                                {f}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {alertsLoading ? (
                                    <Empty title="Loading alerts" text="Checking active alert feed." tag="LOADING" />
                                ) : alertError ? (
                                    <Empty title="Could not load alerts" text={alertError} tag="ERROR" />
                                ) : shownLiveAlerts.length > 0 ? (
                                    <ul className={styles.alertList}>
                                        {shownLiveAlerts.map((a) =>
                                            liveAlertRow(a, true)
                                        )}
                                    </ul>
                                ) : liveAlerts.length === 0 ? (
                                    <Empty title="No alerts yet" text="Health monitoring notifications will appear here when telemetry is received." tag="NO ALERTS" />
                                ) : (
                                    <Empty title="Nothing in this filter" text="Try another filter to see the rest of your alerts." tag="ALL CLEAR" />
                                )}
                            </div>

                            {/* Assessments History */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Health Assessments History</h3>
                                        <p>Chronological log of self-reported check-ins and symptom observations</p>
                                    </div>
                                </div>
                                <div className={styles.acc}>
                                    {checkInsLoading ? (
                                        <Empty title="Loading check-in history" text="Retrieving submitted records." tag="LOADING" />
                                    ) : checkInsError ? (
                                        <Empty title="Could not load check-ins" text={checkInsError} tag="ERROR" />
                                    ) : checkIns.length === 0 ? (
                                        <Empty title="No check-ins yet" text="Your submitted wellness records will appear here." tag="NO RECORDS" />
                                    ) : (
                                        <>
                                            {checkIns.map((item) => (
                                                <div key={item.id} className={styles.accItem}>
                                                    <div className={styles.accHead}>
                                                        <span>
                                                            <b>{item.check_in_type === "WELLNESS" ? "Wellness check-in" : "Symptom report"}</b>
                                                            <small>{new Date(item.recorded_at).toLocaleString()}</small>
                                                        </span>
                                                        <span className={styles.chip}>{item.check_in_type}</span>
                                                    </div>
                                                    <div className={styles.accBody}>
                                                        <ul>
                                                            {Object.entries(item.details).map(([key, value]) => (
                                                                <li key={key}>
                                                                    <strong>{key.replaceAll("_", " ")}:</strong>{" "}
                                                                    {Array.isArray(value)
                                                                        ? value.join(", ")
                                                                        : value !== null && typeof value === "object"
                                                                        ? JSON.stringify(value)
                                                                        : String(value)}
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                </div>
                                            ))}
                                        </>
                                    )}
                                </div>
                            </div>

                            {/* Demo Mode Scenario Simulation Panel */}
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Emergency Scenario Simulation Panel</h3>
                                        <p>Demo controls: inject dust storms, communications blackouts, and sensor faults</p>
                                    </div>
                                </div>
                                <ScenarioPanelView
                                    alertLevel={activeAlert?.level || "normal"}
                                    onApplyScenario={(sc) => {
                                        if (sc.alert_level === "normal") {
                                            setActiveAlert(null);
                                        } else {
                                            setActiveAlert({
                                                id: sc.scenario_id,
                                                level: sc.alert_level,
                                                title: sc.alert_title,
                                                reason: sc.alert_reason,
                                                nextStep: sc.alert_next_step,
                                                timestamp: "Sol 41 Just now",
                                            });
                                        }
                                    }}
                                />
                            </div>
                        </div>
                    )}

                    {/* TAB 7: SETTINGS (Settings + Environment Profile) */}
                    {page === "Settings" && (
                        <div className={styles.tabSectionStack}>
                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Settings & Accessibility</h3>
                                        <p>Gamification toggle, neuro-vestibular reduced motion, contrast, audio and offline sync</p>
                                    </div>
                                </div>
                                <SettingsView
                                    alertLevel={activeAlert?.level || "normal"}
                                    gamificationEnabled={gamificationEnabled}
                                    onToggleGamification={() => setGamificationEnabled(!gamificationEnabled)}
                                />
                            </div>

                            <div className={styles.cardBox}>
                                <div className={styles.cardHead}>
                                    <div>
                                        <h3>Planetary Environment Profile</h3>
                                        <p>Switch between Mars base, Lunar base, Spacecraft, Station, and Rover habitats</p>
                                    </div>
                                </div>
                                <EnvironmentProfileView
                                    alertLevel={activeAlert?.level || "normal"}
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Universal Screen Footer (Rule 3) */}
                <DisclaimerFooter lastSynced="Sol 41 14:34 UTC · 2m ago" isOffline={false} />
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

            {/* Slide-over Readiness Detail Drawer */}
            <ReadinessDrawer
                isOpen={readinessDrawerOpen}
                onClose={() => setReadinessDrawerOpen(false)}
                overallScore={readinessScore}
                overallLevel={readinessLevel}
            />
        </main>
    );
}
