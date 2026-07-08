import * as THREE from "three";
export function createRadar(scene) {
    const g = new THREE.Group();
    const mat = new THREE.MeshBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.45, side: THREE.DoubleSide });
    for (let i = 0; i < 3; i++) {
        const geo = new THREE.RingGeometry(1 + i * 0.6, 1.08 + i * 0.6, 128);
        const mesh = new THREE.Mesh(geo, mat);
        mesh.rotation.x = -Math.PI / 2;
        g.add(mesh);
    }
    g.position.y = -2.3;
    scene.add(g);
    return g;
}
