import * as THREE from "three";
export function createHexGrid(scene) {
    const g = new THREE.Group();
    const mat = new THREE.LineBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.22 });
    const radius = 40, spacing = 1.25;
    function hex(x, z) {
        const pts = [];
        for (let i = 0; i <= 6; i++) {
            const a = (Math.PI / 3) * i;
            pts.push(new THREE.Vector3(Math.cos(a) * 0.55 + x, 0, Math.sin(a) * 0.55 + z));
        }
        return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat);
    }
    for (let x = -radius; x < radius; x++) {
        for (let z = -radius; z < radius; z++) {
            const offset = (x % 2) * 0.6;
            g.add(hex(x * spacing, z * spacing + offset));
        }
    }
    g.position.y = -2.8;
    scene.add(g);
    return g;
}
