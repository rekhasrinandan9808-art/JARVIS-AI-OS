"""
educators/lang_agent.py
Agent #33: LangAgent -- language learning tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class LangAgent(BaseEducatorAgent):
    name = "lang_agent"
    description = "Tutor agent for language learning, with a small built-in fact bank."
    agent_id = 33
    subject = "language_learning"
    facts = {
        'subjunctive mood': 'A grammatical mood expressing wishes, doubts, or hypotheticals rather than facts.',
        'false friends': 'Words that look similar across two languages but have different meanings.',
    }
