import * as THREE from "three";

export class Lights {

    constructor(scene) {

        const ambient = new THREE.AmbientLight(0xffffff, 1.2);
        scene.add(ambient);

        const point = new THREE.PointLight(0xffb400, 15);

        point.position.set(5,5,5);

        scene.add(point);

    }

}