"""
educators/base_educator.py
Shared base for the 14 subject-tutor agents (#24-37). Each subject agent
supplies a small fact/formula bank and a difficulty-scaled explain() --
swap explain() for a real LLM call for open-ended tutoring.
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class BaseEducatorAgent(BaseAgent):
    subject = "general"
    facts: Dict[str, str] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("explain", "Explain a topic in this subject", {"topic": "str", "level": "str"}),
            AgentCapability("list_topics", "List topics this agent has canned facts for", {}),
            AgentCapability("quiz_question", "Generate a simple quiz question for a topic", {"topic": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "list_topics":
            return list(self.facts.keys())
        if action == "explain":
            topic = params["topic"]
            level = params.get("level", "beginner")
            fact = self.facts.get(topic.lower())
            if fact:
                return {"subject": self.subject, "topic": topic, "level": level, "explanation": fact}
            return {
                "subject": self.subject, "topic": topic, "level": level,
                "explanation": None,
                "note": "No canned fact for this topic -- wire this agent to an LLM call for open-ended tutoring.",
            }
        if action == "quiz_question":
            topic = params["topic"]
            fact = self.facts.get(topic.lower(), "(no data yet)")
            return {"question": "What do you know about '" + topic + "' in " + self.subject + "?", "hint": fact}
