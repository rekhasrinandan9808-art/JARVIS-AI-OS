"""
api/mobile_api.py
Mobile App API - REST endpoints for mobile control
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import psutil
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Shared state (in production, use Redis)
jarvis_state = {
    "status": "online",
    "commands": [],
    "responses": []
}


@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """Get system status."""
    return jsonify({
        "status": jarvis_state.get("status", "online"),
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "uptime": psutil.boot_time(),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/v1/command', methods=['POST'])
def send_command():
    """Send a command to JARVIS."""
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({"success": False, "error": "No command"}), 400
    
    # Queue command (processed by main JARVIS loop)
    jarvis_state["commands"].append({
        "command": command,
        "timestamp": datetime.now().isoformat()
    })
    
    return jsonify({
        "success": True,
        "command": command,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/v1/responses', methods=['GET'])
def get_responses():
    """Get recent responses."""
    limit = int(request.args.get('limit', 10))
    responses = jarvis_state["responses"][-limit:]
    return jsonify(responses)


@app.route('/api/v1/memory', methods=['GET'])
def get_memory():
    """Get memory stats."""
    # Would connect to memory agent
    return jsonify({
        "conversations": 0,
        "facts": 0,
        "preferences": 0
    })


@app.route('/api/v1/processes', methods=['GET'])
def get_processes():
    """Get running processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            processes.append(proc.info)
        except:
            continue
    return jsonify(processes[:50])


@app.route('/api/v1/kill', methods=['POST'])
def kill_process():
    """Kill a process."""
    data = request.json
    pid = data.get('pid')
    if pid:
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return jsonify({"success": True, "pid": pid})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": False, "error": "No PID"}), 400


@app.route('/api/v1/voice', methods=['POST'])
def voice_command():
    """Voice command endpoint for mobile."""
    data = request.json
    text = data.get('text', '')
    # Process voice text
    return jsonify({"success": True, "text": text})


def start_mobile_api(port: int = 5001):
    """Start the mobile API server."""
    app.run(host='0.0.0.0', port=port, debug=False)