"""
runtime/watchdog/windows_service.py
Installs the watchdog as a real Windows Service, so JARVIS starts at boot
(even before any user logs in) and keeps running for as long as Windows is
running -- not just for the duration of a logged-in session.

Requires: pip install pywin32

Install (run cmd/PowerShell as Administrator, from this folder):
    python windows_service.py install
    python windows_service.py start

Uninstall:
    python windows_service.py stop
    python windows_service.py remove

Check status: Windows Services app (services.msc) -> "JARVIS AI OS Watchdog"

If you'd rather NOT install a full Windows Service (no admin rights needed),
use the simpler option instead: a Scheduled Task set to "run at logon" that
just launches watchdog.py -- see the README section "Autostart without
admin rights" for the exact schtasks.exe command.
"""

from __future__ import annotations
import os
import sys

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
except ImportError:
    win32serviceutil = None


if win32serviceutil is not None:

    class JarvisWatchdogService(win32serviceutil.ServiceFramework):
        _svc_name_ = "JarvisAIOSWatchdog"
        _svc_display_name_ = "JARVIS AI OS Watchdog"
        _svc_description_ = "Keeps the JARVIS AI OS REST/WebSocket server running continuously, restarting it if it crashes."

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.watchdog = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.watchdog:
                self.watchdog.stop()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self.main()

        def main(self):
            # Import here (not at module top) so this file still parses/loads
            # fine on non-Windows machines for code review purposes.
            from watchdog import Watchdog

            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            python_dir = os.path.join(project_root, "python")

            self.watchdog = Watchdog(
                command=[sys.executable, "-m", "uvicorn", "api.rest_server.main:app", "--host", "0.0.0.0", "--port", "8000"],
                cwd=python_dir,
                check_interval_seconds=5,
            )
            self.watchdog.run_forever()


def main():
    if win32serviceutil is None:
        print("pywin32 is not installed. Run: pip install pywin32")
        print("Then re-run this script as Administrator.")
        return
    win32serviceutil.HandleCommandLine(JarvisWatchdogService)


if __name__ == "__main__":
    main()
