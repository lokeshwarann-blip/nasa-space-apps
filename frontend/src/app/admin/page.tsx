"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Manrope, Space_Grotesk } from "next/font/google";
import dashboardStyles from "../dashboard/dashboard.module.css";
import styles from "./admin.module.css";

/* ---------- fonts (same as the crew dashboard) ---------- */
const ui = Manrope({ subsets: ["latin"], variable: "--font-ui", display: "swap" });
const num = Space_Grotesk({ subsets: ["latin"], variable: "--font-num", display: "swap" });

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const TOKEN_KEY = "meliora_access_token";
const IDENTITY_KEY = "meliora_identity";

/* ---------- types ---------- */
type AdminPage = "Overview" | "System health" | "Integrations" | "Analytics" | "Users";
type ServiceKey = "health" | "adapters" | "providers" | "users";

interface Identity { username: string; role: string }
interface Readiness { status: string; database: string; version: string }
interface DeviceAdapter {
    provider_id: string;
    version: string;
    is_connected: boolean;
    supported_measurement_types: string[];
}
interface ModelProvider {
    provider_id: string;
    model_version: string;
    is_enabled: boolean;
    capabilities: string[];
}
interface UserAccount {
    id: string;
    username: string;
    role: string;
    is_active: boolean;
    crew_member_id: string | null;
    assigned_crew_ids: string[];
    created_at: string;
    updated_at: string;
}
interface CheckEntry { time: string; api: boolean; db: boolean }

const NAV: { name: AdminPage; icon: string; title: string; blurb: string }[] = [
    { name: "Overview", icon: "home", title: "Mission overview", blurb: "Infrastructure, integrations and accounts at a glance" },
    { name: "System health", icon: "server", title: "System health", blurb: "Live readiness checks for the application and database" },
    { name: "Integrations", icon: "radio", title: "Device integrations", blurb: "External telemetry adapters registered in this deployment" },
    { name: "Analytics", icon: "cpu", title: "Analytical providers", blurb: "Model registry and safety state" },
    { name: "Users", icon: "users", title: "User management", blurb: "Registered accounts, roles and status" },
];

const SERVICE_LABEL: Record<ServiceKey, string> = {
    health: "Application and database",
    adapters: "Device adapters",
    providers: "Model registry",
    users: "User service",
};

/* ---------- helpers ---------- */
const cx = (...a: (string | false | undefined)[]) => a.filter(Boolean).join(" ");

