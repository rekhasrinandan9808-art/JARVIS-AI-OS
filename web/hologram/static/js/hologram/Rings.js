import * as THREE from "three";
export function createRings(scene) {
    const g = new THREE.Group();
    for (let i = 0; i < 5; i++) {
        const r = 1.5 + i * 0.5;
        const geo = new THREE.TorusGeometry(r, 0.02, 16, 64);
        const mat = new THREE.MeshBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.rotation.x = Math.PI / 2;
        mesh.rotation.z = i * 0.3;
        g.add(mesh);
    }
    scene.add(g);
    return g;
}
