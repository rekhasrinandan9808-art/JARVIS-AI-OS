"""
educators/history_agent.py
Agent #28: HistoryAgent -- history tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class HistoryAgent(BaseEducatorAgent):
    name = "history_agent"
    description = "Tutor agent for history, with a small built-in fact bank."
    agent_id = 28
    subject = "history"
    facts = {
        'french revolution': '1789-1799, overthrew the French monarchy, led to the rise of Napoleon.',
        'world war 2': '1939-1945, global conflict between the Allied and Axis powers.',
    }
