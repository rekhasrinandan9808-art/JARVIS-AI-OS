import * as THREE from "three";

export function createOrbitLines(scene) {
    const group = new THREE.Group();

    const material = new THREE.LineBasicMaterial({
        color: 0x00ffff
    });

    // No orbit lines - just an empty group

    scene.add(group);
    return group;
}