"""
educators/geography_agent.py
Agent #29: GeographyAgent -- geography tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class GeographyAgent(BaseEducatorAgent):
    name = "geography_agent"
    description = "Tutor agent for geography, with a small built-in fact bank."
    agent_id = 29
    subject = "geography"
    facts = {
        'continents': 'Africa, Antarctica, Asia, Australia, Europe, North America, South America.',
        'longest river': 'The Nile and the Amazon are generally cited as the two longest rivers, depending on measurement method.',
    }
