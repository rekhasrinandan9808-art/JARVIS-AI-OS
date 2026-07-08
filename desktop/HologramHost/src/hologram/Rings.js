import * as THREE from "three";

export function createRings(scene) {
    const group = new THREE.Group();
    const ringCount = 5;
    
    // Ring sizes: 1st small, 5th large - fitting within view
    const ringSizes = [1.2, 1.7, 2.2, 2.7, 3.2];
    const ringColors = [0x00ccff, 0x22ddff, 0x44eeff, 0x66ffff, 0x88ffff];
    const ringOpacities = [0.8, 0.7, 0.6, 0.5, 0.4];
    
    for (let i = 0; i < ringCount; i++) {
        const radius = ringSizes[i];
        const geometry = new THREE.TorusGeometry(radius, 0.025, 32, 128);
        const material = new THREE.MeshBasicMaterial({
            color: ringColors[i],
            transparent: true,
            opacity: ringOpacities[i],
            blending: THREE.AdditiveBlending,
            side: THREE.DoubleSide
        });
        const ring = new THREE.Mesh(geometry, material);
        ring.rotation.x = Math.PI / 2.5;
        ring.rotation.y = i * 0.2;
        ring.position.z = -0.3 + i * 0.15;
        group.add(ring);
    }
    
    scene.add(group);
    return group;
}