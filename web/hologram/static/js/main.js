import "./hologram/Rings.js";
import "./hologram/Particles.js";
import "./hologram/HexGrid.js";
import "./hologram/Radar.js";
import "./hologram/OrbitLines.js";

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

const container = document.getElementById("canvas-container");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000814);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
camera.position.z = 8;

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.9;
renderer.outputColorSpace = THREE.SRGBColorSpace;
container.appendChild(renderer.domElement);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.5, 0.3, 0.2);
composer.addPass(bloom);

// Core
const coreGeo = new THREE.SphereGeometry(3.0, 32, 32);
const coreMat = new THREE.MeshBasicMaterial({ color: 0x00D4FF, wireframe: true, transparent: true, opacity: 0.6 });
const core = new THREE.Mesh(coreGeo, coreMat);
core.position.set(0, 1.0, -4.0);
scene.add(core);

// Inner Core
const innerGeo = new THREE.IcosahedronGeometry(1.1, 3);
const innerMat = new THREE.MeshBasicMaterial({ color: 0x44DDFF, transparent: true, opacity: 0.8, side: THREE.DoubleSide });
const innerCore = new THREE.Mesh(innerGeo, innerMat);
innerCore.position.set(0, 1.0, -4.0);
scene.add(innerCore);

// Inner Glow
const glowGeo = new THREE.SphereGeometry(0.85, 32, 32);
const glowMat = new THREE.MeshBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.18, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
const innerGlow = new THREE.Mesh(glowGeo, glowMat);
innerGlow.position.set(0, 1.0, -4.0);
scene.add(innerGlow);

// Outer Ring
const ringGeo = new THREE.TorusGeometry(3.5, 0.05, 32, 64);
const ringMat = new THREE.MeshBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
const outerRing = new THREE.Mesh(ringGeo, ringMat);
outerRing.position.set(0, 1.0, -4.0);
scene.add(outerRing);

// Grid
const gridMat = new THREE.LineBasicMaterial({ color: 0x00D4FF, transparent: true, opacity: 0.15 });
const gridGroup = new THREE.Group();
const size = 8, divisions = 12, step = size / divisions;
for (let i = 0; i <= divisions; i++) {
    const x = -size/2 + i * step;
    const p1 = [new THREE.Vector3(x, -size/2, 0), new THREE.Vector3(x, size/2, 0)];
    const g1 = new THREE.BufferGeometry().setFromPoints(p1);
    gridGroup.add(new THREE.Line(g1, gridMat));
    const y = -size/2 + i * step;
    const p2 = [new THREE.Vector3(-size/2, y, 0), new THREE.Vector3(size/2, y, 0)];
    const g2 = new THREE.BufferGeometry().setFromPoints(p2);
    gridGroup.add(new THREE.Line(g2, gridMat));
}
gridGroup.position.set(0, -2.5, -4.0);
scene.add(gridGroup);

const light = new THREE.PointLight(0x00D4FF, 15);
light.position.set(4, 4, 4);
scene.add(light);

// Audio
let audioCtx, analyser, dataArr, isAudio = false;
async function initAudio() {
    try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const src = audioCtx.createMediaStreamSource(stream);
        src.connect(analyser);
        dataArr = new Uint8Array(analyser.frequencyBinCount);
        isAudio = true;
    } catch(e) { console.log('Audio unavailable'); }
}
document.addEventListener('click', initAudio);
setTimeout(initAudio, 1000);

let pulse = 0, target = 0;
function animate() {
    requestAnimationFrame(animate);
    
    if (isAudio && analyser) {
        analyser.getByteFrequencyData(dataArr);
        let sum = 0;
        for (let i = 0; i < dataArr.length/4; i++) sum += dataArr[i];
        target = (sum / (dataArr.length/4 * 255)) * 0.8 + 0.2;
    } else {
        target = Math.sin(Date.now() / 1500) * 0.35 + 0.65;
    }
    pulse += (target - pulse) * 0.08;
    
    const sz = 3.0 + (pulse - 0.5) * 1.0;
    if (core.geometry) {
        const ng = new THREE.SphereGeometry(sz, 32, 32);
        core.geometry.dispose();
        core.geometry = ng;
    }
    
    core.rotation.x += 0.0015;
    core.rotation.y += 0.0025;
    innerCore.rotation.x += 0.002;
    innerCore.rotation.y += 0.003;
    innerGlow.rotation.copy(innerCore.rotation);
    
    composer.render();
}
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight);
});

// Stats update
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const d = await res.json();
        document.getElementById('cpu').textContent = Math.round(d.cpu) + '%';
        document.getElementById('memory').textContent = Math.round(d.memory) + '%';
        document.getElementById('network').textContent = Math.round(d.network) + '%';
        document.getElementById('energy').textContent = Math.round(d.energy) + '%';
        document.querySelectorAll('.progress-fill')[0].style.width = Math.round(d.cpu) + '%';
        document.querySelectorAll('.progress-fill')[1].style.width = Math.round(d.memory) + '%';
        document.querySelectorAll('.progress-fill')[2].style.width = Math.round(d.network) + '%';
        document.querySelectorAll('.progress-fill')[3].style.width = Math.round(d.energy) + '%';
    } catch(e) {}
}
setInterval(fetchStats, 2000);
fetchStats();
