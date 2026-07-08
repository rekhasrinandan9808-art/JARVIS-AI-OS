/**
 * hologram_connector_reference.js
 * Reference only -- NOT dropped into your hologram project automatically,
 * since you said you already have one. This is what to adapt into your
 * existing hologram/js/jarvisConnector.js + websocket.js.
 *
 * Backend: ws://<host>:8000/ws  (see api/rest_server/main.py)
 */

class JarvisConnector {
  constructor(url = "ws://localhost:8000/ws", apiKey = null) {
    // apiKey: get one by running `python -m api.rest_server.gen_key` on the
    // backend, or copy the one printed to the server's console on first run.
    this.url = apiKey ? `${url}?key=${encodeURIComponent(apiKey)}` : url;
    this.apiKey = apiKey;
    this.ws = null;
    this.requestId = 0;
    this.pending = new Map();       // request_id -> {resolve, reject}
    this.eventListeners = new Map(); // topic prefix -> [callback]
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => console.log("[JARVIS] connected");
    this.ws.onclose = () => {
      console.log("[JARVIS] disconnected, retrying in 2s");
      setTimeout(() => this.connect(), 2000);
    };
    this.ws.onerror = (e) => console.error("[JARVIS] socket error", e);

    this.ws.onmessage = (msg) => {
      const data = JSON.parse(msg.data);

      if (data.type === "result") {
        const pending = this.pending.get(data.request_id);
        if (pending) {
          pending.resolve(data);
          this.pending.delete(data.request_id);
        }
        return;
      }

      if (data.type === "event") {
        // e.g. topic "agent.task.completed" -- use this to drive hologram
        // reactions: pulse energyCore.js on completion, flash red on failure, etc.
        for (const [prefix, callbacks] of this.eventListeners) {
          if (data.topic.startsWith(prefix)) {
            callbacks.forEach((cb) => cb(data));
          }
        }
      }
    };
  }

  // Call any of the 39 agents, e.g. execute("math_agent", "explain", {topic: "derivative"})
  execute(agent, action, params = {}) {
    const request_id = ++this.requestId;
    return new Promise((resolve, reject) => {
      this.pending.set(request_id, { resolve, reject });
      this.ws.send(JSON.stringify({ type: "execute", agent, action, params, request_id }));
    });
  }

  // Subscribe to backend events to drive visuals, e.g.
  // jarvis.on("agent.task.completed", (e) => hologram.pulse());
  on(topicPrefix, callback) {
    if (!this.eventListeners.has(topicPrefix)) this.eventListeners.set(topicPrefix, []);
    this.eventListeners.get(topicPrefix).push(callback);
  }
}

// usage inside your existing hologram code:
// const jarvis = new JarvisConnector("ws://localhost:8000/ws", "jarvis_yourActualKeyHere");
// jarvis.connect();
// jarvis.on("agent.task.completed", (e) => energyCore.pulse());
// const result = await jarvis.execute("memory", "get", { key: "user_name" });
