"""
coding/agent.py
Agent #4: CodingAgent -- writes and syntax-checks code
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import ast
import os


class CodingAgent(BaseAgent):
    name = "coding"
    description = "Writes code files and validates Python syntax before handing off to testing/debugging."
    agent_id = 4

    def __init__(self, workspace: str = "/tmp/jarvis_workspace"):
        super().__init__()
        self.workspace = workspace
        os.makedirs(self.workspace, exist_ok=True)

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("write_file", "Write code to a file in the sandboxed workspace", {"filename": "str", "content": "str"}),
            AgentCapability("check_syntax", "Validate Python syntax", {"code": "str"}),
            AgentCapability("read_file", "Read a file from the workspace", {"filename": "str"}),
        ]

    def _safe_path(self, filename: str) -> str:
        path = os.path.normpath(os.path.join(self.workspace, filename))
        if not path.startswith(os.path.normpath(self.workspace)):
            raise PermissionError("Path escapes sandboxed workspace")
        return path

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "write_file":
            path = self._safe_path(params["filename"])
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(params["content"])
            return {"written": path}
        if action == "read_file":
            path = self._safe_path(params["filename"])
            with open(path) as f:
                return f.read()
        if action == "check_syntax":
            try:
                ast.parse(params["code"])
                return {"valid": True}
            except SyntaxError as e:
                return {"valid": False, "error": str(e), "line": e.lineno}
