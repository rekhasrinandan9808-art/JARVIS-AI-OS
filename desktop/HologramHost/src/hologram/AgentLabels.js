import * as THREE from "three";
import { TextGeometry } from "three/examples/jsm/geometries/TextGeometry.js";
import { FontLoader } from "three/examples/jsm/loaders/FontLoader.js";

export function createAgentLabels(scene, agentNames, positions) {
    const group = new THREE.Group();
    
    // This is a placeholder - you'd need to load a font
    // For simplicity, we'll use sprites with canvas textures
    
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;
    
    positions.forEach((pos, i) => {
        context.clearRect(0, 0, canvas.width, canvas.height);
        context.fillStyle = 'rgba(0, 136, 204, 0.8)';
        context.font = '24px monospace';
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(agentNames[i], canvas.width/2, canvas.height/2);
        
        const texture = new THREE.CanvasTexture(canvas);
        const material = new THREE.SpriteMaterial({
            map: texture,
            transparent: true,
            opacity: 0.4,
            blending: THREE.AdditiveBlending
        });
        const sprite = new THREE.Sprite(material);
        sprite.position.set(pos.x * 1.2, pos.y * 1.2, pos.z * 1.2);
        sprite.scale.set(0.8, 0.2, 1);
        group.add(sprite);
    });
    
    scene.add(group);
    return group;
}