import "./style.css";

import * as THREE from "three";
import { createHexGrid } from "./hologram/HexGrid";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";

const container = document.getElementById("canvas-container");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000814);

const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);
camera.position.z = 8;

const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true
});

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.9;
renderer.outputColorSpace = THREE.SRGBColorSpace;

container.appendChild(renderer.domElement);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

const bloom = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.5,
    0.3,
    0.2
);
composer.addPass(bloom);

// Main Core - SPHERE (outer core) - Cyan
const geometry = new THREE.SphereGeometry(3.0, 32, 32);
const material = new THREE.MeshBasicMaterial({
    color: 0x00D4FF,
    wireframe: true,
    transparent: true,
    opacity: 0.6
});
const core = new THREE.Mesh(geometry, material);
core.position.set(0, 1.0, -4.0);
scene.add(core);

// Single Outer Ring - Facing Z axis (pulsing with core, no rotation)
const ringGeometry = new THREE.TorusGeometry(3.5, 0.05, 32, 64);
const ringMaterial = new THREE.MeshBasicMaterial({
    color: 0x00D4FF,
    transparent: true,
    opacity: 0.5,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide
});
const outerRing = new THREE.Mesh(ringGeometry, ringMaterial);
outerRing.position.set(0, 1.0, -4.0);
scene.add(outerRing);

// Inner Core - SOLID - Lighter Cyan
const innerGeometry = new THREE.IcosahedronGeometry(1.1, 3);
const innerMaterial = new THREE.MeshBasicMaterial({
    color: 0x44DDFF,
    transparent: true,
    opacity: 0.8,
    side: THREE.DoubleSide
});
const innerCore = new THREE.Mesh(innerGeometry, innerMaterial);
innerCore.position.set(0, 1.0, -4.0);
scene.add(innerCore);

// Inner glow sphere - Cyan
const glowGeometry = new THREE.SphereGeometry(0.85, 32, 32);
const glowMaterial = new THREE.MeshBasicMaterial({
    color: 0x00D4FF,
    transparent: true,
    opacity: 0.18,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide
});
const innerGlow = new THREE.Mesh(glowGeometry, glowMaterial);
innerGlow.position.set(0, 1.0, -4.0);
scene.add(innerGlow);

// ===== CIRCULAR ENERGY BASE =====
function createEnergyBase(scene) {
    const group = new THREE.Group();
    group.position.set(0, -4.0, -4.0);
    
    // Main circular platform
    const platformGeo = new THREE.CylinderGeometry(3.0, 3.2, 0.15, 64);
    const platformMat = new THREE.MeshBasicMaterial({
        color: 0x00D4FF,
        transparent: true,
        opacity: 0.08,
        side: THREE.DoubleSide,
        blending: THREE.AdditiveBlending
    });
    const platform = new THREE.Mesh(platformGeo, platformMat);
    platform.position.y = 0;
    group.add(platform);
    
    // Outer glow ring
    const ringGeo = new THREE.TorusGeometry(3.0, 0.04, 16, 64);
    const ringMat = new THREE.MeshBasicMaterial({
        color: 0x44DDFF,
        transparent: true,
        opacity: 0.4,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.08;
    group.add(ring);
    
    // Inner glow ring
    const innerRingGeo = new THREE.TorusGeometry(2.5, 0.03, 16, 64);
    const innerRingMat = new THREE.MeshBasicMaterial({
        color: 0x00D4FF,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        side: THREE.DoubleSide
    });
    const innerRing = new THREE.Mesh(innerRingGeo, innerRingMat);
    innerRing.rotation.x = Math.PI / 2;
    innerRing.position.y = 0.08;
    group.add(innerRing);
    
    // Energy particles on the base
    const particleCount = 80;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
        const angle = (i / particleCount) * Math.PI * 2;
        const radius = 2.0 + Math.random() * 1.2;
        positions[i * 3] = Math.cos(angle) * radius;
        positions[i * 3 + 1] = 0.1;
        positions[i * 3 + 2] = Math.sin(angle) * radius;
    }
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
        color: 0x44DDFF,
        size: 0.04,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    group.add(particles);
    
    // Energy beams (vertical lines going up)
    const beamCount = 12;
    for (let i = 0; i < beamCount; i++) {
        const angle = (i / beamCount) * Math.PI * 2;
        const radius = 2.8;
        const height = 0.5;
        const points = [
            new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius),
            new THREE.Vector3(Math.cos(angle) * radius * 0.95, height, Math.sin(angle) * radius * 0.95)
        ];
        const beamGeo = new THREE.BufferGeometry().setFromPoints(points);
        const beamMat = new THREE.LineBasicMaterial({
            color: 0x00D4FF,
            transparent: true,
            opacity: 0.15,
            blending: THREE.AdditiveBlending
        });
        const beam = new THREE.Line(beamGeo, beamMat);
        group.add(beam);
    }
    
    scene.add(group);
    return group;
}

