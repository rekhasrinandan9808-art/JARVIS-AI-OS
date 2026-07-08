@echo off
REM JARVIS AI OS -- Windows launcher WITH watchdog (keeps it running continuously)
cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo Starting JARVIS AI OS under the watchdog -- it will auto-restart if it crashes.
echo Press Ctrl+C to stop everything.
python runtime\watchdog\watchdog.py --command "python -m uvicorn api.rest_server.main:app --host 0.0.0.0 --port 8000" --cwd python
