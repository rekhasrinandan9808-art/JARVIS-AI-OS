"""
linux/agent.py
Agent #11: LinuxAgent -- Linux-specific OS operations
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import platform
import subprocess


class LinuxAgent(BaseAgent):
    name = "linux"
    description = "Runs Linux-specific shell commands (services, processes, systemctl)."
    agent_id = 11

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("list_processes", "List running processes via ps", {}),
            AgentCapability("run_shell", "Run a shell command", {"command": "str"}),
            AgentCapability("system_info", "Return basic OS info", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "system_info":
            return {
                "os": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
            }
        if action == "list_processes":
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=15)
            return result.stdout.splitlines()
        if action == "run_shell":
            # Deliberately no shell=True and no arbitrary shell metacharacters --
            # route through the sandbox layer in production, this is a dev-mode agent.
            result = subprocess.run(
                params["command"].split(), capture_output=True, text=True, timeout=30
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