const energyBase = createEnergyBase(scene);

// Modified hex grid - removed hexagons inside the circular ring
function createHexGridWithHole(scene) {
    const group = new THREE.Group();

    const radius = 40;
    const spacing = 1.25;
    const holeRadius = 3.5;

    const material = new THREE.LineBasicMaterial({
        color: 0x00D4FF,
        transparent: true,
        opacity: 0.18
    });

    function hex(x, z) {
        const pts = [];
        for (let i = 0; i <= 6; i++) {
            const a = (Math.PI / 3) * i;
            pts.push(
                new THREE.Vector3(
                    Math.cos(a) * 0.55 + x,
                    0,
                    Math.sin(a) * 0.55 + z
                )
            );
        }
        const geo = new THREE.BufferGeometry().setFromPoints(pts);
        return new THREE.Line(geo, material);
    }

    for (let x = -radius; x < radius; x++) {
        for (let z = -radius; z < radius; z++) {
            const offset = (x % 2) * 0.6;
            const px = x * spacing;
            const pz = z * spacing + offset;
            
            const distance = Math.sqrt(px * px + pz * pz);
            if (distance < holeRadius) {
                continue;
            }
            
            group.add(hex(px, pz));
        }
    }

    group.position.set(0, -4.0, -4.0);
    scene.add(group);
    return group;
}

const floor = createHexGridWithHole(scene);

const light = new THREE.PointLight(0x00D4FF, 15);
light.distance = 40;
light.position.set(4, 4, 4);
scene.add(light);

// Audio context setup
let audioContext = null;
let analyser = null;
let dataArray = null;
let isAudioInitialized = false;
let bassFrequency = 0;
let smoothedBass = 0;
let trebleFrequency = 0;
const SMOOTHING = 0.85;

const BASE_CORE_SIZE = 3.0;
const MAX_CORE_SIZE = 4.0;
const MIN_CORE_SIZE = 3.0;

const BASE_RING_SIZE = 3.5;
const MAX_RING_SIZE = 4.2;
const MIN_RING_SIZE = 3.2;

const BASE_INNER_SIZE = 1.1;
const MAX_INNER_SIZE = 1.8;
const MIN_INNER_SIZE = 0.8;

let currentSize = BASE_CORE_SIZE;
let currentPulse = 0;
let targetPulse = 0;
let innerPulse = 0;
let currentInnerSize = BASE_INNER_SIZE;
let currentRingSize = BASE_RING_SIZE;
let isSpeaking = false;
let searchMode = false;
let searchTimer = 0;
let rotationSpeed = 0.0015;
let isActive = false;

async function initAudio() {
    try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 512;
        analyser.smoothingTimeConstant = 0.8;
        dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);
        
        isAudioInitialized = true;
        console.log('🎤 Audio initialized for reactive animation');
        
        detectVoiceActivity();
    } catch (err) {
        console.log('🎤 Audio not available - using fallback animation');
        startFallbackAnimation();
    }
}

