/**
 * hologram_agent_panels_reference.js
 * Reference only -- adapt into your existing hologram/js/ (e.g. as a new
 * module imported from main.js, alongside jarvisConnector.js).
 *
 * Renders two fixed side panels (left/right) listing every registered
 * agent, each with a deterministic color (same hash function as the
 * backend's supervisor progress data would use), a live status dot that
 * flashes on agent.task.completed/failed events, and a running call count.
 *
 * Depends on JarvisConnector from hologram_connector_reference.js
 * (ws://<host>:8000/ws) and the REST endpoint http://<host>:8000/agents
 * for the initial agent list.
 */

const COLOR_RAMPS = [
  { name: "purple", fill: "#EEEDFE", stroke: "#534AB7", text: "#26215C" },
  { name: "teal",   fill: "#E1F5EE", stroke: "#0F6E56", text: "#04342C" },
  { name: "coral",  fill: "#FAECE7", stroke: "#993C1D", text: "#4A1B0C" },
  { name: "pink",   fill: "#FBEAF0", stroke: "#993556", text: "#4B1528" },
  { name: "blue",   fill: "#E6F1FB", stroke: "#185FA5", text: "#042C53" },
  { name: "green",  fill: "#EAF3DE", stroke: "#3B6D11", text: "#173404" },
  { name: "amber",  fill: "#FAEEDA", stroke: "#854F0B", text: "#412402" },
  { name: "red",    fill: "#FCEBEB", stroke: "#A32D2D", text: "#501313" },
  { name: "gray",   fill: "#F1EFE8", stroke: "#5F5E5A", text: "#2C2C2A" },
];

// Deterministic hash so a given agent name always gets the same color,
// across page reloads and between the left/right panel and any other
// UI (e.g. a future admin dashboard) that reuses this function.
function colorForAgent(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return COLOR_RAMPS[h % COLOR_RAMPS.length];
}

class AgentPanels {
  /**
   * @param {JarvisConnector} jarvis - an already-constructed, connected JarvisConnector
   * @param {string} restBaseUrl - e.g. "http://localhost:8000"
   */
  constructor(jarvis, restBaseUrl = "http://localhost:8000") {
    this.jarvis = jarvis;
    this.restBaseUrl = restBaseUrl;
    this.rows = new Map(); // agent name -> { el, dotEl, countEl, count }
    this.leftPanel = null;
    this.rightPanel = null;
  }

  async init() {
    this._buildPanelShells();
    await this._loadAgentList();
    this._wireLiveEvents();
  }

  _buildPanelShells() {
    const baseStyle = `
      position: fixed; top: 80px; bottom: 80px; width: 220px;
      overflow-y: auto; z-index: 50; padding: 10px;
      display: flex; flex-direction: column; gap: 6px;
      font-family: system-ui, sans-serif; pointer-events: auto;
    `;

    this.leftPanel = document.createElement("div");
    this.leftPanel.id = "jarvis-agent-panel-left";
    this.leftPanel.style.cssText = baseStyle + "left: 16px;";
    document.body.appendChild(this.leftPanel);

    this.rightPanel = document.createElement("div");
    this.rightPanel.id = "jarvis-agent-panel-right";
    this.rightPanel.style.cssText = baseStyle + "right: 16px;";
    document.body.appendChild(this.rightPanel);
  }

  async _loadAgentList() {
    const headers = this.jarvis.apiKey ? { Authorization: `Bearer ${this.jarvis.apiKey}` } : {};
    const res = await fetch(`${this.restBaseUrl}/agents`, { headers });
    const agents = await res.json(); // [{agent, agent_id, description, capabilities}, ...]
    agents.sort((a, b) => (a.agent_id || 99) - (b.agent_id || 99));

    const half = Math.ceil(agents.length / 2);
    agents.slice(0, half).forEach((a) => this._addRow(this.leftPanel, a));
    agents.slice(half).forEach((a) => this._addRow(this.rightPanel, a));
  }

  _addRow(panel, agentInfo) {
    const name = agentInfo.agent;
    const color = colorForAgent(name);

    const row = document.createElement("div");
    row.style.cssText = `
      display: flex; align-items: center; gap: 8px;
      padding: 6px 10px; border-radius: 8px;
      background: ${color.fill}; border-left: 3px solid ${color.stroke};
      cursor: pointer; transition: transform 0.15s ease;
    `;
    row.title = agentInfo.description || name;

    const dot = document.createElement("span");
    dot.style.cssText = `
      width: 7px; height: 7px; border-radius: 50%;
      background: ${color.stroke}; flex-shrink: 0;
      transition: box-shadow 0.2s ease;
    `;

    const label = document.createElement("span");
    label.textContent = name;
    label.style.cssText = `font-size: 12px; color: ${color.text}; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;`;

    const count = document.createElement("span");
    count.textContent = "0";
    count.style.cssText = `font-size: 10px; color: ${color.text}; opacity: 0.7;`;

    row.append(dot, label, count);
    panel.appendChild(row);

    // Clicking an agent asks it for its own progress -- useful during dev/debugging.
    row.addEventListener("click", async () => {
      const result = await this.jarvis.execute("supervisor", "progress_report", {});
      console.log(`[JARVIS] progress report (clicked ${name}):`, result);
    });

    this.rows.set(name, { el: row, dotEl: dot, countEl: count, count: 0 });
  }

  _wireLiveEvents() {
    // Flash the dot and bump the counter whenever this agent completes or fails a task.
    const flash = (agentName, success) => {
      const entry = this.rows.get(agentName);
      if (!entry) return;
      entry.count += 1;
      entry.countEl.textContent = String(entry.count);
      const glowColor = success ? "0 0 6px 2px rgba(80,200,120,0.8)" : "0 0 6px 2px rgba(220,60,60,0.8)";
      entry.dotEl.style.boxShadow = glowColor;
      setTimeout(() => { entry.dotEl.style.boxShadow = "none"; }, 600);
    };

    this.jarvis.on("agent.task.completed", (e) => flash(e.source, true));
    this.jarvis.on("agent.task.failed", (e) => flash(e.source, false));
  }
}

// usage inside your existing hologram code (after connecting JarvisConnector):
// const panels = new AgentPanels(jarvis, "http://localhost:8000");
// await panels.init();

export { AgentPanels, colorForAgent };
