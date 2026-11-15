"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

type Props = {
    selectedZone?: string | null;
    onSelectOrgan?: (organName: string) => void;
    height?: number | string;
    reduceMotion?: boolean;
    className?: string;
    chipClassName?: string;
};

const ORGAN_NODES: Record<string, string> = {
    heart: "Heart",
    lungs: "Lungs",
    brain: "Brain",
    eyes: "Eyes",
    digestive: "Digestive_System",
    urinary: "Urinary_System",
    skeleton: "Skeleton",
    vessels: "Blood_Vessels",
    all: "ALL_BODY",
};

const LAYERS = [
    { id: "skeleton", label: "Skeleton" },
    { id: "brain", label: "Brain" },
    { id: "eyes", label: "Eyes" },
    { id: "heart", label: "Heart" },
    { id: "lungs", label: "Lungs" },
    { id: "digestive", label: "Digestive" },
    { id: "urinary", label: "Urinary" },
    { id: "vessels", label: "Vessels" },
];

export default function HumanBody({
    selectedZone,
    onSelectOrgan,
    height = "520px",
    reduceMotion = false,
    className,
}: Props) {
    const mountRef = useRef<HTMLDivElement>(null);
    const sceneRef = useRef<THREE.Scene | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
    const controlsRef = useRef<OrbitControls | null>(null);
    const modelRef = useRef<THREE.Object3D | null>(null);

    const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
    const [progress, setProgress] = useState(0);
    const [hidden, setHidden] = useState<string[]>([]);
    const [activeFocus, setActiveFocus] = useState<string>("all");

    const homeCamPos = useRef(new THREE.Vector3(0, 0.2, 1.8));
    const homeTarget = useRef(new THREE.Vector3(0, 0.1, 0));

    // Focus camera on specific anatomical organ
    const focusOnNode = (organKey: string) => {
        const camera = cameraRef.current;
        const controls = controlsRef.current;
        const model = modelRef.current;
        if (!camera || !controls || !model) return;

        setActiveFocus(organKey);

        if (organKey === "all") {
            camera.position.copy(homeCamPos.current);
            controls.target.copy(homeTarget.current);
            controls.update();
            return;
        }

        const nodeName = ORGAN_NODES[organKey];
        let targetNode: THREE.Object3D | null = null;

        if (nodeName) {
            targetNode = model.getObjectByName(nodeName) || null;
        }

        if (!targetNode) {
            targetNode = model.getObjectByName(organKey) || null;
        }

        if (!targetNode) {
            model.traverse((o) => {
                if (!targetNode && o.name.toLowerCase().includes(organKey.toLowerCase())) {
                    targetNode = o;
                }
            });
        }

        if (targetNode) {
            const box = new THREE.Box3().setFromObject(targetNode);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());

            controls.target.copy(center);

            const maxDim = Math.max(size.x, size.y, size.z, 0.08);
            const fov = THREE.MathUtils.degToRad(camera.fov);
            const dist = THREE.MathUtils.clamp((maxDim / 2) / Math.tan(fov / 2) * 1.8, 0.12, 2.5);

            const offset = new THREE.Vector3(0, maxDim * 0.15, dist);
            camera.position.copy(center).add(offset);
            camera.near = 0.005;
            camera.updateProjectionMatrix();
            controls.update();
        }
    };

    useEffect(() => {
        if (!selectedZone) return;
        const map: Record<string, string> = {
            heart: "heart",
            lungs: "lungs",
            brain: "brain",
            sleep: "brain",
            bones: "skeleton",
            muscles: "skeleton",
            immune: "vessels",
        };
        const target = map[selectedZone.toLowerCase()];
        if (target) focusOnNode(target);
    }, [selectedZone]);

    useEffect(() => {
        const mount = mountRef.current;
        if (!mount) return;

        const scene = new THREE.Scene();
        sceneRef.current = scene;

        const camera = new THREE.PerspectiveCamera(45, mount.clientWidth / mount.clientHeight, 0.005, 1000);
        cameraRef.current = camera;

        let renderer: THREE.WebGLRenderer;
        try {
            renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        } catch {
            setStatus("error");
            return;
        }
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(mount.clientWidth, mount.clientHeight);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.35;
        renderer.setClearColor(0x000000, 0);
        mount.appendChild(renderer.domElement);
        rendererRef.current = renderer;

        // Cinematic neutral lighting
        scene.add(new THREE.AmbientLight(0xffffff, 1.6));
        scene.add(new THREE.HemisphereLight(0xe8f4f8, 0x1b2832, 0.9));

        const key = new THREE.DirectionalLight(0xffffff, 2.6);
        key.position.set(3, 4, 5);
        scene.add(key);

        const fill = new THREE.DirectionalLight(0xdcf0fa, 1.4);
        fill.position.set(-4, 1.5, 3);
        scene.add(fill);

        const rim = new THREE.DirectionalLight(0xffffff, 2.0);
        rim.position.set(0, 3, -4);
        scene.add(rim);

        // Ground platform grid with wireframe styling
        const grid = new THREE.GridHelper(2.5, 12, 0xff4d5a, 0x333333);
        grid.position.y = -0.92;
        (grid.material as THREE.Material).transparent = true;
        (grid.material as THREE.Material).opacity = 0.2;
        scene.add(grid);

        // High-precision OrbitControls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.06;
        controls.enablePan = true;
        controls.panSpeed = 1.0;
        controls.enableZoom = true;
        controls.zoomSpeed = 1.2;
        controls.autoRotate = false;
        controls.minDistance = 0.03;
        controls.maxDistance = 8.0;
        controlsRef.current = controls;

        let mixer: THREE.AnimationMixer | null = null;
        let model: THREE.Object3D | null = null;
        let disposed = false;

        const fit = (obj: THREE.Object3D) => {
            const box = new THREE.Box3().setFromObject(obj);
            const size = box.getSize(new THREE.Vector3());
            const center = box.getCenter(new THREE.Vector3());
            obj.position.sub(center);

            const fov = THREE.MathUtils.degToRad(camera.fov);
            const dist = (size.y / 2) / Math.tan(fov / 2) * 1.12;

            camera.position.set(0, 0.15, dist);
            camera.near = 0.005;
            camera.far = 1000;
            camera.updateProjectionMatrix();

            controls.target.set(0, 0.1, 0);
            controls.minDistance = 0.03;
            controls.maxDistance = dist * 2.5;
            controls.update();

            homeCamPos.current.copy(camera.position);
            homeTarget.current.copy(controls.target);
        };

        const loader = new GLTFLoader();
        loader.load(
            "/models/human-body.glb",
            (gltf) => {
                if (disposed) return;
                model = gltf.scene;

                model.traverse((o) => {
                    const mesh = o as THREE.Mesh;
                    if (!mesh.isMesh) return;
                    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                    mats.forEach((m) => {
                        m.side = THREE.DoubleSide;
                        const std = m as THREE.MeshStandardMaterial;
                        if (std.normalMap) std.normalScale.set(1, -1);
                        std.needsUpdate = true;
                    });
                });

                scene.add(model);
                modelRef.current = model;
                fit(model);

                if (gltf.animations.length > 0) {
                    mixer = new THREE.AnimationMixer(model);
                    gltf.animations.forEach((clip) => mixer!.clipAction(clip).play());
                    if (reduceMotion && mixer) mixer.timeScale = 0;
                }
                setStatus("ready");
            },
            (e) => {
                if (e.total > 0) setProgress(Math.round((e.loaded / e.total) * 100));
            },
            () => {
                if (!disposed) setStatus("error");
            }
        );

        let raf = 0;
        const clock = new THREE.Clock();

        const animate = () => {
            raf = requestAnimationFrame(animate);
            const delta = clock.getDelta();
            if (mixer && !reduceMotion) mixer.update(delta);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        const onResize = () => {
            if (!mount) return;
            const w = mount.clientWidth;
            const h = mount.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener("resize", onResize);

        return () => {
            disposed = true;
            cancelAnimationFrame(raf);
            window.removeEventListener("resize", onResize);
            controls.dispose();
            renderer.dispose();
            if (mount.contains(renderer.domElement)) {
                mount.removeChild(renderer.domElement);
            }
        };
    }, [reduceMotion]);

    // Handle Layer Visibility
    useEffect(() => {
        const model = modelRef.current;
        if (!model) return;

        LAYERS.forEach((l) => {
            const visible = !hidden.includes(l.id);
            const node = model.getObjectByName(ORGAN_NODES[l.id] || l.id);
            if (node) {
                node.visible = visible;
            } else {
                model.traverse((o) => {
                    if (o.name.toLowerCase().includes(l.id)) {
                        o.visible = visible;
                    }
                });
            }
        });
    }, [hidden, status]);

    const zoomStep = (factor: number) => {
        const camera = cameraRef.current;
        const controls = controlsRef.current;
        if (!camera || !controls) return;
        const dir = camera.position.clone().sub(controls.target);
        const nextDist = THREE.MathUtils.clamp(dir.length() * factor, 0.03, 8.0);
        camera.position.copy(controls.target).add(dir.setLength(nextDist));
        controls.update();
    };

    const PRESETS = [
        { id: "all", label: "Full" },
        { id: "heart", label: "Heart" },
        { id: "brain", label: "Brain" },
        { id: "lungs", label: "Lungs" },
        { id: "digestive", label: "Digestive" },
        { id: "skeleton", label: "Skeleton" },
    ];

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, width: "100%" }}>
            {/* ONE unified toolbar: Camera presets, Layers dropdown, Zoom -/+ */}
            <div
                style={{
                    display: "flex",
                    flexWrap: "wrap",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: 10,
                    padding: "8px 12px",
                    background: "var(--surface-2, rgba(255,255,255,0.04))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    borderRadius: "2px",
                }}
            >
                {/* Camera preset segmented control */}
                <div style={{ display: "flex", gap: 4, alignItems: "center" }} role="group" aria-label="Camera preset">
                    <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.14em", marginRight: 4 }}>
                        View:
                    </span>
                    {PRESETS.map((p) => {
                        const isActive = activeFocus === p.id;
                        return (
                            <button
                                key={p.id}
                                type="button"
                                onClick={() => {
                                    focusOnNode(p.id);
                                    if (p.id !== "all") onSelectOrgan?.(p.id);
                                }}
                                style={{
                                    padding: "3px 8px",
                                    borderRadius: "2px",
                                    border: isActive ? "1px solid var(--accent, #FF4D5A)" : "1px solid var(--line, rgba(233,228,223,0.16))",
                                    background: isActive ? "var(--accent, #FF4D5A)" : "transparent",
                                    color: isActive ? "var(--accent-ink, #030307)" : "var(--text, #ECE8E3)",
                                    fontSize: "11px",
                                    fontFamily: "var(--font-mono, monospace)",
                                    fontWeight: 600,
                                    letterSpacing: "0.12em",
                                    textTransform: "uppercase",
                                    cursor: "pointer",
                                }}
                            >
                                {p.label}
                            </button>
                        );
                    })}
                </div>

                {/* Right toolbar controls: Layers dropdown and Zoom */}
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ fontSize: "11px", color: "var(--muted, rgba(236,232,227,0.55))", fontFamily: "var(--font-mono, monospace)", textTransform: "uppercase", letterSpacing: "0.14em" }}>
                            Layers:
                        </span>
                        <select
                            onChange={(e) => {
                                const val = e.target.value;
                                if (val === "all") setHidden([]);
                                else if (val === "organs") setHidden(["skeleton"]);
                                else if (val === "skeleton") setHidden(["brain", "eyes", "heart", "lungs", "digestive", "urinary", "vessels"]);
                                else setHidden((h) => h.includes(val) ? h.filter((x) => x !== val) : [...h, val]);
                            }}
                            style={{
                                background: "var(--bg, #030307)",
                                color: "var(--text, #ECE8E3)",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                borderRadius: "2px",
                                padding: "4px 8px",
                                fontSize: "11px",
                                fontFamily: "var(--font-mono, monospace)",
                                textTransform: "uppercase",
                                letterSpacing: "0.08em",
                                cursor: "pointer",
                            }}
                        >
                            <option value="all">All Layers</option>
                            <option value="organs">Organs Only</option>
                            <option value="skeleton">Skeleton Only</option>
                            {LAYERS.map((l) => (
                                <option key={l.id} value={l.id}>
                                    {hidden.includes(l.id) ? `[Hidden] ${l.label}` : `[Visible] ${l.label}`}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div style={{ display: "flex", gap: 4 }}>
                        <button
                            type="button"
                            onClick={() => zoomStep(0.7)}
                            style={{
                                padding: "4px 8px",
                                borderRadius: "2px",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                background: "transparent",
                                color: "var(--text, #ECE8E3)",
                                fontSize: "11px",
                                fontFamily: "var(--font-mono, monospace)",
                                cursor: "pointer",
                            }}
                            title="Zoom In"
                            aria-label="Zoom in"
                        >
                            +
                        </button>
                        <button
                            type="button"
                            onClick={() => zoomStep(1.35)}
                            style={{
                                padding: "4px 8px",
                                borderRadius: "2px",
                                border: "1px solid var(--line, rgba(233,228,223,0.16))",
                                background: "transparent",
                                color: "var(--text, #ECE8E3)",
                                fontSize: "11px",
                                fontFamily: "var(--font-mono, monospace)",
                                cursor: "pointer",
                            }}
                            title="Zoom Out"
                            aria-label="Zoom out"
                        >
                            −
                        </button>
                    </div>
                </div>
            </div>

            {/* 3D WebGL Canvas with wireframe corner ticks */}
            <div
                className={className}
                style={{
                    position: "relative",
                    width: "100%",
                    height,
                    minHeight: "460px",
                    borderRadius: "2px",
                    overflow: "hidden",
                    background: "var(--surface, rgba(6,8,14,0.86))",
                    border: "1px solid var(--line, rgba(233,228,223,0.16))",
                    cursor: "grab",
                }}
            >
                {/* 4 L-shaped corner ticks, 8px, in var(--line) */}
                <div style={{ position: "absolute", top: 0, left: 0, width: 8, height: 8, borderTop: "1px solid var(--line, rgba(233,228,223,0.16))", borderLeft: "1px solid var(--line, rgba(233,228,223,0.16))", pointerEvents: "none", zIndex: 10 }} />
                <div style={{ position: "absolute", top: 0, right: 0, width: 8, height: 8, borderTop: "1px solid var(--line, rgba(233,228,223,0.16))", borderRight: "1px solid var(--line, rgba(233,228,223,0.16))", pointerEvents: "none", zIndex: 10 }} />
                <div style={{ position: "absolute", bottom: 0, left: 0, width: 8, height: 8, borderBottom: "1px solid var(--line, rgba(233,228,223,0.16))", borderLeft: "1px solid var(--line, rgba(233,228,223,0.16))", pointerEvents: "none", zIndex: 10 }} />
                <div style={{ position: "absolute", bottom: 0, right: 0, width: 8, height: 8, borderBottom: "1px solid var(--line, rgba(233,228,223,0.16))", borderRight: "1px solid var(--line, rgba(233,228,223,0.16))", pointerEvents: "none", zIndex: 10 }} />

                <div ref={mountRef} style={{ position: "absolute", inset: 0 }} />

                {status !== "ready" && (
                    <div
                        style={{
                            position: "absolute",
                            inset: 0,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "var(--surface, rgba(6,8,14,0.86))",
                            fontSize: "12px",
                            fontFamily: "var(--font-mono, monospace)",
                            color: "var(--accent, #FF4D5A)",
                            gap: "12px",
                            zIndex: 20,
                        }}
                    >
                        {status === "error" ? (
                            <span style={{ color: "var(--accent, #FF4D5A)" }}>3D model could not be loaded.</span>
                        ) : (
                            <>
                                <div style={{ width: "24px", height: "24px", borderRadius: "2px", border: "1px solid var(--line, rgba(233,228,223,0.16))", borderTopColor: "var(--accent, #FF4D5A)", animation: "spin 1s linear infinite" }} />
                                <span style={{ textTransform: "uppercase", letterSpacing: "0.14em" }}>
                                    Loading Anatomy {progress ? `${progress}%` : "..."}
                                </span>
                            </>
                        )}
                    </div>
                )}

                {/* Subtle helper text */}
                <div
                    style={{
                        position: "absolute",
                        bottom: "8px",
                        left: "12px",
                        right: "12px",
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: "11px",
                        fontFamily: "var(--font-mono, monospace)",
                        color: "var(--muted, rgba(236,232,227,0.55))",
                        pointerEvents: "none",
                        zIndex: 10,
                    }}
                >
                    <span>Left-drag: Orbit · Right-drag: Pan · Scroll: Zoom</span>
                    <span>Anatomical Telemetry</span>
                </div>
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}
