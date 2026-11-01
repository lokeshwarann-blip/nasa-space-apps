import styles from "./SolarSystem.module.css";

export default function SolarSystem() {
    return (
        <div className={styles.background} aria-hidden="true">
            <div className={styles.solarSystem}>
                <div className={styles.sun} />

                <div className={`${styles.orbit} ${styles.mercuryOrbit}`}>
                    <span className={`${styles.planet} ${styles.mercury}`} />
                </div>

                <div className={`${styles.orbit} ${styles.venusOrbit}`}>
                    <span className={`${styles.planet} ${styles.venus}`} />
                </div>

                <div className={`${styles.orbit} ${styles.earthOrbit}`}>
                    <span className={`${styles.planet} ${styles.earth}`} />
                </div>

                <div className={`${styles.orbit} ${styles.marsOrbit}`}>
                    <span className={`${styles.planet} ${styles.mars}`} />
                </div>

                <div className={`${styles.orbit} ${styles.jupiterOrbit}`}>
                    <span className={`${styles.planet} ${styles.jupiter}`} />
                </div>

                <div className={`${styles.orbit} ${styles.saturnOrbit}`}>
                    <span className={`${styles.planet} ${styles.saturn}`} />
                </div>

                <div className={`${styles.orbit} ${styles.uranusOrbit}`}>
                    <span className={`${styles.planet} ${styles.uranus}`} />
                </div>

                <div className={`${styles.orbit} ${styles.neptuneOrbit}`}>
                    <span className={`${styles.planet} ${styles.neptune}`} />
                </div>
            </div>
        </div>
    );
}