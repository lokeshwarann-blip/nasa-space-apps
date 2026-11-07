
"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

interface CelestialSphereProps {
    hue?: number;
    speed?: number;
    zoom?: number;
    particleSize?: number;
    className?: string;
}

export default function CelestialSphere({
    hue = 220,
    speed = 0.3,
    zoom = 1.5,
    particleSize = 3,
    className = "",
}: CelestialSphereProps) {
    const mountRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const mount = mountRef.current;
        if (!mount) return;

        let animationFrameId = 0;
        let renderer: THREE.WebGLRenderer | null = null;
        let resizeObserver: ResizeObserver | null = null;
        let geometry: THREE.PlaneGeometry | null = null;
        let material: THREE.ShaderMaterial | null = null;

        try {
            const scene = new THREE.Scene();
            const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

            renderer = new THREE.WebGLRenderer({
                antialias: true,
                alpha: false,
            });

            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1));
            mount.appendChild(renderer.domElement);

            const vertexShader = `
                varying vec2 vUv;

                void main() {
                    vUv = uv;
                    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
            `;

            const fragmentShader = `
                precision highp float;

                varying vec2 vUv;

                uniform vec2 u_resolution;
                uniform float u_time;
                uniform float u_hue;
                uniform float u_zoom;
                uniform float u_particle_size;

                vec3 hsl2rgb(vec3 c) {
                    vec3 rgb = clamp(
                        abs(mod(c.x * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0,
                        0.0,
                        1.0
                    );
                    return c.z * mix(vec3(1.0), rgb, c.y);
                }

                float random(vec2 st) {
                    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453);
                }

                float noise(vec2 st) {
                    vec2 i = floor(st);
                    vec2 f = fract(st);

                    float a = random(i);
                    float b = random(i + vec2(1.0, 0.0));
                    float c = random(i + vec2(0.0, 1.0));
                    float d = random(i + vec2(1.0, 1.0));

                    vec2 u = f * f * (3.0 - 2.0 * f);

                    return mix(a, b, u.x) +
                        (c - a) * u.y * (1.0 - u.x) +
                        (d - b) * u.y * u.x;
                }

                float fbm(vec2 st) {
                    float value = 0.0;
                    float amplitude = 0.5;

                    for (int i = 0; i < 6; i++) {
                        value += amplitude * noise(st);
                        st *= 2.0;
                        amplitude *= 0.5;
                    }

                    return value;
                }

                void main() {
                    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution.xy) /
                              min(u_resolution.y, u_resolution.x);

                    uv *= u_zoom;
                

                    float f = fbm(uv + vec2(u_time * 0.1, u_time * 0.05));
                    float t = fbm(uv + f + vec2(u_time * 0.05, u_time * 0.02));

                    float nebula = pow(t, 2.0);

                    vec3 color = hsl2rgb(
                        vec3(u_hue / 360.0 + nebula * 0.2, 0.7, 0.5)
                    );

                    color *= nebula * 2.5;

                    float star = random(vUv * 500.0);

                    if (star > 0.998) {
                        color += vec3((star - 0.998) / 0.002 * u_particle_size);
                    }

                    gl_FragColor = vec4(color, 1.0);
                }
            `;

            material = new THREE.ShaderMaterial({
                vertexShader,
                fragmentShader,
                uniforms: {
                    u_time: { value: 0 },
                    u_resolution: { value: new THREE.Vector2() },
                    u_hue: { value: hue },
                    u_zoom: { value: zoom },
                    u_particle_size: { value: particleSize },
                },
            });

            geometry = new THREE.PlaneGeometry(2, 2);

            const mesh = new THREE.Mesh(geometry, material);
            scene.add(mesh);

            const resize = () => {
                if (!renderer || !material) return;

                const width = mount.clientWidth;
                const height = mount.clientHeight;

                if (!width || !height) return;

                renderer.setSize(width, height);
                material.uniforms.u_resolution.value.set(width, height);
            };



            const animate = () => {
                if (!renderer || !material) return;

                material.uniforms.u_time.value += 0.005 * speed;
                renderer.render(scene, camera);

                animationFrameId = requestAnimationFrame(animate);
            };

            resizeObserver = new ResizeObserver(resize);
            resizeObserver.observe(mount);



            resize();
            animate();

            return () => {
                cancelAnimationFrame(animationFrameId);
                resizeObserver?.disconnect();

                geometry?.dispose();
                material?.dispose();
                renderer?.dispose();

                if (renderer?.domElement.parentElement === mount) {
                    mount.removeChild(renderer.domElement);
                }
            };
        } catch (error) {
            console.error("Celestial Sphere initialization failed:", error);

            cancelAnimationFrame(animationFrameId);
            resizeObserver?.disconnect();
            geometry?.dispose();
            material?.dispose();
            renderer?.dispose();

            if (renderer?.domElement.parentElement === mount) {
                mount.removeChild(renderer.domElement);
            }
        }
    }, [hue, speed, zoom, particleSize]);

    return (
        <div
            ref={mountRef}
            className={className}
            aria-hidden="true"
        />
    );
}

