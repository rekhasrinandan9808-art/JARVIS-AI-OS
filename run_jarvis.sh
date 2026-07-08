#!/usr/bin/env bash
# JARVIS AI OS -- local launcher
# Usage: ./run_jarvis.sh
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt

echo "Starting JARVIS AI OS REST + WebSocket server on http://localhost:8000"
echo "  REST:      http://localhost:8000/agents"
echo "  WebSocket: ws://localhost:8000/ws   (point your hologram here)"
cd python
uvicorn api.rest_server.main:app --reload --host 0.0.0.0 --port 8000
