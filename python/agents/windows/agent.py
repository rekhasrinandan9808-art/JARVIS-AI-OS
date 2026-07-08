"""
windows/agent.py
Agent #10: WindowsAgent -- Windows-specific OS operations
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import platform
import subprocess


class WindowsAgent(BaseAgent):
    name = "windows"
    description = "Runs Windows-specific shell commands (services, processes, registry queries)."
    agent_id = 10

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("list_processes", "List running processes", {}),
            AgentCapability("run_powershell", "Run a PowerShell command (Windows only)", {"command": "str"}),
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
            if platform.system() != "Windows":
                return {"error": "list_processes requires Windows; this host is " + platform.system()}
            result = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=15)
            return result.stdout.splitlines()
        if action == "run_powershell":
            if platform.system() != "Windows":
                return {"error": "PowerShell requires Windows; this host is " + platform.system()}
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", params["command"]],
                capture_output=True, text=True, timeout=30,
            )
            return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