function detectVoiceActivity() {
    setInterval(() => {
        if (!isAudioInitialized || !analyser) return;
        
        analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
        }
        const avgEnergy = sum / dataArray.length;
        
        isActive = avgEnergy > 25;
        isSpeaking = avgEnergy > 40;
        
        if (isSpeaking) {
            searchTimer += 0.016;
            if (searchTimer > 2.0 && Math.random() > 0.7) {
                searchMode = true;
                searchTimer = 0;
            }
        } else {
            searchTimer = 0;
            if (searchMode) {
                searchMode = false;
            }
        }
    }, 50);
}

function startFallbackAnimation() {
    let time = 0;
    setInterval(() => {
        time += 0.02;
        bassFrequency = Math.sin(time * 0.8) * 0.5 + 0.5;
        isActive = Math.sin(time * 1.5) > 0.1;
        isSpeaking = Math.sin(time * 1.5) > 0.3;
        if (isSpeaking && Math.random() > 0.8) {
            searchMode = true;
            setTimeout(() => { searchMode = false; }, 1000);
        }
    }, 16);
    console.log('🎤 Using fallback animation (sine wave)');
}

function updateAudioData() {
    if (!isAudioInitialized || !analyser) {
        return;
    }
    
    analyser.getByteFrequencyData(dataArray);
    
    let bassSum = 0;
    const bassCount = Math.floor(dataArray.length / 4);
    for (let i = 0; i < bassCount; i++) {
        bassSum += dataArray[i];
    }
    bassFrequency = bassSum / (bassCount * 255);
    
    let trebleSum = 0;
    const trebleStart = Math.floor(dataArray.length * 0.7);
    for (let i = trebleStart; i < dataArray.length; i++) {
        trebleSum += dataArray[i];
    }
    trebleFrequency = trebleSum / ((dataArray.length - trebleStart) * 255);
    
    smoothedBass = smoothedBass * SMOOTHING + bassFrequency * (1 - SMOOTHING);
}

