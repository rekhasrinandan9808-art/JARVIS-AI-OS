import * as THREE from "three";

export function createRadar(scene) {
    const group = new THREE.Group();

    const material = new THREE.MeshBasicMaterial({
        color: 0x00ccff,
        transparent: true,
        opacity: 0.45,
        side: THREE.DoubleSide
    });

    // No rings - just an empty group
    // Add a single subtle ring if you want, or leave empty

    group.position.y = -2.3;
    scene.add(group);
    return group;
}