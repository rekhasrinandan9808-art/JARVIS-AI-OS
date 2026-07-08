"""
admin/agent.py
Agent #22: AdminAgent -- parses admin instructions and checks permissions
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class AdminAgent(BaseAgent):
    name = "admin"
    description = "Parses natural-language admin instructions into structured commands and checks permission levels."
    agent_id = 22

    PERMISSION_LEVELS = {"guest": 0, "user": 1, "trusted": 2, "admin": 3}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("parse_instruction", "Parse an instruction into a structured command", {"instruction": "str"}),
            AgentCapability("check_permission", "Check if a role meets the required level", {"role": "str", "required": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "parse_instruction":
            instr = params["instruction"].strip()
            words = instr.split()
            verb = words[0].lower() if words else ""
            return {"raw": instr, "verb": verb, "args": words[1:]}
        if action == "check_permission":
            role = params["role"]
            required = params["required"]
            role_level = self.PERMISSION_LEVELS.get(role, -1)
            required_level = self.PERMISSION_LEVELS.get(required, 99)
            return {"allowed": role_level >= required_level, "role_level": role_level, "required_level": required_level}
