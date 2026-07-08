"""
runtime/scheduler/scheduler.py
Lightweight async scheduler for recurring jobs (e.g. "poll supervisor
health every 30s", "run learning.due_cards every morning at 8am").
No external deps -- for cron-string parsing at scale, swap in APScheduler.
"""

from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger("jarvis.scheduler")


@dataclass
class ScheduledJob:
    name: str
    func: Callable[[], Awaitable[Any]]
    interval_seconds: float
    last_run: Optional[float] = None
    run_count: int = 0
    enabled: bool = True


class Scheduler:
    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False

    def add_job(self, name: str, func: Callable[[], Awaitable[Any]], interval_seconds: float) -> None:
        if name in self._jobs:
            raise ValueError(f"Job '{name}' already scheduled")
        self._jobs[name] = ScheduledJob(name=name, func=func, interval_seconds=interval_seconds)

    def remove_job(self, name: str) -> None:
        self._jobs.pop(name, None)

    def pause_job(self, name: str) -> None:
        if name in self._jobs:
            self._jobs[name].enabled = False

    def resume_job(self, name: str) -> None:
        if name in self._jobs:
            self._jobs[name].enabled = True

    async def _tick(self) -> None:
        now = time.monotonic()
        for job in list(self._jobs.values()):
            if not job.enabled:
                continue
            due = job.last_run is None or (now - job.last_run) >= job.interval_seconds
            if due:
                job.last_run = now
                job.run_count += 1
                try:
                    await job.func()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Scheduled job '%s' raised: %s", job.name, exc)

    async def run_forever(self, tick_interval_seconds: float = 1.0) -> None:
        self._running = True
        logger.info("Scheduler started with %d jobs", len(self._jobs))
        while self._running:
            await self._tick()
            await asyncio.sleep(tick_interval_seconds)

    def stop(self) -> None:
        self._running = False

    def status(self) -> Dict[str, dict]:
        return {
            j.name: {"enabled": j.enabled, "run_count": j.run_count, "interval_seconds": j.interval_seconds}
            for j in self._jobs.values()
        }
