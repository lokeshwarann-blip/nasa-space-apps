
"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/examples/jsm/loaders/DRACOLoader.js";

export default function Spacecraft() {
    const mountRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const mount = mountRef.current;
        if (!mount) return;

        const scene = new THREE.Scene();

        const camera = new THREE.PerspectiveCamera(
            45,
            mount.clientWidth / mount.clientHeight,
            0.1,
            1000
        );
        camera.position.set(0, 0, 12);

        const renderer = new THREE.WebGLRenderer({
            alpha: true,
            antialias: true,
        });

        renderer.setSize(mount.clientWidth, mount.clientHeight);
        renderer.setPixelRatio(1);
        mount.appendChild(renderer.domElement);

        scene.add(new THREE.AmbientLight(0xffffff, 2));

        const light = new THREE.DirectionalLight(0xffffff, 3);
        light.position.set(5, 5, 5);
        scene.add(light);

        let spacecraft: THREE.Object3D | null = null;
        const draco = new DRACOLoader();
        draco.setDecoderPath("https://www.gstatic.com/draco/versioned/decoders/1.5.7/");

        const loader = new GLTFLoader();
        loader.setDRACOLoader(draco);

        loader.load(
            "/models/spacecraft-opt.glb",
            (gltf) => {
                spacecraft = gltf.scene;

                spacecraft.scale.setScalar(0.05);

                const box = new THREE.Box3().setFromObject(spacecraft);
                const center = box.getCenter(new THREE.Vector3());

                const sphere = box.getBoundingSphere(new THREE.Sphere());
                modelRadius = sphere.radius;

                spacecraft.position.sub(center);

                scene.add(spacecraft);
            }
        );
        let mouseX = 0;
        let mouseY = 0;

        let targetX = 0;
        let targetY = 0;
        let modelRadius = 0;

        const onMouseMove = (event: MouseEvent) => {
            const width = window.innerWidth;
            const height = window.innerHeight;

            // Find where the login card begins
            const card = document.getElementById("login-card");

            const cardLeft =
                card?.getBoundingClientRect().left ?? width * 0.55;

            // Calculate the visible world dimensions
            const halfHeight =
                camera.position.z *
                Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));

            const halfWidth = halfHeight * camera.aspect;

            // Convert model size into screen pixels
            const pixelsPerUnit = width / (2 * halfWidth);
            const margin = modelRadius * pixelsPerUnit + 25;

            // Restrict spacecraft to the available left-side area
            const minX = margin;
            const maxX = cardLeft - margin;

            const safeX = THREE.MathUtils.clamp(
                event.clientX,
                minX,
                maxX
            );

            const safeY = THREE.MathUtils.clamp(
                event.clientY,
                margin,
                height - margin
            );

            // Convert screen coordinates into Three.js coordinates
            mouseX = (safeX / width) * 2 - 1;
            mouseY = (safeY / height) * 2 - 1;

            targetX = mouseX * halfWidth;
            targetY = -mouseY * halfHeight;
        };
        window.addEventListener("mousemove", onMouseMove);

        let animationId = 0;

        const animate = () => {
            animationId = requestAnimationFrame(animate);

            if (spacecraft) {
                // Mouse-controlled rotation
                spacecraft.rotation.y +=
                    (mouseX * 0.6 - spacecraft.rotation.y) * 0.04;

                spacecraft.rotation.x +=
                    (-mouseY * 0.3 - spacecraft.rotation.x) * 0.04;

                // Mouse-controlled movement
                spacecraft.position.x +=
                    (targetX - spacecraft.position.x) * 0.04;

                spacecraft.position.y +=
                    (targetY - spacecraft.position.y) * 0.04;
            }

            renderer.render(scene, camera);
        };

        animate();

        const onResize = () => {
            camera.aspect = mount.clientWidth / mount.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(mount.clientWidth, mount.clientHeight);
        };

        window.addEventListener("resize", onResize);

        return () => {
            cancelAnimationFrame(animationId);
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("resize", onResize);
            renderer.dispose();
            renderer.domElement.remove();
        };
    }, []);

    return (
        <div
            ref={mountRef}
            style={{
                width: "100%",
                height: "100%",
            }}
        />
    );
}
