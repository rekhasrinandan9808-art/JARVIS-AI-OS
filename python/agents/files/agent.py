"""
files/agent.py
Agent #9: FilesAgent -- sandboxed filesystem operations
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import os
import shutil


class FilesAgent(BaseAgent):
    name = "files"
    description = "Reads, writes, lists, and deletes files inside a sandboxed root directory."
    agent_id = 9

    def __init__(self, root: str = "/tmp/jarvis_files"):
        super().__init__()
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def _safe(self, path: str) -> str:
        full = os.path.normpath(os.path.join(self.root, path.lstrip("/\\")))
        if not full.startswith(os.path.normpath(self.root)):
            raise PermissionError("Path escapes sandboxed root")
        return full

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("list", "List directory contents", {"path": "str"}),
            AgentCapability("read", "Read a file", {"path": "str"}),
            AgentCapability("write", "Write a file", {"path": "str", "content": "str"}),
            AgentCapability("delete", "Delete a file", {"path": "str"}),
            AgentCapability("move", "Move/rename a file", {"src": "str", "dst": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "list":
            p = self._safe(params.get("path", "."))
            return os.listdir(p)
        if action == "read":
            with open(self._safe(params["path"])) as f:
                return f.read()
        if action == "write":
            p = self._safe(params["path"])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as f:
                f.write(params["content"])
            return {"written": p}
        if action == "delete":
            os.remove(self._safe(params["path"]))
            return {"deleted": params["path"]}
        if action == "move":
            shutil.move(self._safe(params["src"]), self._safe(params["dst"]))
            return {"moved_to": params["dst"]}
