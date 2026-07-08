"""
translation/agent.py
Agent #19: TranslationAgent -- text translation interface
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class TranslationAgent(BaseAgent):
    name = "translation"
    description = (
        "Text translation interface. Wire translate() to a real backend "
        "(Anthropic API, DeepL, Google Translate, or a local NLLB model)."
    )
    agent_id = 19

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("translate", "Translate text to a target language (requires backend wired in)", {"text": "str", "target_lang": "str"}),
            AgentCapability("detect_language", "Detect the language of a text (requires backend wired in)", {"text": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action in ("translate", "detect_language"):
            return {
                "error": "No translation backend wired in yet. Plug in the Anthropic API, DeepL, or a local model.",
                "input": params,
            }
