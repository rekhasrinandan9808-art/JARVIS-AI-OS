"""
runtime/watchdog/watchdog.py
Keeps the JARVIS REST server (or any command you point it at) running
continuously. If the process dies -- crash, killed, whatever -- the watchdog
notices within `check_interval_seconds` and restarts it, with exponential
backoff so a genuine crash-loop doesn't hammer the machine.

This is distinct from runtime/process_manager/manager.py, which supervises
services *within* one running Python process (asyncio tasks). This watchdog
supervises the whole OS process from *outside* it, so it survives even if
the entire Python interpreter dies -- which is what "run on Windows the
whole time" actually requires.

Usage:
    python watchdog.py --command "python api/rest_server/main.py" --cwd ../../python

Run this itself as a Windows service / scheduled task at logon (see
runtime/watchdog/windows_service.py and the README section on autostart)
so it, in turn, survives reboots.
"""

from __future__ import annotations
import argparse
import logging
import subprocess
import time
from typing import List, Optional

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [watchdog] %(message)s",
)
logger = logging.getLogger("jarvis.watchdog")


class Watchdog:
    def __init__(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        check_interval_seconds: float = 5.0,
        max_backoff_seconds: float = 120.0,
    ):
        self.command = command
        self.cwd = cwd
        self.check_interval_seconds = check_interval_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self._stopping = False

    def _start_process(self) -> subprocess.Popen:
        logger.info("Starting: %s", " ".join(self.command))
        return subprocess.Popen(self.command, cwd=self.cwd)

    def _is_alive(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None  # None means still running

    def run_forever(self) -> None:
        logger.info("Watchdog started. Watching: %s", " ".join(self.command))
        self.process = self._start_process()

        while not self._stopping:
            time.sleep(self.check_interval_seconds)

            if self._is_alive():
                self.restart_count = 0  # reset backoff once it's been healthy for a full check interval
                continue

            exit_code = self.process.poll()
            logger.warning("Process died (exit code %s). Restarting...", exit_code)
            self.restart_count += 1
            backoff = min(self.max_backoff_seconds, 2 ** min(self.restart_count, 7))
            logger.info("Waiting %.1fs before restart (attempt %d)", backoff, self.restart_count)
            time.sleep(backoff)

            if self._stopping:
                break
            self.process = self._start_process()

    def stop(self) -> None:
        self._stopping = True
        if self.process and self._is_alive():
            logger.info("Stopping watched process...")
            if psutil:
                try:
                    parent = psutil.Process(self.process.pid)
                    for child in parent.children(recursive=True):
                        child.terminate()
                except psutil.NoSuchProcess:
                    pass
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()


def main():
    parser = argparse.ArgumentParser(description="JARVIS AI OS watchdog -- keeps a process alive continuously.")
    parser.add_argument("--command", required=True, help='Command to run, e.g. "python api/rest_server/main.py"')
    parser.add_argument("--cwd", default=None, help="Working directory to run the command from")
    parser.add_argument("--interval", type=float, default=5.0, help="Health-check interval in seconds")
    args = parser.parse_args()

    wd = Watchdog(command=args.command.split(), cwd=args.cwd, check_interval_seconds=args.interval)
    try:
        wd.run_forever()
    except KeyboardInterrupt:
        logger.info("Ctrl+C received, shutting down.")
        wd.stop()


if __name__ == "__main__":
    main()
