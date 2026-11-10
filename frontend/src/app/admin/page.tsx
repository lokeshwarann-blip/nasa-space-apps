
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Manrope, Space_Grotesk } from "next/font/google";
import dashboardStyles from "../dashboard/dashboard.module.css";
import styles from "./admin.module.css";

const ui = Manrope({
    subsets: ["latin"],
    variable: "--font-ui",
    display: "swap",
});

const num = Space_Grotesk({
    subsets: ["latin"],
    variable: "--font-num",
    display: "swap",
});

const API_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

interface Identity {
    username: string;
    role: string;
}

interface Readiness {
    status: string;
    database: string;
    version: string;
}

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

export default function AdminPage() {
    const router = useRouter();

    const [dark, setDark] = useState(true);

    const [identity, setIdentity] = useState<Identity | null>(null);
    const [readiness, setReadiness] = useState<Readiness | null>(null);
    const [adapters, setAdapters] = useState<DeviceAdapter[]>([]);
    const [providers, setProviders] = useState<ModelProvider[]>([]);
    const [users, setUsers] = useState<UserAccount[]>([]);

    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState("");
    const [lastUpdated, setLastUpdated] = useState("");

    const loadDashboard = useCallback(async (token: string) => {
        setError("");

        const headers = {
            Authorization: `Bearer ${token}`,
        };

        const results = await Promise.allSettled([
            fetch(`${API_URL}/health/ready`),
            fetch(`${API_URL}/api/v1/devices/adapters`, { headers }),
            fetch(`${API_URL}/api/v1/models/providers`, { headers }),
            fetch(`${API_URL}/api/v1/auth/users`, { headers }),
        ]);

        const [
            healthResult,
            deviceResult,
            modelResult,
            usersResult,
        ] = results;

        if (healthResult.status === "fulfilled" && healthResult.value.ok) {
            setReadiness(await healthResult.value.json());
        } else {
            setReadiness(null);
        }

        if (deviceResult.status === "fulfilled" && deviceResult.value.ok) {
            const data = await deviceResult.value.json();
            setAdapters(data.adapters ?? []);
        } else {
            setAdapters([]);
        }

        if (modelResult.status === "fulfilled" && modelResult.value.ok) {
            const data = await modelResult.value.json();
            setProviders(data.providers ?? []);
        } else {
            setProviders([]);
        }

        if (usersResult.status === "fulfilled" && usersResult.value.ok) {
            const data = await usersResult.value.json();
            setUsers(Array.isArray(data) ? data : []);
        } else {
            setUsers([]);
        }

        const failures = results.filter(
            (result) =>
                result.status === "rejected" ||
                (result.status === "fulfilled" && !result.value.ok)
        );

        if (failures.length > 0) {
            setError(
                `${failures.length} service check(s) could not be completed. Some information may be unavailable.`
            );
        }

        setLastUpdated(new Date().toLocaleTimeString());
    }, []);

    useEffect(() => {
        const token = sessionStorage.getItem("meliora_access_token");
        const storedIdentity = sessionStorage.getItem("meliora_identity");

        if (!token || !storedIdentity) {
            router.replace("/login");
            return;
        }

        try {
            const parsed = JSON.parse(storedIdentity);

            if (parsed.role !== "ADMIN") {
                router.replace("/login");
                return;
            }

            setIdentity(parsed);
            loadDashboard(token).finally(() => setLoading(false));
        } catch {
            sessionStorage.removeItem("meliora_identity");
            router.replace("/login");
        }
    }, [router, loadDashboard]);

    async function refreshDashboard() {
        const token = sessionStorage.getItem("meliora_access_token");

        if (!token) {
            router.replace("/login");
            return;
        }

        setRefreshing(true);

        try {
            await loadDashboard(token);
        } finally {
            setRefreshing(false);
        }
    }

    function logout() {
        sessionStorage.removeItem("meliora_access_token");
        sessionStorage.removeItem("meliora_identity");
        router.replace("/login");
    }

    function formatDate(date: string) {
        if (!date) return "—";

        const parsed = new Date(date);

        if (Number.isNaN(parsed.getTime())) return "—";

        return parsed.toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    }

    if (loading || !identity) {
        return (
            <main className={styles.loadingScreen}>
                <div className={styles.loader} />
                <p>Initializing mission control...</p>
            </main>
        );
    }

    const systemHealthy = readiness?.status === "ready";
    const databaseConnected = readiness?.database === "connected";

    const activeUsers = users.filter((user) => user.is_active).length;

    return (
        <main
            className={`${dashboardStyles.dashboard} ${ui.variable} ${num.variable}`}
            data-theme={dark ? "dark" : "light"}
        >
            <div className={dashboardStyles.shell}>
                <aside className={dashboardStyles.sidebar}>
                    <div className={dashboardStyles.brand}>
                        <h2>MELIORA</h2>
                        <span>MISSION CONTROL</span>
                    </div>

                    <nav>
                        <a
                            href="#overview"
                            className={`${dashboardStyles.navItem} ${dashboardStyles.active}`}
                        >
                            <span>▦</span>
                            Overview
                        </a>

                        <a
                            href="#system-health"
                            className={dashboardStyles.navItem}
                        >
                            <span>⌘</span>
                            System health
                        </a>

                        <a
                            href="#integrations"
                            className={dashboardStyles.navItem}
                        >
                            <span>◈</span>
                            Integrations
                        </a>

                        <a
                            href="#users"
                            className={dashboardStyles.navItem}
                        >
                            <span>♙</span>
                            User management
                        </a>
                    </nav>

                    <div className={dashboardStyles.sidebarBottom}>
                        <strong>{identity.username}</strong>
                        <span>Administrator</span>

                        <button
                            type="button"
                            className={styles.logout}
                            onClick={logout}
                        >
                            Sign out <span>↗</span>
                        </button>
                    </div>
                </aside>

                <section className={dashboardStyles.main}>
                    <header className={dashboardStyles.header}>
                        <div>
                            <p className={dashboardStyles.crumb}>
                                MELIORA / ADMINISTRATION
                            </p>
                            <h2>Mission overview</h2>
                        </div>

                        <div className={dashboardStyles.tools}>
                            <span className={styles.liveLabel}>
                                <span className={styles.liveDot} />
                                SYSTEM MONITORING
                            </span>

                            <button
                                type="button"
                                className={styles.refreshButton}
                                onClick={refreshDashboard}
                                disabled={refreshing}
                            >
                                {refreshing ? "Refreshing..." : "↻ Refresh"}
                            </button>

                            <button
                                type="button"
                                className={`${dashboardStyles.switchBtn} ${dark ? dashboardStyles.switchOn : ""
                                    }`}
                                onClick={() => setDark((current) => !current)}
                                aria-label={`Switch to ${dark ? "light" : "dark"} theme`}
                                aria-pressed={dark}
                            >
                                <span className={dashboardStyles.switchKnob} />
                                {dark ? "Dark mode" : "Light mode"}
                            </button>
                        </div>
                    </header>

                    <div className={dashboardStyles.content}>
                        <section className={styles.welcome} id="overview">
                            <div>
                                <p className={styles.eyebrow}>
                                    ADMINISTRATIVE CONSOLE
                                </p>

                                <h1>Mission systems at a glance.</h1>

                                <p>
                                    Monitor infrastructure, integrations and
                                    analytical services from one workspace.
                                </p>
                            </div>

                            <div className={styles.version}>
                                <span>DEPLOYMENT VERSION</span>
                                <strong>{readiness?.version ?? "—"}</strong>
                            </div>
                        </section>

                        {error && (
                            <div className={styles.warning}>
                                <span>!</span>
                                {error}
                            </div>
                        )}

                        {/* SYSTEM HEALTH */}

                        <div
                            className={styles.sectionHeading}
                            id="system-health"
                        >
                            <div>
                                <span>01 / INFRASTRUCTURE</span>
                                <h2>System health</h2>
                            </div>

                            <span className={styles.updated}>
                                Last checked: {lastUpdated || "—"}
                            </span>
                        </div>

                        <div className={styles.healthGrid}>
                            <article className={styles.healthCard}>
                                <div className={styles.cardTop}>
                                    <span>APPLICATION API</span>
                                    <span className={styles.cardIcon}>⌘</span>
                                </div>

                                <div className={styles.healthValue}>
                                    {systemHealthy ? "Operational" : "Unavailable"}
                                </div>

                                <div className={styles.cardFooter}>
                                    <span className={systemHealthy ? styles.good : styles.bad}>
                                        <i /> {systemHealthy ? "READY" : "NOT READY"}
                                    </span>
                                    <span>FastAPI</span>
                                </div>
                            </article>

                            <article className={styles.healthCard}>
                                <div className={styles.cardTop}>
                                    <span>DATABASE</span>
                                    <span className={styles.cardIcon}>▤</span>
                                </div>

                                <div className={styles.healthValue}>
                                    {databaseConnected ? "Connected" : "Unavailable"}
                                </div>

                                <div className={styles.cardFooter}>
                                    <span className={databaseConnected ? styles.good : styles.bad}>
                                        <i /> {databaseConnected ? "CONNECTED" : "DISCONNECTED"}
                                    </span>
                                    <span>PostgreSQL</span>
                                </div>
                            </article>

                            <article className={styles.healthCard}>
                                <div className={styles.cardTop}>
                                    <span>DEVICE ADAPTERS</span>
                                    <span className={styles.cardIcon}>◈</span>
                                </div>

                                <div className={styles.healthValue}>
                                    {adapters.filter((a) => a.is_connected).length}
                                    <small> / {adapters.length}</small>
                                </div>

                                <div className={styles.cardFooter}>
                                    <span className={styles.neutral}>
                                        <i /> REGISTERED / CONNECTED
                                    </span>
                                    <span>Integrations</span>
                                </div>
                            </article>

                            <article className={styles.healthCard}>
                                <div className={styles.cardTop}>
                                    <span>ANALYTICAL MODELS</span>
                                    <span className={styles.cardIcon}>✧</span>
                                </div>

                                <div className={styles.healthValue}>
                                    {providers.filter((p) => p.is_enabled).length}
                                    <small> / {providers.length}</small>
                                </div>

                                <div className={styles.cardFooter}>
                                    <span className={styles.neutral}>
                                        <i /> ENABLED / REGISTERED
                                    </span>
                                    <span>Providers</span>
                                </div>
                            </article>
                        </div>

                        {/* DEVICE INTEGRATIONS */}

                        <div
                            className={styles.sectionHeading}
                            id="integrations"
                        >
                            <div>
                                <span>02 / CONNECTIVITY</span>
                                <h2>Device integrations</h2>
                            </div>

                            <span className={styles.count}>
                                {adapters.length} REGISTERED
                            </span>
                        </div>

                        <section className={styles.panel}>
                            <div className={styles.panelHeader}>
                                <div>
                                    <h3>Registered adapters</h3>
                                    <p>External telemetry integration services</p>
                                </div>
                                <span className={styles.panelIcon}>◈</span>
                            </div>

                            {adapters.length === 0 ? (
                                <div className={styles.emptyState}>
                                    <div>◈</div>
                                    <strong>No adapters registered</strong>
                                    <p>
                                        No external device adapters are currently
                                        configured in this deployment.
                                    </p>
                                </div>
                            ) : (
                                <div className={styles.tableWrap}>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>PROVIDER</th>
                                                <th>VERSION</th>
                                                <th>MEASUREMENTS</th>
                                                <th>STATUS</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {adapters.map((adapter) => (
                                                <tr key={adapter.provider_id}>
                                                    <td>{adapter.provider_id}</td>
                                                    <td>{adapter.version}</td>
                                                    <td>
                                                        {adapter.supported_measurement_types.join(", ") || "—"}
                                                    </td>
                                                    <td>
                                                        <span className={adapter.is_connected ? styles.good : styles.neutral}>
                                                            <i />
                                                            {adapter.is_connected ? "Connected" : "Disconnected"}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        {/* ANALYTICAL PROVIDERS */}

                        <div className={styles.sectionHeading}>
                            <div>
                                <span>03 / ANALYTICS</span>
                                <h2>Analytical providers</h2>
                            </div>

                            <span className={styles.count}>
                                {providers.length} REGISTERED
                            </span>
                        </div>

                        <section className={styles.panel}>
                            <div className={styles.panelHeader}>
                                <div>
                                    <h3>Model registry</h3>
                                    <p>
                                        Versioned analytical services and safety state
                                    </p>
                                </div>
                                <span className={styles.panelIcon}>✧</span>
                            </div>

                            {providers.length === 0 ? (
                                <div className={styles.emptyState}>
                                    <div>✧</div>
                                    <strong>No analytical providers registered</strong>
                                    <p>
                                        No model providers are configured. MELIORA
                                        will not generate predictions without an
                                        enabled provider.
                                    </p>
                                </div>
                            ) : (
                                <div className={styles.tableWrap}>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>PROVIDER</th>
                                                <th>MODEL VERSION</th>
                                                <th>CAPABILITIES</th>
                                                <th>SAFETY STATE</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {providers.map((provider) => (
                                                <tr key={provider.provider_id}>
                                                    <td>{provider.provider_id}</td>
                                                    <td>{provider.model_version}</td>
                                                    <td>
                                                        {provider.capabilities.join(", ") || "—"}
                                                    </td>
                                                    <td>
                                                        <span className={provider.is_enabled ? styles.good : styles.neutral}>
                                                            <i />
                                                            {provider.is_enabled ? "Enabled" : "Disabled"}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </section>

                        {/* USER MANAGEMENT */}

                        <div className={styles.sectionHeading} id="users">
                            <div>
                                <span>04 / ACCESS CONTROL</span>
                                <h2>User management</h2>
                            </div>

                            <span className={styles.count}>
                                {users.length} REGISTERED
                            </span>
                        </div>

                        <section className={styles.panel}>
                            <div className={styles.panelHeader}>
                                <div>
                                    <h3>Registered accounts</h3>
                                    <p>
                                        Manage visibility of system accounts,
                                        roles and account status.
                                    </p>
                                </div>

                                <span className={styles.panelIcon}>♙</span>
                            </div>

                            <div className={styles.healthGrid}>
                                <article className={styles.healthCard}>
                                    <div className={styles.cardTop}>
                                        <span>TOTAL ACCOUNTS</span>
                                        <span className={styles.cardIcon}>♙</span>
                                    </div>
                                    <div className={styles.healthValue}>
                                        {users.length}
                                    </div>
                                    <div className={styles.cardFooter}>
                                        <span className={styles.neutral}>
                                            <i /> REGISTERED USERS
                                        </span>
                                    </div>
                                </article>

                                <article className={styles.healthCard}>
                                    <div className={styles.cardTop}>
                                        <span>ACTIVE ACCOUNTS</span>
                                        <span className={styles.cardIcon}>✓</span>
                                    </div>
                                    <div className={styles.healthValue}>
                                        {activeUsers}
                                    </div>
                                    <div className={styles.cardFooter}>
                                        <span className={styles.good}>
                                            <i /> ACTIVE
                                        </span>
                                    </div>
                                </article>
                            </div>

                            {users.length === 0 ? (
                                <div className={styles.emptyState}>
                                    <div>♙</div>
                                    <strong>No user accounts found</strong>
                                    <p>
                                        No registered accounts were returned
                                        by the user management service.
                                    </p>
                                </div>
                            ) : (
                                <div className={styles.tableWrap}>
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>USERNAME</th>
                                                <th>ROLE</th>
                                                <th>ACCOUNT STATUS</th>
                                                <th>REGISTERED</th>
                                            </tr>
                                        </thead>

                                        <tbody>
                                            {users.map((user) => (
                                                <tr key={user.id}>
                                                    <td>
                                                        <strong>{user.username}</strong>
                                                    </td>

                                                    <td>
                                                        {user.role.replaceAll("_", " ")}
                                                    </td>

                                                    <td>
                                                        <span
                                                            className={
                                                                user.is_active
                                                                    ? styles.good
                                                                    : styles.bad
                                                            }
                                                        >
                                                            <i />
                                                            {user.is_active
                                                                ? "Active"
                                                                : "Inactive"}
                                                        </span>
                                                    </td>

                                                    <td>
                                                        {formatDate(user.created_at)}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <p className={styles.updated}>
                                Account information is read-only in this view.
                            </p>
                        </section>

                        <footer className={styles.footer}>
                            <span>MELIORA · ASTRONAUT HEALTH MONITORING</span>
                            <span>ADMINISTRATIVE ACCESS · RESTRICTED</span>
                        </footer>
                    </div>
                </section>
            </div>
        </main>
    );
}
