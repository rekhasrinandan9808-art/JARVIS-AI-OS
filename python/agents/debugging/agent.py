"""
debugging/agent.py
Agent #5: DebuggingAgent -- parses tracebacks and suggests causes
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import re


class DebuggingAgent(BaseAgent):
    name = "debugging"
    description = "Parses Python tracebacks to extract the failing file/line/exception type."
    agent_id = 5

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("parse_traceback", "Extract structured info from a traceback string", {"traceback": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "parse_traceback":
            tb = params["traceback"]
            frames = re.findall(r'File "([^"]+)", line (\d+), in (\S+)', tb)
            last_line = tb.strip().splitlines()[-1] if tb.strip() else ""
            exc_match = re.match(r"(\w+(\.\w+)*Error|\w+Exception)\s*:\s*(.*)", last_line)
            return {
                "frames": [{"file": f, "line": int(l), "function": fn} for f, l, fn in frames],
                "exception_type": exc_match.group(1) if exc_match else None,
                "message": exc_match.group(3) if exc_match else last_line,
            }
