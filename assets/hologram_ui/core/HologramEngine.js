import { SceneManager } from "./SceneManager";
import { Camera } from "./Camera";
import { Renderer } from "./Renderer";
import { Lights } from "./Lights";
import { AnimationLoop } from "./AnimationLoop";

export class HologramEngine {

    constructor(container){

        this.sceneManager = new SceneManager();

        this.camera = new Camera();

        this.renderer = new Renderer(container);

        this.lights = new Lights(this.sceneManager.scene);

        this.loop = new AnimationLoop(
            this.renderer.renderer,
            this.sceneManager.scene,
            this.camera.camera
        );

        window.addEventListener("resize",()=>{

            this.camera.camera.aspect =
                window.innerWidth/window.innerHeight;

            this.camera.camera.updateProjectionMatrix();

            this.renderer.resize(
                window.innerWidth,
                window.innerHeight
            );

        });

    }

    start(){

        this.loop.start();

    }

}