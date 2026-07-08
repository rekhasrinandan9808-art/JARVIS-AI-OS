import json
import time
import threading
from flask import Flask, Response, jsonify, send_from_directory
import psutil
import platform
import os

app = Flask(__name__, static_folder='static', static_url_path='')

class HologramDataProvider:
    def __init__(self):
        self.running = True
        
    def get_system_stats(self):
        return {
            'cpu': psutil.cpu_percent(),
            'memory': psutil.virtual_memory().percent,
            'network': 89,
            'energy': 94,
            'environment': {
                'temp': '24°C',
                'humidity': '48%',
                'pressure': '1012 hPa',
                'wind': '3.2 m/s'
            },
            'uptime': time.time() - psutil.boot_time(),
            'timestamp': time.time()
        }
    
    def get_agents_status(self):
        agents = [
            'memory', 'rag', 'research', 'coding', 'debugging', 'testing', 'documentation',
            'browser', 'files', 'windows', 'linux', 'networking', 'robotics', 'iot',
            'plugins', 'vision', 'voice', 'ocr', 'translation', 'learning', 'security',
            'admin', 'communications', 'math_agent', 'physics_agent', 'chemistry_agent',
            'biology_agent', 'history_agent', 'geography_agent', 'literature_agent',
            'philosophy_agent', 'cs_agent', 'lang_agent', 'art_agent', 'economics_agent',
            'law_agent', 'medical_agent', 'app_controller', 'supervisor'
        ]
        return {'agents': [{'name': a, 'status': 'active'} for a in agents]}

provider = HologramDataProvider()

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/stats')
def stats():
    return jsonify(provider.get_system_stats())

@app.route('/api/agents')
def agents():
    return jsonify(provider.get_agents_status())

@app.route('/api/events')
def events():
    def generate():
        while True:
            data = {
                'stats': provider.get_system_stats(),
                'agents': provider.get_agents_status(),
                'timestamp': time.time()
            }
            yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
