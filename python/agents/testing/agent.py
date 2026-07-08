"""
testing/agent.py
Agent #6: TestingAgent -- runs pytest suites and reports results
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import subprocess


class TestingAgent(BaseAgent):
    name = "testing"
    description = "Runs pytest against a given path and returns pass/fail counts."
    agent_id = 6

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("run_tests", "Run pytest on a path", {"path": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "run_tests":
            path = params["path"]
            try:
                result = subprocess.run(
                    ["python3", "-m", "pytest", path, "-q"],
                    capture_output=True, text=True, timeout=120,
                )
                return {
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-2000:],
                    "stderr_tail": result.stderr[-1000:],
                    "passed": result.returncode == 0,
                }
            except FileNotFoundError:
                return {"error": "pytest not installed in this environment"}
            except subprocess.TimeoutExpired:
                return {"error": "test run timed out"}