function updateCoreSize() {
    let pulseValue;
    
    if (isAudioInitialized) {
        if (isActive) {
            pulseValue = smoothedBass * 0.8 + 0.2;
        } else {
            pulseValue = 0.5;
        }
    } else {
        const time = Date.now() / 1000;
        if (isSpeaking) {
            pulseValue = Math.sin(time * 0.6) * 0.35 + 0.65;
        } else {
            pulseValue = 0.5;
        }
    }
    
    if (isSpeaking && isActive) {
        pulseValue = Math.min(pulseValue * 1.2, 0.9);
    }
    
    targetPulse = pulseValue;
    currentPulse += (targetPulse - currentPulse) * 0.08;
    
    const pulseFactor = isActive ? (isSpeaking ? 1.3 : 1.1) : 0;
    const targetSize = BASE_CORE_SIZE + (currentPulse - 0.5) * 1.0 * pulseFactor;
    currentSize += (targetSize - currentSize) * 0.08;
    
    if (!isActive) {
        currentSize += (BASE_CORE_SIZE - currentSize) * 0.05;
    }
    
    const clampedSize = Math.max(MIN_CORE_SIZE, Math.min(MAX_CORE_SIZE, currentSize));
    
    if (core.geometry) {
        const newGeometry = new THREE.SphereGeometry(clampedSize, 32, 32);
        core.geometry.dispose();
        core.geometry = newGeometry;
    }
    
    // Update outer ring to pulse with core (no rotation)
    const targetRingSize = BASE_RING_SIZE + (currentPulse - 0.5) * 0.8 * pulseFactor;
    currentRingSize += (targetRingSize - currentRingSize) * 0.08;
    
    if (!isActive) {
        currentRingSize += (BASE_RING_SIZE - currentRingSize) * 0.05;
    }
    
    const clampedRingSize = Math.max(MIN_RING_SIZE, Math.min(MAX_RING_SIZE, currentRingSize));
    
    if (outerRing.geometry) {
        const newRingGeo = new THREE.TorusGeometry(clampedRingSize, 0.05, 32, 64);
        outerRing.geometry.dispose();
        outerRing.geometry = newRingGeo;
        outerRing.material.opacity = 0.3 + currentPulse * 0.4;
    }
    
    // Ring does NOT rotate - removed rotation code
    
    const innerPulseFactor = isActive ? (isSpeaking ? 1.4 : 1.1) : 0;
    const targetInnerSize = BASE_INNER_SIZE + (currentPulse - 0.5) * 1.0 * innerPulseFactor;
    currentInnerSize += (targetInnerSize - currentInnerSize) * 0.08;
    
    if (!isActive) {
        currentInnerSize += (BASE_INNER_SIZE - currentInnerSize) * 0.05;
    }
    
    const clampedInnerSize = Math.max(MIN_INNER_SIZE, Math.min(MAX_INNER_SIZE, currentInnerSize));
    
    if (innerCore.geometry) {
        const newInnerGeometry = new THREE.IcosahedronGeometry(clampedInnerSize, 3);
        innerCore.geometry.dispose();
        innerCore.geometry = newInnerGeometry;
    }
    
    const glowSize = clampedInnerSize * 0.7;
    if (innerGlow.geometry) {
        const newGlowGeometry = new THREE.SphereGeometry(glowSize, 32, 32);
        innerGlow.geometry.dispose();
        innerGlow.geometry = newGlowGeometry;
    }
    innerGlow.material.opacity = isActive ? (0.1 + currentPulse * 0.12) : 0.1;
    
    if (searchMode) {
        rotationSpeed = 0.03 + trebleFrequency * 0.05;
    } else if (isActive) {
        rotationSpeed = 0.008 + trebleFrequency * 0.01;
    } else {
        rotationSpeed = 0.0015;
    }
    rotationSpeed = Math.min(rotationSpeed, 0.08);
    
    energyBase.children.forEach(child => {
        if (child.isMesh && child.geometry.type === 'CylinderGeometry') {
            const scale = isActive ? (1 + currentPulse * 0.04) : 1;
            child.scale.set(scale, 1, scale);
            child.material.opacity = isActive ? (0.04 + currentPulse * 0.05) : 0.04;
        }
        if (child.isMesh && child.geometry.type === 'TorusGeometry') {
            const scale = isActive ? (1 + currentPulse * 0.025) : 1;
            child.scale.set(scale, scale, scale);
            child.material.opacity = isActive ? (0.18 + currentPulse * 0.3) : 0.18;
        }
        if (child.isPoints) {
            const scale = isActive ? (1 + currentPulse * 0.08) : 1;
            child.scale.set(scale, scale, scale);
            child.material.opacity = isActive ? (0.25 + currentPulse * 0.3) : 0.25;
        }
    });
    
    energyBase.rotation.y += isActive ? 0.005 : 0.001;
    
    innerPulse += (pulseValue - innerPulse) * 0.15;
    const innerSpeed = searchMode ? 0.05 : (isActive ? 0.015 : 0.005);
    innerCore.rotation.x += innerSpeed + pulseValue * 0.02;
    innerCore.rotation.y += innerSpeed * 1.5 + pulseValue * 0.025;
    
    innerGlow.rotation.copy(innerCore.rotation);
    
    const glowIntensity = isActive ? (0.25 + currentPulse * 0.3) : 0.15;
    bloom.strength = isActive ? (0.25 + glowIntensity * 0.3) : 0.15;
}

window.addEventListener("resize", () => {
    const width = window.innerWidth;
    const height = window.innerHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    composer.setSize(width, height);
});

document.addEventListener('click', () => {
    if (!isAudioInitialized) {
        initAudio();
    }
});

setTimeout(() => {
    initAudio();
}, 1000);

function animate() {
    requestAnimationFrame(animate);

    updateAudioData();
    updateCoreSize();

    floor.rotation.y += 0.0001;

    composer.render();
}

animate();