import * as THREE from "three";

export class Camera {

    constructor() {

        this.camera = new THREE.PerspectiveCamera(
            45,
            window.innerWidth / window.innerHeight,
            0.1,
            1000
        );

        this.camera.position.set(0, 2, 8);

    }

}