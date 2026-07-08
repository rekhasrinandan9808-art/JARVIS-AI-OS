"""
learning/agent.py
Agent #20: LearningAgent -- spaced-repetition scheduling (SM-2 algorithm)
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


from datetime import datetime, timedelta


class LearningAgent(BaseAgent):
    name = "learning"
    description = "Implements the SM-2 spaced-repetition algorithm to schedule review of learned material."
    agent_id = 20

    def __init__(self):
        super().__init__()
        self._cards: Dict[str, Dict[str, Any]] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("add_card", "Add a new flashcard/topic to track", {"card_id": "str", "content": "str"}),
            AgentCapability("review", "Record a review with quality 0-5 (SM-2)", {"card_id": "str", "quality": "int"}),
            AgentCapability("due_cards", "List cards due for review today", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "add_card":
            self._cards[params["card_id"]] = {
                "content": params["content"], "ef": 2.5, "interval": 0, "reps": 0,
                "due": datetime.utcnow().isoformat(),
            }
            return {"added": params["card_id"]}
        if action == "review":
            card = self._cards[params["card_id"]]
            q = int(params["quality"])
            if q < 3:
                card["reps"] = 0
                card["interval"] = 1
            else:
                card["reps"] += 1
                if card["reps"] == 1:
                    card["interval"] = 1
                elif card["reps"] == 2:
                    card["interval"] = 6
                else:
                    card["interval"] = round(card["interval"] * card["ef"])
                card["ef"] = max(1.3, card["ef"] + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
            card["due"] = (datetime.utcnow() + timedelta(days=card["interval"])).isoformat()
            return card
        if action == "due_cards":
            now = datetime.utcnow().isoformat()
            return [cid for cid, c in self._cards.items() if c["due"] <= now]
