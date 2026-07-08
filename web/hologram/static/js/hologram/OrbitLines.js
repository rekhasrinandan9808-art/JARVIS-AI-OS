import * as THREE from "three";
export function createOrbitLines(scene) {
    const g = new THREE.Group();
    const mat = new THREE.LineBasicMaterial({ color: 0x00D4FF });
    for (let i = 0; i < 4; i++) {
        const curve = new THREE.EllipseCurve(0, 0, 2.5 + i * 0.3, 2 + i * 0.25, 0, 2 * Math.PI);
        const pts = curve.getPoints(250);
        const geo = new THREE.BufferGeometry().setFromPoints(pts.map(p => new THREE.Vector3(p.x, p.y, 0)));
        const line = new THREE.LineLoop(geo, mat);
        line.rotation.x = Math.random() * Math.PI;
        line.rotation.y = Math.random() * Math.PI;
        g.add(line);
    }
    scene.add(g);
    return g;
}
