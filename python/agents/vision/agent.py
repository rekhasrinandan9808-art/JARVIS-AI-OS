"""
vision/agent.py
Agent #16: VisionAgent -- image analysis interface
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import os


class VisionAgent(BaseAgent):
    name = "vision"
    description = (
        "Image analysis interface. Ships with basic image metadata reading; "
        "wire in a real detector (e.g. YOLO via ultralytics) inside detect_objects()."
    )
    agent_id = 16

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("image_info", "Get basic metadata for an image file", {"path": "str"}),
            AgentCapability("detect_objects", "Detect objects in an image (requires a vision model wired in)", {"path": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "image_info":
            path = params["path"]
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            return {"path": path, "size_bytes": os.path.getsize(path)}
        if action == "detect_objects":
            return {
                "error": "No vision model wired in yet. Install ultralytics/YOLO or an ONNX model "
                         "and implement detection here.",
                "path": params.get("path"),
            }
