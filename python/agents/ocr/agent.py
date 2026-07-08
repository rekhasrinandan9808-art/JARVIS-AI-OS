"""
ocr/agent.py
Agent #18: OCRAgent -- optical character recognition
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class OCRAgent(BaseAgent):
    name = "ocr"
    description = "Extracts text from images. Uses pytesseract if installed, otherwise reports how to enable it."
    agent_id = 18

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("extract_text", "Run OCR on an image file", {"path": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "extract_text":
            try:
                import pytesseract  # type: ignore
                from PIL import Image  # type: ignore
            except ImportError:
                return {"error": "pytesseract/Pillow not installed. pip install pytesseract pillow, and install the tesseract binary."}
            img = Image.open(params["path"])
            return {"text": pytesseract.image_to_string(img)}
