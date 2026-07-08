"""
educators/cs_agent.py
Agent #32: CSAgent -- computer science tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class CSAgent(BaseEducatorAgent):
    name = "cs_agent"
    description = "Tutor agent for computer science, with a small built-in fact bank."
    agent_id = 32
    subject = "computer_science"
    facts = {
        'big o notation': "Describes an algorithm's worst-case growth rate relative to input size, e.g. O(n log n).",
        'recursion': 'A function calling itself with a smaller input until it reaches a base case.',
    }
