"""
runtime/process_manager/manager.py
Supervises long-running JARVIS services (the REST API, the scheduler loop,
the health monitor, etc). Restarts a service if it dies unexpectedly,
with exponential backoff so a crash loop doesn't spin the CPU.
"""

from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

logger = logging.getLogger("jarvis.process_manager")


@dataclass
class ManagedService:
    name: str
    coro_factory: Callable[[], Awaitable[None]]  # call this to get a fresh coroutine to run
    restart_on_failure: bool = True
    max_backoff_seconds: float = 60.0
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _restart_count: int = 0
    _running: bool = False


class ProcessManager:
    """
    Usage:
        pm = ProcessManager()
        pm.register("scheduler", scheduler_loop)
        pm.register("health_monitor", health_loop)
        await pm.start_all()
        ...
        await pm.stop_all()
    """

    def __init__(self):
        self._services: Dict[str, ManagedService] = {}
        self._stopping = False

    def register(self, name: str, coro_factory: Callable[[], Awaitable[None]], restart_on_failure: bool = True) -> None:
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")
        self._services[name] = ManagedService(name=name, coro_factory=coro_factory, restart_on_failure=restart_on_failure)

    async def _run_with_supervision(self, svc: ManagedService) -> None:
        while not self._stopping:
            svc._running = True
            start = time.monotonic()
            try:
                await svc.coro_factory()
                logger.info("Service '%s' exited cleanly", svc.name)
                svc._running = False
                return
            except asyncio.CancelledError:
                svc._running = False
                raise
            except Exception as exc:  # noqa: BLE001
                svc._running = False
                ran_for = time.monotonic() - start
                logger.error("Service '%s' crashed after %.1fs: %s", svc.name, ran_for, exc)
                if not svc.restart_on_failure or self._stopping:
                    return
                svc._restart_count += 1
                backoff = min(svc.max_backoff_seconds, 2 ** min(svc._restart_count, 6))
                logger.info("Restarting '%s' in %.1fs (attempt %d)", svc.name, backoff, svc._restart_count)
                await asyncio.sleep(backoff)

    async def start_all(self) -> None:
        self._stopping = False
        for svc in self._services.values():
            svc._task = asyncio.create_task(self._run_with_supervision(svc), name=svc.name)
        logger.info("Started %d services: %s", len(self._services), list(self._services.keys()))

    async def start_one(self, name: str) -> None:
        svc = self._services[name]
        svc._task = asyncio.create_task(self._run_with_supervision(svc), name=svc.name)

    async def stop_all(self) -> None:
        self._stopping = True
        for svc in self._services.values():
            if svc._task and not svc._task.done():
                svc._task.cancel()
        await asyncio.gather(
            *(svc._task for svc in self._services.values() if svc._task),
            return_exceptions=True,
        )
        logger.info("All services stopped")

    def status(self) -> Dict[str, dict]:
        return {
            name: {
                "running": svc._running,
                "restart_count": svc._restart_count,
                "done": svc._task.done() if svc._task else None,
            }
            for name, svc in self._services.items()
        }