function roleLabel(role: string) {
    const s = role.replaceAll("_", " ").toLowerCase();
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatDate(date: string) {
    const d = new Date(date);
    if (!date || Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function formatDateTime(date: string) {
    const d = new Date(date);
    if (!date || Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function csvCell(value: string) {
    const safe = /^[=+\-@]/.test(value) ? `'${value}` : value;
    return `"${safe.replaceAll('"', '""')}"`;
}

/* ---------- icons ---------- */
const ICONS: Record<string, ReactNode> = {
    home: <><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M9 22V12h6v10" /></>,
    server: <><rect x="2" y="2" width="20" height="8" rx="2" /><rect x="2" y="14" width="20" height="8" rx="2" /><path d="M6 6h.01M6 18h.01" /></>,
    database: <><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.7-4 3-9 3s-9-1.3-9-3" /><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5" /></>,
    radio: <><circle cx="12" cy="12" r="2" /><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19 5a10 10 0 0 1 0 14M5 19a10 10 0 0 1 0-14" /></>,
    cpu: <><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3" /></>,
    users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" /></>,
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
    refresh: <><path d="M23 4v6h-6M1 20v-6h6" /><path d="M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>,
    copy: <><rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></>,
    download: <><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><path d="M7 10l5 5 5-5M12 15V3" /></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></>,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4" /></>,
    moon: <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />,
    close: <path d="M18 6L6 18M6 6l12 12" />,
    chevron: <path d="M6 9l6 6 6-6" />,
    check: <><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></>,
};

function Icon({ name }: { name: string }) {
    return (
        <svg className={dashboardStyles.icon} viewBox="0 0 24 24" aria-hidden="true">
            {ICONS[name]}
        </svg>
    );
}

function Status({ tone, children }: { tone: "good" | "bad" | "neutral"; children: ReactNode }) {
    return <span className={cx(styles.status, styles[tone])}>{children}</span>;
}

function Empty({ icon, title, text, action }: { icon: string; title: string; text: string; action?: ReactNode }) {
    return (
        <div className={dashboardStyles.emptyState}>
            <div className={dashboardStyles.emptyIcon}><Icon name={icon} /></div>
            <h3>{title}</h3>
            <p>{text}</p>
            {action}
        </div>
    );
}

/* ---------- page ---------- */
export default function AdminPage() {
    const router = useRouter();

    const [page, setPage] = useState<AdminPage>("Overview");
    const [dark, setDark] = useState(true);

    const [identity, setIdentity] = useState<Identity | null>(null);
    const [readiness, setReadiness] = useState<Readiness | null>(null);
    const [adapters, setAdapters] = useState<DeviceAdapter[]>([]);
    const [providers, setProviders] = useState<ModelProvider[]>([]);
    const [users, setUsers] = useState<UserAccount[]>([]);

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [errors, setErrors] = useState<Partial<Record<ServiceKey, string>>>({});
    const [lastUpdated, setLastUpdated] = useState("");
    const [history, setHistory] = useState<CheckEntry[]>([]);
    const [auto, setAuto] = useState(false);
    const [now, setNow] = useState("");
    const [toast, setToast] = useState("");

    const [openRow, setOpenRow] = useState<string | null>(null);
    const [adapterQuery, setAdapterQuery] = useState("");
    const [query, setQuery] = useState("");
    const [roleFilter, setRoleFilter] = useState("All");
    const [statusFilter, setStatusFilter] = useState<"All" | "Active" | "Inactive">("All");
    const [selectedUser, setSelectedUser] = useState<UserAccount | null>(null);

    const info = NAV.find((n) => n.name === page) ?? NAV[0];

    /* ----- data loading ----- */
    const loadDashboard = useCallback(
        async (token: string) => {
            const headers = { Authorization: `Bearer ${token}` };

            const get = async (path: string, auth: boolean) => {
                const res = await fetch(`${API_URL}${path}`, auth ? { headers } : undefined);
                if (res.status === 401) throw new Error("UNAUTHORIZED");
                if (!res.ok) throw new Error(res.status === 403 ? "Access denied (403)" : `Request failed (${res.status})`);
                return res.json();
            };

            const [h, d, m, u] = await Promise.allSettled([
                get("/health/ready", false),
                get("/api/v1/devices/adapters", true),
                get("/api/v1/models/providers", true),
                get("/api/v1/auth/users", true),
            ]);

            const expired = [h, d, m, u].some(
                (r) => r.status === "rejected" && r.reason instanceof Error && r.reason.message === "UNAUTHORIZED"
            );
            if (expired) {
                sessionStorage.removeItem(TOKEN_KEY);
                sessionStorage.removeItem(IDENTITY_KEY);
                router.replace("/login");
                return;
            }

            const errs: Partial<Record<ServiceKey, string>> = {};
            const why = (r: PromiseRejectedResult) =>
                r.reason instanceof TypeError ? "Server unreachable" : r.reason instanceof Error ? r.reason.message : "Request failed";

            if (h.status === "fulfilled") setReadiness(h.value as Readiness);
            else { setReadiness(null); errs.health = why(h); }

            if (d.status === "fulfilled") setAdapters((d.value as { adapters?: DeviceAdapter[] }).adapters ?? []);
            else { setAdapters([]); errs.adapters = why(d); }

            if (m.status === "fulfilled") setProviders((m.value as { providers?: ModelProvider[] }).providers ?? []);
            else { setProviders([]); errs.providers = why(m); }

            if (u.status === "fulfilled") setUsers(Array.isArray(u.value) ? (u.value as UserAccount[]) : []);
            else { setUsers([]); errs.users = why(u); }

            const ok = h.status === "fulfilled";
            const r = ok ? (h.value as Readiness) : null;
            setHistory((cur) =>
                [...cur, { time: new Date().toLocaleTimeString(), api: r?.status === "ready", db: r?.database === "connected" }].slice(-12)
            );
            setErrors(errs);
            setLastUpdated(new Date().toLocaleTimeString());
        },
        [router]
    );

    useEffect(() => {
        const token = sessionStorage.getItem(TOKEN_KEY);
        const stored = sessionStorage.getItem(IDENTITY_KEY);

        if (!token || !stored) {
            router.replace("/login");
            return;
        }

        try {
            const parsed: Identity = JSON.parse(stored);
            if (parsed.role !== "ADMIN") {
                router.replace("/login");
                return;
            }
            setIdentity(parsed);
            loadDashboard(token).finally(() => setLoading(false));
        } catch {
            sessionStorage.removeItem(IDENTITY_KEY);
            router.replace("/login");
        }
    }, [router, loadDashboard]);

    useEffect(() => {
        if (!auto) return;
        const id = setInterval(() => {
            const token = sessionStorage.getItem(TOKEN_KEY);
            if (token) loadDashboard(token);
        }, 30000);
        return () => clearInterval(id);
    }, [auto, loadDashboard]);

    useEffect(() => {
        const tick = () => setNow(new Date().toISOString().slice(11, 19) + " UTC");
        tick();
        const id = setInterval(tick, 1000);
        return () => clearInterval(id);
    }, []);

    useEffect(() => {
        if (!toast) return;
        const id = setTimeout(() => setToast(""), 3000);
        return () => clearTimeout(id);
    }, [toast]);

    useEffect(() => {
        if (!selectedUser) return;
        const onKey = (e: KeyboardEvent) => e.key === "Escape" && setSelectedUser(null);
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [selectedUser]);

    async function refresh() {
        const token = sessionStorage.getItem(TOKEN_KEY);
        if (!token) {
            router.replace("/login");
            return;
        }
        setRefreshing(true);
        try {
            await loadDashboard(token);
            setToast("Checks refreshed");
        } finally {
            setRefreshing(false);
        }
    }

    function logout() {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(IDENTITY_KEY);
        router.replace("/login");
    }

    /* ----- derived data ----- */
    const systemHealthy = readiness?.status === "ready";
    const databaseConnected = readiness?.database === "connected";
    const adaptersConnected = adapters.filter((a) => a.is_connected).length;
    const providersEnabled = providers.filter((p) => p.is_enabled).length;
    const activeUsers = users.filter((u) => u.is_active).length;
    const failed = Object.entries(errors) as [ServiceKey, string][];

    const roles = useMemo(() => Array.from(new Set(users.map((u) => u.role))).sort(), [users]);
    const roleCounts = useMemo(
        () => roles.map((r) => ({ role: r, count: users.filter((u) => u.role === r).length })),
        [roles, users]
    );

    const filteredUsers = useMemo(() => {
        const q = query.trim().toLowerCase();
        return users.filter(
            (u) =>
                (!q || u.username.toLowerCase().includes(q)) &&
                (roleFilter === "All" || u.role === roleFilter) &&
                (statusFilter === "All" || (statusFilter === "Active" ? u.is_active : !u.is_active))
        );
    }, [users, query, roleFilter, statusFilter]);

    const newest = useMemo(
        () => [...users].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 4),
        [users]
    );

    const shownAdapters = adapters.filter((a) => a.provider_id.toLowerCase().includes(adapterQuery.trim().toLowerCase()));

    function clearFilters() {
        setQuery("");
        setRoleFilter("All");
        setStatusFilter("All");
    }

    function exportCsv() {
        const rows = [
            ["username", "role", "status", "registered"],
            ...filteredUsers.map((u) => [u.username, roleLabel(u.role), u.is_active ? "Active" : "Inactive", formatDate(u.created_at)]),
        ];
        const csv = rows.map((r) => r.map(csvCell).join(",")).join("\n");
        const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        const a = document.createElement("a");
        a.href = url;
        a.download = "meliora-accounts.csv";
        a.click();
        URL.revokeObjectURL(url);
        setToast(`Exported ${filteredUsers.length} account${filteredUsers.length === 1 ? "" : "s"}`);
    }

    async function copyId(id: string) {
        try {
            await navigator.clipboard.writeText(id);
            setToast("Account ID copied");
        } catch {
            setToast("Could not copy. Select the ID and copy it manually.");
        }
    }

    /* ----- loading screen ----- */
    if (loading || !identity) {
        return (
            <main className={cx(dashboardStyles.dashboard, ui.variable, num.variable)} data-theme="dark">
                <div className={styles.loadingScreen}>
                    <div className={styles.loader} />
                    <p>Initializing mission control...</p>
                </div>
            </main>
        );
    }

    const initials = identity.username.slice(0, 2).toUpperCase();

    /* ----- reusable blocks ----- */
    const metric = (
        icon: string, label: string, value: string, unit: string, tone: "good" | "bad" | "neutral", chip: string, to: AdminPage
    ) => (
        <button type="button" className={dashboardStyles.metricCard} onClick={() => setPage(to)}>
            <span className={styles.cardTop}>
                <span className={styles.statIcon}><Icon name={icon} /></span>
                <span className={dashboardStyles.metricName}>{label}</span>
            </span>
            <span className={dashboardStyles.metricValue}>{value} <small>{unit}</small></span>
            <span className={dashboardStyles.metricBottom}>
                <Status tone={tone}>{chip}</Status>
            </span>
        </button>
    );

    const dots = (key: "api" | "db") => (
        <div className={styles.dots} aria-label={key === "api" ? "Application check history" : "Database check history"}>
            {history.map((h, i) => (
                <i key={`${key}-${i}`} className={h[key] ? styles.dotOk : styles.dotBad} title={`${h.time}: ${h[key] ? "OK" : "Failed"}`} />
            ))}
        </div>
    );

    return (
        <main className={cx(dashboardStyles.dashboard, ui.variable, num.variable)} data-theme={dark ? "dark" : "light"}>
            <div className={dashboardStyles.shell}>
                {/* SIDEBAR */}
                <aside className={dashboardStyles.sidebar}>
                    <div className={dashboardStyles.brand}>
                        <h2>Meliora</h2>
                        <span>Mission control</span>
                    </div>

                    <nav aria-label="Main">
                        {NAV.map((n) => (
                            <button
                                key={n.name}
                                type="button"
                                onClick={() => setPage(n.name)}
                                aria-current={page === n.name ? "page" : undefined}
                                className={cx(dashboardStyles.navItem, page === n.name && dashboardStyles.active)}
                            >
                                <Icon name={n.icon} />
                                {n.name}
                                {n.name === "System health" && failed.length > 0 && (
                                    <span className={dashboardStyles.navBadge}>{failed.length}</span>
                                )}
                            </button>
                        ))}
                    </nav>

                    <div className={dashboardStyles.sidebarBottom}>
                        <b>{identity.username}</b>
                        <span>Administrator</span>
                        <span>Engineering prototype. Not a certified medical device.</span>
                        <button type="button" className={styles.logout} onClick={logout}>
                            <Icon name="logout" /> Sign out
                        </button>
                    </div>
                </aside>

                {/* MAIN */}
                <section className={dashboardStyles.main}>
                    <header className={dashboardStyles.header}>
                        <div>
                            <p className={dashboardStyles.crumb}>Administration</p>
                            <h2>{info.title}</h2>
                        </div>
                        <div className={dashboardStyles.tools}>
                            <span className={dashboardStyles.clock}>{now}</span>
                            <button
                                type="button"
                                role="switch"
                                aria-checked={auto}
                                onClick={() => setAuto(!auto)}
                                className={cx(dashboardStyles.switchBtn, auto && dashboardStyles.switchOn)}
                            >
                                <span className={dashboardStyles.switchKnob} />
                                Auto refresh
                            </button>
                            <button
                                type="button"
                                className={cx(dashboardStyles.iconBtn, styles.round)}
                                onClick={refresh}
                                disabled={refreshing}
                                aria-label="Refresh checks"
                            >
                                <span className={refreshing ? styles.spin : undefined}><Icon name="refresh" /></span>
                            </button>
                            <button
                                type="button"
                                className={cx(dashboardStyles.iconBtn, styles.round)}
                                onClick={() => setDark(!dark)}
                                aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
                            >
                                <Icon name={dark ? "sun" : "moon"} />
                            </button>
                            <div className={dashboardStyles.profile}>
                                <div className={dashboardStyles.avatar}>{initials}</div>
                                <span>Administrator</span>
                            </div>
                        </div>
                    </header>

                    <div className={dashboardStyles.content} key={page}>
                        <div className={dashboardStyles.hero}>
                            <div>
                                <h1>{page === "Overview" ? "Mission systems at a glance" : info.title}</h1>
                                <p>{page === "Overview" ? `Last checked ${lastUpdated || "—"}` : info.blurb}</p>
                            </div>
                            <button type="button" className={dashboardStyles.cta} onClick={refresh} disabled={refreshing}>
                                <Icon name="refresh" /> {refreshing ? "Refreshing..." : "Refresh now"}
                            </button>
                        </div>

                        {failed.length > 0 && (
                            <div className={styles.banner} role="alert">
                                <b>!</b>
                                <span>
                                    {failed.map(([k, msg]) => `${SERVICE_LABEL[k]}: ${msg}`).join(" · ")}. Some information may be unavailable.
                                </span>
                            </div>
                        )}

                        {/* ===== OVERVIEW ===== */}
                        {page === "Overview" && (
                            <>
                                <div className={dashboardStyles.metricGrid}>
                                    {metric("server", "Application API", systemHealthy ? "Online" : "Offline", "", systemHealthy ? "good" : "bad", systemHealthy ? "Ready" : "Not ready", "System health")}
                                    {metric("database", "Database", databaseConnected ? "Connected" : "Down", "", databaseConnected ? "good" : "bad", databaseConnected ? "PostgreSQL" : "Disconnected", "System health")}
                                    {metric("radio", "Device adapters", `${adaptersConnected}/${adapters.length}`, "connected", adapters.length ? "good" : "neutral", `${adapters.length} registered`, "Integrations")}
                                    {metric("cpu", "Analytical models", `${providersEnabled}/${providers.length}`, "enabled", "neutral", `${providers.length} registered`, "Analytics")}
                                </div>

                                <div className={dashboardStyles.row2}>
                                    <section className={dashboardStyles.card}>
                                        <div className={dashboardStyles.cardHead}>
                                            <div>
                                                <h3>Service checks</h3>
                                                <p>Version {readiness?.version ?? "—"}</p>
                                            </div>
                                            <button type="button" className={dashboardStyles.linkBtn} onClick={() => setPage("System health")}>Details</button>
                                        </div>
                                        <ul className={styles.svcList}>
                                            {(Object.keys(SERVICE_LABEL) as ServiceKey[]).map((k) => (
                                                <li key={k}>
                                                    <span>{SERVICE_LABEL[k]}</span>
                                                    {errors[k] ? <Status tone="bad">{errors[k]}</Status> : <Status tone="good">Responding</Status>}
                                                </li>
                                            ))}
                                        </ul>
                                    </section>

                                    <section className={dashboardStyles.card}>
                                        <div className={dashboardStyles.cardHead}>
                                            <h3>Accounts</h3>
                                            <button type="button" className={dashboardStyles.linkBtn} onClick={() => setPage("Users")}>Manage</button>
                                        </div>
                                        <p className={styles.bigNumber}>{users.length} <small>total, {activeUsers} active</small></p>
                                        <ul className={styles.bars}>
                                            {roleCounts.map((r) => (
                                                <li key={r.role}>
                                                    <span>{roleLabel(r.role)}</span>
                                                    <b>{r.count}</b>
                                                    <div className={dashboardStyles.progress} aria-hidden="true">
                                                        <span style={{ width: `${users.length ? (r.count / users.length) * 100 : 0}%` }} />
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                        {roleCounts.length === 0 && <p className={dashboardStyles.quiet}>No accounts returned by the user service.</p>}
                                    </section>
                                </div>

                                <div className={dashboardStyles.row3}>
                                    <section className={dashboardStyles.card}>
                                        <h3>Newest accounts</h3>
                                        {newest.length === 0 ? (
                                            <p className={dashboardStyles.quiet}>No accounts to show yet.</p>
                                        ) : (
                                            <ul className={styles.people}>
                                                {newest.map((u) => (
                                                    <li key={u.id}>
                                                        <button type="button" onClick={() => setSelectedUser(u)}>
                                                            <span className={styles.mini}>{u.username.slice(0, 2).toUpperCase()}</span>
                                                            <span className={styles.personText}>
                                                                <b>{u.username}</b>
                                                                <small>{roleLabel(u.role)} · {formatDate(u.created_at)}</small>
                                                            </span>
                                                            <Status tone={u.is_active ? "good" : "bad"}>{u.is_active ? "Active" : "Inactive"}</Status>
                                                        </button>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </section>

                                    <section className={dashboardStyles.card}>
                                        <h3>Safety notes</h3>
                                        <ul className={styles.notes}>
                                            <li><Icon name="shield" /> Analytical models stay off unless a provider is explicitly enabled.</li>
                                            <li><Icon name="shield" /> Analytical output is experimental and cannot change clinical thresholds.</li>
                                            <li><Icon name="shield" /> This console is read-only. Account changes are not available here.</li>
                                        </ul>
                                    </section>
                                </div>
                            </>
                        )}

                        {/* ===== SYSTEM HEALTH ===== */}
                        {page === "System health" && (
                            <>
                                <div className={dashboardStyles.vitalGrid}>
                                    <article className={dashboardStyles.card}>
                                        <div className={styles.cardTop}>
                                            <span className={styles.statIcon}><Icon name="server" /></span>
                                            <span className={dashboardStyles.metricName}>Application API</span>
                                            <span className={styles.push}><Status tone={systemHealthy ? "good" : "bad"}>{systemHealthy ? "Ready" : "Not ready"}</Status></span>
                                        </div>
                                        <dl className={styles.kv}>
                                            <div><dt>Status</dt><dd>{readiness?.status ?? "Unavailable"}</dd></div>
                                            <div><dt>Version</dt><dd>{readiness?.version ?? "—"}</dd></div>
                                            <div><dt>Framework</dt><dd>FastAPI</dd></div>
                                            <div><dt>Last checked</dt><dd>{lastUpdated || "—"}</dd></div>
                                        </dl>
                                        {dots("api")}
                                    </article>

                                    <article className={dashboardStyles.card}>
                                        <div className={styles.cardTop}>
                                            <span className={styles.statIcon}><Icon name="database" /></span>
                                            <span className={dashboardStyles.metricName}>Database</span>
                                            <span className={styles.push}><Status tone={databaseConnected ? "good" : "bad"}>{databaseConnected ? "Connected" : "Disconnected"}</Status></span>
                                        </div>
                                        <dl className={styles.kv}>
                                            <div><dt>Connection</dt><dd>{readiness?.database ?? "Unavailable"}</dd></div>
                                            <div><dt>Engine</dt><dd>PostgreSQL</dd></div>
                                            <div><dt>Last checked</dt><dd>{lastUpdated || "—"}</dd></div>
                                        </dl>
                                        {dots("db")}
                                    </article>
                                </div>
                                <p className={dashboardStyles.quiet}>
                                    The dots show the checks made since you opened this screen (last 12). Turn on auto refresh to check every 30 seconds.
                                </p>
                            </>
                        )}

                        {/* ===== INTEGRATIONS ===== */}
                        {page === "Integrations" && (
                            <>
                                <div className={styles.toolbar}>
                                    <label className={styles.search}>
                                        <Icon name="search" />
                                        <input value={adapterQuery} onChange={(e) => setAdapterQuery(e.target.value)} placeholder="Search adapters" aria-label="Search adapters" />
                                    </label>
                                    <span className={styles.count}>{shownAdapters.length} of {adapters.length} shown</span>
                                </div>

                                {errors.adapters ? (
                                    <Empty icon="radio" title="Could not load adapters" text={errors.adapters} />
                                ) : adapters.length === 0 ? (
                                    <Empty icon="radio" title="No adapters registered" text="No external device adapters are configured in this deployment." />
                                ) : shownAdapters.length === 0 ? (
                                    <Empty icon="search" title="No adapter matches" text="Try a different search term." />
                                ) : (
                                    <div className={dashboardStyles.acc}>
                                        {shownAdapters.map((a) => {
                                            const key = `ad-${a.provider_id}`;
                                            const open = openRow === key;
                                            return (
                                                <div key={key} className={cx(dashboardStyles.accItem, open && dashboardStyles.accOpen)}>
                                                    <button type="button" className={dashboardStyles.accHead} aria-expanded={open} onClick={() => setOpenRow(open ? null : key)}>
                                                        <span><b>{a.provider_id}</b><small>Version {a.version}</small></span>
                                                        <Status tone={a.is_connected ? "good" : "neutral"}>{a.is_connected ? "Connected" : "Disconnected"}</Status>
                                                        <span className={dashboardStyles.chev}><Icon name="chevron" /></span>
                                                    </button>
                                                    {open && (
                                                        <div className={dashboardStyles.accBody}>
                                                            <p>Supported measurement types</p>
                                                            {a.supported_measurement_types.length ? (
                                                                <div className={styles.tags}>
                                                                    {a.supported_measurement_types.map((t) => <span key={t} className={styles.tag}>{t.replaceAll("_", " ")}</span>)}
                                                                </div>
                                                            ) : (
                                                                <p className={dashboardStyles.quiet}>None declared.</p>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </>
                        )}

                        {/* ===== ANALYTICS ===== */}
                        {page === "Analytics" && (
                            <>
                                <div className={styles.notice}>
                                    <Icon name="shield" />
                                    <span>Analytical output is experimental and never changes clinical thresholds. MELIORA makes no predictions without an enabled provider.</span>
                                </div>

                                {errors.providers ? (
                                    <Empty icon="cpu" title="Could not load providers" text={errors.providers} />
                                ) : providers.length === 0 ? (
                                    <Empty icon="cpu" title="No analytical providers registered" text="No model providers are configured in this deployment." />
                                ) : (
                                    <div className={dashboardStyles.acc}>
                                        {providers.map((p) => {
                                            const key = `pr-${p.provider_id}`;
                                            const open = openRow === key;
                                            return (
                                                <div key={key} className={cx(dashboardStyles.accItem, open && dashboardStyles.accOpen)}>
                                                    <button type="button" className={dashboardStyles.accHead} aria-expanded={open} onClick={() => setOpenRow(open ? null : key)}>
                                                        <span><b>{p.provider_id}</b><small>Model version {p.model_version}</small></span>
                                                        <Status tone={p.is_enabled ? "good" : "neutral"}>{p.is_enabled ? "Enabled" : "Disabled"}</Status>
                                                        <span className={dashboardStyles.chev}><Icon name="chevron" /></span>
                                                    </button>
                                                    {open && (
                                                        <div className={dashboardStyles.accBody}>
                                                            <p>Capabilities</p>
                                                            {p.capabilities.length ? (
                                                                <div className={styles.tags}>
                                                                    {p.capabilities.map((c) => <span key={c} className={styles.tag}>{c.replaceAll("_", " ")}</span>)}
                                                                </div>
                                                            ) : (
                                                                <p className={dashboardStyles.quiet}>None declared.</p>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </>
                        )}

                        {/* ===== USERS ===== */}
                        {page === "Users" && (
                            <>
                                <div className={dashboardStyles.statRow}>
                                    <div className={dashboardStyles.stat}><span>Total accounts</span><b>{users.length}</b></div>
                                    <div className={dashboardStyles.stat}><span>Active</span><b>{activeUsers}</b></div>
                                    <div className={dashboardStyles.stat}><span>Inactive</span><b>{users.length - activeUsers}</b></div>
                                </div>

                                <section className={dashboardStyles.card}>
                                    <div className={styles.toolbar}>
                                        <label className={styles.search}>
                                            <Icon name="search" />
                                            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by username" aria-label="Search by username" />
                                        </label>
                                        <button type="button" className={styles.ghost} onClick={exportCsv} disabled={filteredUsers.length === 0}>
                                            <Icon name="download" /> Export CSV
                                        </button>
                                    </div>

                                    <div className={dashboardStyles.pills} role="group" aria-label="Filter by role">
                                        {["All", ...roles].map((r) => (
                                            <button key={r} type="button" aria-pressed={roleFilter === r} onClick={() => setRoleFilter(r)}
                                                className={cx(dashboardStyles.pill, roleFilter === r && dashboardStyles.pillActive)}>
                                                {r === "All" ? "All roles" : roleLabel(r)}
                                            </button>
                                        ))}
                                    </div>
                                    <div className={dashboardStyles.pills} role="group" aria-label="Filter by status">
                                        {(["All", "Active", "Inactive"] as const).map((s) => (
                                            <button key={s} type="button" aria-pressed={statusFilter === s} onClick={() => setStatusFilter(s)}
                                                className={cx(dashboardStyles.pill, statusFilter === s && dashboardStyles.pillActive)}>
                                                {s === "All" ? "Any status" : s}
                                            </button>
                                        ))}
                                    </div>

                                    {errors.users ? (
                                        <Empty icon="users" title="Could not load accounts" text={errors.users} />
                                    ) : users.length === 0 ? (
                                        <Empty icon="users" title="No user accounts found" text="No registered accounts were returned by the user service." />
                                    ) : filteredUsers.length === 0 ? (
                                        <Empty icon="search" title="No accounts match" text="Try a different search or clear the filters."
                                            action={<button type="button" className={dashboardStyles.linkBtn} onClick={clearFilters}>Clear filters</button>} />
                                    ) : (
                                        <div className={styles.tableWrap}>
                                            <table>
                                                <thead>
                                                    <tr><th>Username</th><th>Role</th><th>Status</th><th>Registered</th><th>Assigned crew</th></tr>
                                                </thead>
                                                <tbody>
                                                    {filteredUsers.map((u) => (
                                                        <tr key={u.id}>
                                                            <td><button type="button" className={styles.rowBtn} onClick={() => setSelectedUser(u)}>{u.username}</button></td>
                                                            <td>{roleLabel(u.role)}</td>
                                                            <td><Status tone={u.is_active ? "good" : "bad"}>{u.is_active ? "Active" : "Inactive"}</Status></td>
                                                            <td>{formatDate(u.created_at)}</td>
                                                            <td>{u.assigned_crew_ids.length || "—"}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                    <p className={dashboardStyles.quiet}>Account information is read-only in this view. Showing {filteredUsers.length} of {users.length}.</p>
                                </section>
                            </>
                        )}

                        <footer className={styles.footer}>
                            <span>Meliora · Astronaut health monitoring</span>
                            <span>Administrative access · Restricted</span>
                        </footer>
                    </div>
                </section>
            </div>

            {/* USER DETAILS */}
            {selectedUser && (
                <div className={dashboardStyles.overlay} onClick={() => setSelectedUser(null)}>
                    <div className={dashboardStyles.modal} role="dialog" aria-modal="true" aria-labelledby="user-title" onClick={(e) => e.stopPropagation()}>
                        <div className={dashboardStyles.modalHead}>
                            <h3 id="user-title">{selectedUser.username}</h3>
                            <button type="button" className={cx(dashboardStyles.iconBtn, styles.round)} onClick={() => setSelectedUser(null)} aria-label="Close">
                                <Icon name="close" />
                            </button>
                        </div>
                        <dl className={styles.kv}>
                            <div><dt>Role</dt><dd>{roleLabel(selectedUser.role)}</dd></div>
                            <div><dt>Status</dt><dd>{selectedUser.is_active ? "Active" : "Inactive"}</dd></div>
                            <div><dt>Account ID</dt><dd className={styles.mono}>{selectedUser.id}</dd></div>
                            <div><dt>Crew member ID</dt><dd className={styles.mono}>{selectedUser.crew_member_id ?? "—"}</dd></div>
                            <div><dt>Assigned crew</dt><dd>{selectedUser.assigned_crew_ids.length || "None"}</dd></div>
                            <div><dt>Registered</dt><dd>{formatDateTime(selectedUser.created_at)}</dd></div>
                            <div><dt>Last updated</dt><dd>{formatDateTime(selectedUser.updated_at)}</dd></div>
                        </dl>
                        <div className={dashboardStyles.modalActions}>
                            <button type="button" className={dashboardStyles.ghostBtn} onClick={() => copyId(selectedUser.id)}>
                                <Icon name="copy" /> Copy ID
                            </button>
                            <button type="button" className={dashboardStyles.cta} onClick={() => setSelectedUser(null)}>Close</button>
                        </div>
                    </div>
                </div>
            )}

            {toast && <div className={dashboardStyles.toast} role="status">{toast}</div>}
        </main>
    );
}

