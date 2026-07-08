"""
app_controller/agent.py
Agent #38: AppControllerAgent -- launches and lists applications on this device
"""

from __future__ import annotations
from typing import Any, Dict, List
import platform
import subprocess
from ..base_agent import BaseAgent, AgentCapability


class AppControllerAgent(BaseAgent):
    name = "app_controller"
    description = (
        "Launches applications already installed on this machine, and lists running "
        "windows/processes. Does NOT silently install software on any device -- app "
        "installation must be an explicit, visible action the device owner initiates."
    )
    agent_id = 38

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("launch_app", "Launch an installed application by command/name", {"command": "str"}),
            AgentCapability("list_running", "List running processes", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "launch_app":
            command = params["command"]
            try:
                subprocess.Popen(command.split())
                return {"launched": command}
            except FileNotFoundError:
                return {"error": "Executable not found: " + command}
        if action == "list_running":
            if platform.system() == "Windows":
                result = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=15)
            else:
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=15)
            return result.stdout.splitlines()
