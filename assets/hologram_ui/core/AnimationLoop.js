import * as THREE from "three";
export class AnimationLoop {

    constructor(renderer, scene, camera) {

        this.renderer = renderer;
        this.scene = scene;
        this.camera = camera;

        this.clock = new THREE.Clock();

        this.callbacks = [];

    }

    add(callback){

        this.callbacks.push(callback);

    }

    start(){

        const animate = ()=>{

            requestAnimationFrame(animate);

            const delta = this.clock.getDelta();

            this.callbacks.forEach(cb=>cb(delta));

            this.renderer.render(this.scene,this.camera);

        };

        animate();

    }

}