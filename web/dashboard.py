"""
web/dashboard.py
Web Dashboard - Flask-based UI for JARVIS
"""

import os
import json
import asyncio
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'jarvis-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store state
jarvis_state = {
    "status": "idle",
    "agents": [],
    "memory_stats": {},
    "system_info": {},
    "conversations": [],
    "commands": []
}


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get system status."""
    return jsonify({
        "status": jarvis_state.get("status", "idle"),
        "agents": len(jarvis_state.get("agents", [])),
        "uptime": jarvis_state.get("uptime", 0),
        "memory": jarvis_state.get("memory_stats", {})
    })


@app.route('/api/agents')
def api_agents():
    """Get agent list."""
    return jsonify(jarvis_state.get("agents", []))


@app.route('/api/memory')
def api_memory():
    """Get memory stats."""
    return jsonify(jarvis_state.get("memory_stats", {}))


@app.route('/api/system')
def api_system():
    """Get system info."""
    return jsonify(jarvis_state.get("system_info", {}))


@app.route('/api/conversations')
def api_conversations():
    """Get recent conversations."""
    return jsonify(jarvis_state.get("conversations", []))


@app.route('/api/command', methods=['POST'])
def api_command():
    """Send a command to JARVIS."""
    data = request.json
    command = data.get('command', '')
    if command:
        jarvis_state["commands"].append({
            "command": command,
            "timestamp": datetime.now().isoformat()
        })
        # Here you would send to JARVIS
        socketio.emit('command', {'command': command})
        return jsonify({"success": True, "command": command})
    return jsonify({"success": False, "error": "No command"})


@socketio.on('connect')
def handle_connect():
    """WebSocket connection."""
    emit('connected', {'status': 'connected to JARVIS'})


# Web dashboard templates
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>JARVIS Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0a0a0a; color: #00ff88; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { border-bottom: 2px solid #00ff88; padding-bottom: 10px; margin-bottom: 20px; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.online { background: #00ff88; color: #0a0a0a; }
        .status.offline { background: #ff4444; color: #fff; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #1a1a2e; border: 1px solid #00ff88; border-radius: 10px; padding: 20px; }
        .card h3 { margin-top: 0; color: #00ff88; }
        .stat { font-size: 2em; }
        .stat-label { color: #888; font-size: 0.8em; }
        .conversations { max-height: 300px; overflow-y: auto; }
        .conversation { border-bottom: 1px solid #333; padding: 10px 0; }
        .conversation .user { color: #88ffcc; }
        .conversation .assistant { color: #ffaa00; }
        .input-area { display: flex; gap: 10px; margin-top: 20px; }
        .input-area input { flex: 1; padding: 10px; background: #1a1a2e; border: 1px solid #00ff88; color: #fff; border-radius: 5px; }
        .input-area button { padding: 10px 20px; background: #00ff88; color: #0a0a0a; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; }
        .input-area button:hover { background: #00cc77; }
        .logs { background: #0a0a0a; border: 1px solid #333; border-radius: 5px; padding: 10px; height: 150px; overflow-y: auto; font-family: monospace; font-size: 0.9em; }
        .logs .log { color: #aaa; }
        .logs .log.success { color: #00ff88; }
        .logs .log.error { color: #ff4444; }
        .logs .log.warning { color: #ffaa00; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦾 JARVIS OS Dashboard</h1>
            <span class="status online" id="status">● Online</span>
            <span style="margin-left: 20px; color: #888;" id="uptime">Uptime: 0s</span>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🤖 Agents</h3>
                <div class="stat" id="agentCount">0</div>
                <div class="stat-label">Total Agents</div>
            </div>
            <div class="card">
                <h3>🧠 Memory</h3>
                <div class="stat" id="memoryCount">0</div>
                <div class="stat-label">Stored Memories</div>
            </div>
            <div class="card">
                <h3>💬 Conversations</h3>
                <div class="stat" id="convCount">0</div>
                <div class="stat-label">Total Conversations</div>
            </div>
            <div class="card">
                <h3>⚡ System</h3>
                <div class="stat" id="cpuStat">0%</div>
                <div class="stat-label">CPU Usage</div>
                <div style="margin-top: 5px;">
                    <span id="memStat">0%</span> <span class="stat-label">Memory</span>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>💬 Conversations</h3>
            <div class="conversations" id="conversations">
                <div style="color: #888;">No conversations yet</div>
            </div>
        </div>
        
        <div class="input-area">
            <input type="text" id="commandInput" placeholder="Type a command..." onkeypress="if(event.key==='Enter') sendCommand()">
            <button onclick="sendCommand()">Send</button>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>📋 Logs</h3>
            <div class="logs" id="logs">
                <div class="log">System ready...</div>
            </div>
        </div>
    </div>
    
    <script>
        // Send command
        function sendCommand() {
            const input = document.getElementById('commandInput');
            const command = input.value.trim();
            if (!command) return;
            
            fetch('/api/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: command })
            });
            
            addLog('Command sent: ' + command, 'success');
            input.value = '';
        }
        
        // Add log
        function addLog(message, type = '') {
            const logs = document.getElementById('logs');
            const entry = document.createElement('div');
            entry.className = 'log ' + type;
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + message;
            logs.appendChild(entry);
            logs.scrollTop = logs.scrollHeight;
        }
        
        // Update stats
        async function updateStats() {
            try {
                const resp = await fetch('/api/status');
                const data = await resp.json();
                document.getElementById('agentCount').textContent = data.agents || 0;
                document.getElementById('status').textContent = data.status === 'online' ? '● Online' : '● Offline';
                document.getElementById('status').className = 'status ' + (data.status === 'online' ? 'online' : 'offline');
                
                if (data.memory) {
                    document.getElementById('memoryCount').textContent = data.memory.conversations || 0;
                    document.getElementById('convCount').textContent = data.memory.conversations || 0;
                }
                
                if (data.cpu !== undefined) {
                    document.getElementById('cpuStat').textContent = data.cpu + '%';
                }
                if (data.memory_percent !== undefined) {
                    document.getElementById('memStat').textContent = data.memory_percent + '%';
                }
                if (data.uptime) {
                    document.getElementById('uptime').textContent = 'Uptime: ' + Math.floor(data.uptime) + 's';
                }
            } catch(e) {
                console.error(e);
            }
        }
        
        // Load conversations
        async function loadConversations() {
            try {
                const resp = await fetch('/api/conversations');
                const data = await resp.json();
                const container = document.getElementById('conversations');
                container.innerHTML = '';
                if (data.length === 0) {
                    container.innerHTML = '<div style="color: #888;">No conversations yet</div>';
                } else {
                    data.forEach(conv => {
                        const div = document.createElement('div');
                        div.className = 'conversation';
                        div.innerHTML = `
                            <div class="user">🧑 ${conv.user_input || 'User'}</div>
                            <div class="assistant">🤖 ${conv.response || '...'}</div>
                        `;
                        container.appendChild(div);
                    });
                }
            } catch(e) {
                console.error(e);
            }
        }
        
        // Update every 5 seconds
        setInterval(updateStats, 5000);
        setInterval(loadConversations, 10000);
        updateStats();
        loadConversations();
        
        // WebSocket
        const socket = io();
        socket.on('connect', () => {
            addLog('Connected to JARVIS', 'success');
        });
        socket.on('command', (data) => {
            addLog('Processing: ' + data.command, 'warning');
        });
    </script>
</body>
</html>
"""


def start_dashboard(port: int = 5000, debug: bool = False):
    """Start the dashboard server."""
    # Create templates folder if not exists
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # Write template
    with open(os.path.join(template_dir, 'dashboard.html'), 'w') as f:
        f.write(DASHBOARD_HTML)
    
    # Run in a thread
    def run():
        socketio.run(app, host='0.0.0.0', port=port, debug=debug)
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logger.info(f"🌐 Dashboard running at http://localhost:{port}")
    return thread


if __name__ == '__main__':
    start_dashboard(debug=True)