"""
desktop_python/desktop_app.py
A real, working desktop shell for JARVIS AI OS -- a native window (via
pywebview) hosting your hologram, plus a system tray icon (via pystray)
for quick controls without keeping a terminal window open.

This is a lighter-weight alternative to the full C# WPF shell in the
original architecture doc (desktop/JARVIS.Shell/) -- same job (native
window + tray + control panel), buildable today with two pip installs
instead of a Visual Studio project. If you want the full WPF version
later, this Python shell's REST calls translate directly to C#
HttpClient calls against the same /agents, /execute, /health endpoints.

Requires:
    pip install pywebview pystray pillow

Run:
    python desktop_app.py
    (starts the JARVIS backend automatically if it's not already running,
    opens your hologram in a native window, adds a tray icon)
"""

from __future__ import annotations
import os
import subprocess
import sys
import threading
import time
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
HOLOGRAM_DIR = os.path.join(PROJECT_ROOT, "hologram")
BACKEND_URL = "http://localhost:8000"
HOLOGRAM_URL = "http://localhost:5173"  # vite's default dev server port


def backend_is_up() -> bool:
    try:
        urllib.request.urlopen(BACKEND_URL, timeout=1.5)
        return True
    except Exception:
        return False


class JarvisDesktopApp:
    def __init__(self):
        self.backend_process = None
        self.hologram_process = None
        self.window = None
        self.tray_icon = None

    # ---- process management --------------------------------------------------
    def start_backend(self):
        if backend_is_up():
            print("[desktop] Backend already running.")
            return
        print("[desktop] Starting backend...")
        self.backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.rest_server.main:app", "--port", "8000"],
            cwd=PYTHON_DIR,
        )
        for _ in range(30):
            if backend_is_up():
                print("[desktop] Backend is up.")
                return
            time.sleep(0.5)
        print("[desktop] WARNING: backend did not respond after 15s -- check its console output.")

    def start_hologram_dev_server(self):
        """Optional: only if you run the hologram via `npm run dev` instead of a pre-built dist/."""
        if not os.path.isdir(HOLOGRAM_DIR):
            print("[desktop] No hologram/ directory found -- skipping.")
            return
        print("[desktop] Starting hologram dev server...")
        self.hologram_process = subprocess.Popen(["npm", "run", "dev"], cwd=HOLOGRAM_DIR, shell=(os.name == "nt"))
        time.sleep(3)  # give vite a moment to bind its port

    def stop_all(self):
        for proc in (self.backend_process, self.hologram_process):
            if proc and proc.poll() is None:
                proc.terminate()

    # ---- native window ---------------------------------------------------------
    def open_window(self):
        try:
            import webview
        except ImportError:
            print("[desktop] pywebview not installed. Run: pip install pywebview")
            print(f"[desktop] Falling back to your default browser at {HOLOGRAM_URL}")
            import webbrowser
            webbrowser.open(HOLOGRAM_URL)
            return

        target_url = HOLOGRAM_URL if self._url_reachable(HOLOGRAM_URL) else self._local_dist_path()
        self.window = webview.create_window("JARVIS AI OS", target_url, width=1280, height=800)
        webview.start()

    def _url_reachable(self, url: str) -> bool:
        try:
            urllib.request.urlopen(url, timeout=1.5)
            return True
        except Exception:
            return False

    def _local_dist_path(self) -> str:
        dist_index = os.path.join(HOLOGRAM_DIR, "dist", "index.html")
        if os.path.exists(dist_index):
            return "file://" + dist_index.replace("\\", "/")
        # last resort: a simple status page pointing at the REST API
        return BACKEND_URL

    # ---- system tray -------------------------------------------------------
    def start_tray_icon(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            print("[desktop] pystray/pillow not installed -- skipping tray icon. Run: pip install pystray pillow")
            return

        img = Image.new("RGB", (64, 64), color=(20, 20, 30))
        draw = ImageDraw.Draw(img)
        draw.ellipse((14, 14, 50, 50), fill=(60, 160, 255))

        def on_open(icon, item):
            import webbrowser
            webbrowser.open(HOLOGRAM_URL if self._url_reachable(HOLOGRAM_URL) else BACKEND_URL)

        def on_restart_backend(icon, item):
            if self.backend_process:
                self.backend_process.terminate()
            self.start_backend()

        def on_quit(icon, item):
            self.stop_all()
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem("Open JARVIS", on_open, default=True),
            pystray.MenuItem("Restart backend", on_restart_backend),
            pystray.MenuItem("Quit", on_quit),
        )
        self.tray_icon = pystray.Icon("jarvis", img, "JARVIS AI OS", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def run(self):
        self.start_backend()
        self.start_tray_icon()
        self.open_window()  # blocks until window closes
        self.stop_all()


if __name__ == "__main__":
    app = JarvisDesktopApp()
    app.run()
