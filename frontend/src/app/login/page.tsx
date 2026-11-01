"use client";

import { useState } from "react";
import SolarSystem from "../../components/SolarSystem";
import styles from "./login.module.css";

export default function LoginPage() {
    const [role, setRole] = useState("Crew Member");

    return (
        <main className={styles.page}>
            <SolarSystem />

            <section className={styles.card}>
                <div className={styles.logo}>
                    <h1>MELIORA</h1>
                    <p>ASTRONAUT HEALTH MONITORING</p>
                </div>

                <h2 className={styles.heading}>Welcome back</h2>
                <p className={styles.description}>
                    Sign in to access your mission dashboard.
                </p>

                <label className={styles.roleLabel}>SELECT YOUR ROLE</label>

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
                </div>

                <form onSubmit={(event) => event.preventDefault()}>
                    <div className={styles.field}>
                        <label className={styles.inputLabel} htmlFor="email">
                            Email address
                        </label>
                        <input
                            className={styles.input}
                            id="email"
                            type="email"
                            placeholder="Enter your email"
                            required
                        />
                    </div>

                    <div className={styles.field}>
                        <label className={styles.inputLabel} htmlFor="password">
                            Password
                        </label>
                        <input
                            className={styles.input}
                            id="password"
                            type="password"
                            placeholder="Enter your password"
                            required
                        />
                    </div>

                    <button className={styles.submit} type="submit">
                        Sign In
                    </button>
                </form>

                <p className={styles.note}>
                    Selected access: {role}
                    <br />
                    Authentication will be connected to the mission backend.
                </p>
            </section>
        </main>
    );
}