import * as THREE from "three";

export function createAgentNodes(scene, agentNames) {
    const group = new THREE.Group();
    const numAgents = agentNames.length;
    
    // Orange color variations
    const colors = [
        0xff6600, 0xff7700, 0xff8800, 0xff9900, 0xffaa00,
        0xffbb00, 0xffcc00, 0xff8800, 0xff7700, 0xff9900
    ];
    
    for (let i = 0; i < numAgents; i++) {
        const phi = Math.acos(1 - 2 * (i + 0.5) / numAgents);
        const theta = Math.PI * (1 + Math.sqrt(5)) * i;
        
        const radius = 3.0 + Math.random() * 1.5;
        const x = radius * Math.sin(phi) * Math.cos(theta);
        const y = radius * Math.sin(phi) * Math.sin(theta);
        const z = radius * Math.cos(phi);
        
        const dotGeometry = new THREE.SphereGeometry(0.06, 8, 8);
        const dotMaterial = new THREE.MeshBasicMaterial({
            color: colors[i % colors.length],
            transparent: true,
            opacity: 0.9
        });
        const dot = new THREE.Mesh(dotGeometry, dotMaterial);
        dot.position.set(x, y, z);
        dot.userData = { 
            name: agentNames[i],
            index: i,
            targetX: x,
            targetY: y,
            targetZ: z,
            phase: Math.random() * Math.PI * 2
        };
        group.add(dot);
        
        const auraGeometry = new THREE.SphereGeometry(0.12, 8, 8);
        const auraMaterial = new THREE.MeshBasicMaterial({
            color: colors[i % colors.length],
            transparent: true,
            opacity: 0.2,
            blending: THREE.AdditiveBlending
        });
        const aura = new THREE.Mesh(auraGeometry, auraMaterial);
        aura.position.set(x, y, z);
        aura.userData = { parent: dot };
        group.add(aura);
        
        const curvePoints = [];
        const start = new THREE.Vector3(0, 0, 0);
        const end = new THREE.Vector3(x, y, z);
        const mid = new THREE.Vector3(
            x * 0.5 + (Math.random() - 0.5) * 0.8,
            y * 0.5 + (Math.random() - 0.5) * 0.8,
            z * 0.5 + (Math.random() - 0.5) * 0.8
        );
        
        for (let t = 0; t <= 1; t += 0.02) {
            const point = new THREE.Vector3();
            const u = 1 - t;
            point.x = u * u * start.x + 2 * u * t * mid.x + t * t * end.x;
            point.y = u * u * start.y + 2 * u * t * mid.y + t * t * end.y;
            point.z = u * u * start.z + 2 * u * t * mid.z + t * t * end.z;
            curvePoints.push(point);
        }
        
        const curveGeometry = new THREE.BufferGeometry().setFromPoints(curvePoints);
        const curveMaterial = new THREE.LineBasicMaterial({
            color: colors[i % colors.length],
            transparent: true,
            opacity: 0.15,
            blending: THREE.AdditiveBlending
        });
        const curve = new THREE.Line(curveGeometry, curveMaterial);
        curve.userData = { parent: dot };
        group.add(curve);
        
        const ringGeo = new THREE.RingGeometry(0.08, 0.1, 16);
        const ringMat = new THREE.MeshBasicMaterial({
            color: colors[i % colors.length],
            transparent: true,
            opacity: 0.3,
            side: THREE.DoubleSide,
            blending: THREE.AdditiveBlending
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.position.set(x, y, z);
        ring.lookAt(0, 0, 0);
        ring.userData = { parent: dot };
        group.add(ring);
    }
    
    scene.add(group);
    return group;
}