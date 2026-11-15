"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

interface AstronautViewerProps {
    heartRate?: number;
    oxygenSat?: number;
    coreTemp?: number;
}

export default function AstronautViewer({}: AstronautViewerProps) {
    const mountRef = useRef<HTMLDivElement>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const controlsRef = useRef<OrbitControls | null>(null);
    const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
    const initialCameraPos = useRef<THREE.Vector3>(new THREE.Vector3(0, 0.28, 2.3)); // Frames upper body, chest & skull like screenshot

    const handleResetView = () => {
        if (cameraRef.current && controlsRef.current) {
            cameraRef.current.position.copy(initialCameraPos.current);
            controlsRef.current.target.set(0, 0.22, 0);
            controlsRef.current.update();
        }
    };

    useEffect(() => {
        const mount = mountRef.current;
        if (!mount) return;

        let animationFrameId: number;
        let isDisposed = false;
        setError(null);
        setLoading(true);

        const width = mount.clientWidth || 400;
        const height = mount.clientHeight || 560;

        // Three.js Scene Setup
        const scene = new THREE.Scene();

        // Perspective Camera setup: Framed like the user's reference photo
        const camera = new THREE.PerspectiveCamera(36, width / height, 0.1, 100);
        camera.position.copy(initialCameraPos.current);
        cameraRef.current = camera;

        // WebGL Renderer with High-Fidelity Color & PBR Tone Mapping
        const renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true,
            powerPreference: "high-performance",
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.45;
        mount.appendChild(renderer.domElement);

        // Orbit Controls
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.autoRotate = false;
        controls.minDistance = 0.8;
        controls.maxDistance = 6.0;
        controls.maxPolarAngle = Math.PI / 1.7;
        controls.minPolarAngle = Math.PI / 8;
        controls.target.set(0, 0.22, 0);
        controlsRef.current = controls;

        // Balanced Studio Lighting (Matching Sketchfab's exact lighting setup)
        const ambientLight = new THREE.AmbientLight(0xffffff, 1.8);
        scene.add(ambientLight);

        // Key light (Front-top sun)
        const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
        keyLight.position.set(3, 5, 4);
        scene.add(keyLight);

        // Fill light (Soft blue-white fill from side)
        const fillLight = new THREE.DirectionalLight(0xe2f1f8, 2.2);
        fillLight.position.set(-4, 2, 3);
        scene.add(fillLight);

        // Rim backlight (Highlights skull curve, ribs, and veins)
        const rimLight = new THREE.DirectionalLight(0xffffff, 2.8);
        rimLight.position.set(0, 4, -4);
        scene.add(rimLight);

        // Bottom bounce light (Illuminates lower organs and pelvis)
        const bounceLight = new THREE.DirectionalLight(0x2a3d45, 1.2);
        bounceLight.position.set(0, -3, 2);
        scene.add(bounceLight);

        // Ground Platform Grid (Ethereal cyan platform beneath boots)
        const gridHelper = new THREE.GridHelper(3.2, 16, 0x00e5ff, 0x143440);
        gridHelper.position.y = -1.05;
        (gridHelper.material as THREE.Material).transparent = true;
        (gridHelper.material as THREE.Material).opacity = 0.22;
        scene.add(gridHelper);

        // Root Group
        const rootGroup = new THREE.Group();
        scene.add(rootGroup);

        // Load the EXACT Textured GLTF Model
        const loader = new GLTFLoader();
        loader.load(
            "/models/human_body/6a7a537a71444f6e8201e18a685a013d_Textured.gltf",
            (gltf) => {
                if (isDisposed) return;
                const model = gltf.scene;

                // Height of human body in centimeters is 170.0
                // Scale to 2.05 scene units
                const targetHeight = 2.05;
                const scale = targetHeight / 170.0;
                model.scale.setScalar(scale);

                // Center vertically so origin (0,0,0) is at torso/waist
                model.position.set(0, -targetHeight / 2, 0);

                // Preserve ALL 51 original PBR textures, normal maps, roughness maps
                model.traverse((child) => {
                    if ((child as THREE.Mesh).isMesh) {
                        const mesh = child as THREE.Mesh;
                        if (mesh.material) {
                            const matList = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                            matList.forEach((m) => {
                                m.side = THREE.DoubleSide; // Ensure ribcage interior & skull cavity render correctly
                                m.needsUpdate = true;
                                if ((m as THREE.MeshStandardMaterial).isMeshStandardMaterial) {
                                    const stdMat = m as THREE.MeshStandardMaterial;
                                    stdMat.roughness = Math.max(0.2, stdMat.roughness || 0.4);
                                    stdMat.metalness = Math.min(0.3, stdMat.metalness || 0.1);
                                }
                            });
                        }
                    }
                });

                rootGroup.add(model);
                setError(null);
                setLoading(false);
            },
            undefined,
            (err) => {
                console.error("Error loading exact human body model:", err);
                if (!isDisposed) {
                    setError(`Failed to load exact 3D model: ${err instanceof Error ? err.message : String(err)}`);
                    setLoading(false);
                }
            }
        );

        // Window Resize
        const handleResize = () => {
            if (!mount) return;
            const w = mount.clientWidth || 400;
            const h = mount.clientHeight || 560;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
        };
        window.addEventListener("resize", handleResize);

        // Animation Loop
        const animate = () => {
            animationFrameId = requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        return () => {
            isDisposed = true;
            window.removeEventListener("resize", handleResize);
            cancelAnimationFrame(animationFrameId);
            controls.dispose();
            renderer.dispose();
            if (mount.contains(renderer.domElement)) {
                mount.removeChild(renderer.domElement);
            }
        };
    }, []);

    return (
        <div style={{
            position: "relative",
            width: "100%",
            height: "100%",
            minHeight: "580px",
            display: "flex",
            flexDirection: "column",
            borderRadius: "24px",
            overflow: "hidden",
            background: "radial-gradient(ellipse at 50% 25%, #182228 0%, #0d161a 55%, #050a0d 100%)",
            border: "1px solid rgba(0, 229, 255, 0.3)",
            boxShadow: "inset 0 0 50px rgba(0, 229, 255, 0.06), 0 16px 40px rgba(0, 0, 0, 0.6)",
            userSelect: "none",
        }}>
            {/* 3D WebGL Canvas - Clean & Completely Unobstructed */}
            <div
                ref={mountRef}
                onDoubleClick={handleResetView}
                title="Double-click to reset view · Drag to orbit 360° · Scroll to zoom"
                style={{
                    width: "100%",
                    height: "100%",
                    minHeight: "580px",
                    cursor: "grab",
                }}
            />

            {/* Subtle Bottom Helper (Pointer-events none so it never blocks clicks) */}
            <div style={{
                position: "absolute",
                bottom: "12px",
                left: "14px",
                right: "14px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                pointerEvents: "none",
                zIndex: 10,
            }}>
                <span style={{
                    fontFamily: "var(--font-mono, monospace)",
                    fontSize: "10px",
                    color: "rgba(164, 194, 203, 0.55)",
                    letterSpacing: "0.04em",
                }}>
                    Drag to orbit in 360° · Scroll to zoom · Double-click to reset view
                </span>
            </div>

            {/* Loading Overlay */}
            {loading && (
                <div style={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "rgba(10, 21, 26, 0.95)",
                    backdropFilter: "blur(14px)",
                    zIndex: 25,
                    gap: "12px",
                }}>
                    <div style={{
                        width: "38px",
                        height: "38px",
                        borderRadius: "50%",
                        border: "3px solid rgba(0, 229, 255, 0.2)",
                        borderTopColor: "#00e5ff",
                        animation: "spin 1s linear infinite",
                    }} />
                    <span style={{
                        fontFamily: "var(--font-mono, monospace)",
                        fontSize: "11px",
                        letterSpacing: "0.1em",
                        color: "#00e5ff",
                        textTransform: "uppercase",
                    }}>
                        Loading Exact PBR Anatomical Systems (51 Textures)...
                    </span>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div style={{
                    position: "absolute",
                    inset: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "rgba(10, 21, 26, 0.88)",
                    color: "#ff8b80",
                    fontSize: "12px",
                    fontFamily: "var(--font-mono, monospace)",
                    zIndex: 25,
                    padding: "20px",
                    textAlign: "center",
                }}>
                    {error}
                </div>
            )}

            <style>{`
                @keyframes spin { to { transform: rotate(360deg); } }
            `}</style>
        </div>
    );
}
