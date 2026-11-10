
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import CelestialSphere from "../../components/ui/celestial-sphere";
import Spacecraft from "../../components/Spacecraft";
import styles from "./login.module.css";

const API_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function LoginPage() {
    const [role, setRole] = useState("Crew Member");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const router = useRouter();

    async function handleLogin(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError("");
        setLoading(true);

        try {
            // 1. Authenticate with the backend
            const loginResponse = await fetch(
                `${API_URL}/api/v1/auth/token`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        username,
                        password,
                    }),
                }
            );

            if (!loginResponse.ok) {
                throw new Error("Invalid username or password.");
            }

            const tokenData = await loginResponse.json();

            // 2. Verify the actual logged-in identity
            const profileResponse = await fetch(
                `${API_URL}/api/v1/auth/me`,
                {
                    headers: {
                        Authorization: `Bearer ${tokenData.access_token}`,
                    },
                }
            );

            if (!profileResponse.ok) {
                throw new Error("Could not verify your account.");
            }

            const identity = await profileResponse.json();

            // 3. Check the verified backend role
            const expectedRole =
                role === "Crew Member"
                    ? "CREW_MEMBER"
                    : role === "Flight Surgeon"
                        ? "FLIGHT_SURGEON"
                        : "ADMIN";
              if (identity.role !== expectedRole) {
               throw new Error("Your account does not match the selected role.");
           }

            // 4. Save the session for subsequent API requests
            sessionStorage.setItem(
                "meliora_access_token",
                tokenData.access_token
            );

            sessionStorage.setItem(
                "meliora_identity",
                JSON.stringify(identity)
            );

            // 5. Redirect using the verified role
            if (identity.role === "CREW_MEMBER") {
                router.push("/dashboard");
            } else if (identity.role === "FLIGHT_SURGEON") {
                router.push("/flight-sergeon");
            } else if (identity.role === "ADMIN") {
                router.push("/admin");
            }

        } catch (err) {
            setError(
                err instanceof Error
                    ? err.message
                    : "Unable to connect to the server."
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className={styles.page}>
            <CelestialSphere
                hue={220}
                speed={0.4}
                zoom={1.2}
                particleSize={4}
                className={styles.background}
            />

            <div className={styles.spacecraft}>
                <Spacecraft />
            </div>

            <section id="login-card" className={styles.card}>
                <div className={styles.logo}>
                    <h1>MELIORA</h1>
                    <p>ASTRONAUT HEALTH MONITORING</p>
                </div>

                <h2 className={styles.heading}>Welcome back</h2>

                <p className={styles.description}>
                    Sign in to access your mission dashboard.
                </p>

                <label className={styles.roleLabel}>
                    SELECT YOUR ROLE
                </label>

                <div className={styles.roles}>
                    <button
                        type="button"
                        className={`${styles.roleButton} ${role === "Crew Member" ? styles.selected : ""
                            }`}
                        aria-pressed={role === "Crew Member"}
                        onClick={() => setRole("Crew Member")}
                    >
                        Crew Member
                    </button>

                    <button
                        type="button"
                        className={`${styles.roleButton} ${role === "Flight Surgeon" ? styles.selected : ""
                            }`}
                        aria-pressed={role === "Flight Surgeon"}
                        onClick={() => setRole("Flight Surgeon")}
                    >
                        Flight Surgeon
                    </button>
                    <button
                        type="button"
                        className={`${styles.roleButton} ${role === "Admin" ? styles.selected : ""}`}
                        aria-pressed={role === "Admin"}
                        onClick={() => setRole("Admin")}
                    >
                        Admin
                    </button>
                </div>

                <form onSubmit={handleLogin}>
                    <div className={styles.field}>
                        <label
                            className={styles.inputLabel}
                            htmlFor="username"
                        >
                            Username
                        </label>

                        <input
                            className={styles.input}
                            id="username"
                            type="text"
                            placeholder="Enter your username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            minLength={3}
                            maxLength={64}
                            required
                        />
                    </div>

                    <div className={styles.field}>
                        <label
                            className={styles.inputLabel}
                            htmlFor="password"
                        >
                            Password
                        </label>

                        <input
                            className={styles.input}
                            id="password"
                            type="password"
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            minLength={8}
                            maxLength={128}
                            required
                        />
                    </div>

                    {error && (
                        <p
                            role="alert"
                            style={{
                                color: "#e05252",
                                fontSize: "13px",
                                marginBottom: "12px",
                            }}
                        >
                            {error}
                        </p>
                    )}

                    <button
                        className={styles.submit}
                        type="submit"
                        disabled={loading}
                    >
                        {loading ? "Authenticating..." : "Sign In"}
                    </button>
                </form>

                <p className={styles.note}>
                    Selected access: {role}
                    <br />
                    Secure mission authentication
                </p>
            </section>
        </main>
    );
}
