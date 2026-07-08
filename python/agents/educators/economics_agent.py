"""
educators/economics_agent.py
Agent #35: EconomicsAgent -- economics tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class EconomicsAgent(BaseEducatorAgent):
    name = "economics_agent"
    description = "Tutor agent for economics, with a small built-in fact bank."
    agent_id = 35
    subject = "economics"
    facts = {
        'supply and demand': 'Price tends toward the point where quantity supplied equals quantity demanded.',
        'opportunity cost': 'The value of the next-best alternative given up when making a choice.',
    }
