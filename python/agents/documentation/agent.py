"""
documentation/agent.py
Agent #7: DocumentationAgent -- extracts docstrings/signatures from Python source
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import ast


class DocumentationAgent(BaseAgent):
    name = "documentation"
    description = "Extracts function/class signatures and docstrings from Python source to auto-draft docs."
    agent_id = 7

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("extract", "Extract API surface from Python source", {"code": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "extract":
            tree = ast.parse(params["code"])
            out = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    out.append({
                        "kind": type(node).__name__,
                        "name": node.name,
                        "docstring": ast.get_docstring(node) or "",
                        "line": node.lineno,
                    })
            return out
