"""
educators/art_agent.py
Agent #34: ArtAgent -- art tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class ArtAgent(BaseEducatorAgent):
    name = "art_agent"
    description = "Tutor agent for art, with a small built-in fact bank."
    agent_id = 34
    subject = "art"
    facts = {
        'golden ratio': 'Approximately 1.618, a proportion historically used in composition for perceived aesthetic balance.',
        'complementary colors': 'Colors opposite each other on the color wheel that create strong visual contrast.',
    }
