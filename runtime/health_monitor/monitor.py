"""
runtime/health_monitor/monitor.py
Periodically checks all agents (via the orchestrator/supervisor agent)
and OS services (via ServiceRegistry), and publishes events on the
EventRouter when something goes unhealthy -- e.g. "system.agent_down".
This is the glue that makes agents/supervisor/health_agent.py actually
proactive instead of only reachable on-demand.
"""

from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from moa.orchestrator import Orchestrator
    from runtime.event_router.router import EventRouter

logger = logging.getLogger("jarvis.health_monitor")


class HealthMonitor:
    def __init__(self, orchestrator: "Orchestrator", event_router: Optional["EventRouter"] = None):
        self.orchestrator = orchestrator
        self.event_router = event_router
        self._last_unhealthy: set[str] = set()

    async def check_once(self) -> dict:
        result = await self.orchestrator.run("supervisor", "check_all", {})
        if not result.success:
            logger.error("Supervisor check_all failed: %s", result.error)
            return {"error": result.error}

        data = result.data
        unhealthy_now = {s["agent"] for s in data["statuses"] if not s["healthy"]}

        newly_unhealthy = unhealthy_now - self._last_unhealthy
        recovered = self._last_unhealthy - unhealthy_now

        if self.event_router:
            for agent_name in newly_unhealthy:
                await self.event_router.publish(
                    "system.agent_down", {"agent": agent_name}, source="health_monitor"
                )
            for agent_name in recovered:
                await self.event_router.publish(
                    "system.agent_recovered", {"agent": agent_name}, source="health_monitor"
                )

        self._last_unhealthy = unhealthy_now
        return data

    async def run_as_job(self) -> None:
        """Designed to be registered with runtime.scheduler.Scheduler.add_job()."""
        await self.check_once()
