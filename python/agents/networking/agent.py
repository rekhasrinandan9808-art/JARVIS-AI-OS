"""
networking/agent.py
Agent #12: NetworkingAgent -- basic network diagnostics
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import socket
import subprocess
import platform


class NetworkingAgent(BaseAgent):
    name = "networking"
    description = "Basic network diagnostics: ping, DNS resolution, local IP, port check."
    agent_id = 12

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("ping", "Ping a host", {"host": "str"}),
            AgentCapability("resolve", "Resolve a hostname to IP", {"host": "str"}),
            AgentCapability("local_ip", "Get this machine's local IP", {}),
            AgentCapability("check_port", "Check if a TCP port is open on a host", {"host": "str", "port": "int"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "local_ip":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return {"local_ip": s.getsockname()[0]}
            finally:
                s.close()
        if action == "resolve":
            return {"host": params["host"], "ip": socket.gethostbyname(params["host"])}
        if action == "ping":
            flag = "-n" if platform.system() == "Windows" else "-c"
            result = subprocess.run(
                ["ping", flag, "2", params["host"]], capture_output=True, text=True, timeout=15
            )
            return {"reachable": result.returncode == 0, "output": result.stdout[-800:]}
        if action == "check_port":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            try:
                open_ = sock.connect_ex((params["host"], int(params["port"]))) == 0
                return {"host": params["host"], "port": params["port"], "open": open_}
            finally:
                sock.close()
