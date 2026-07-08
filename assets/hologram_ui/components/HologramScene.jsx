import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { HologramEngine } from "../core/HologramEngine";

export default function HologramScene() {
    const containerRef = useRef(null);

    useEffect(() => {
        const engine = new HologramEngine(containerRef.current);

        const scene = engine.sceneManager.scene;

        // ===========================
        // Hologram Sphere
        // ===========================

        const geometry = new THREE.SphereGeometry(1.4, 64, 64);

        const material = new THREE.MeshBasicMaterial({
            color: 0xffb000,
            wireframe: true,
            transparent: true,
            opacity: 0.9
        });

        const sphere = new THREE.Mesh(geometry, material);

        scene.add(sphere);

        // ===========================
        // Animation
        // ===========================

        engine.loop.add((delta) => {

            sphere.rotation.y += delta * 0.35;
            sphere.rotation.x += delta * 0.08;

            sphere.position.y =
                Math.sin(performance.now() * 0.0015) * 0.18;

        });

        engine.start();

        return () => {
            containerRef.current.innerHTML = "";
        };

    }, []);

    return (
        <div
            ref={containerRef}
            style={{
                width: "100%",
                height: "100%",
                position: "absolute",
                inset: 0
            }}
        />
    );
}