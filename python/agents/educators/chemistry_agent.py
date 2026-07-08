"""
educators/chemistry_agent.py
Agent #26: ChemistryAgent -- chemistry tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class ChemistryAgent(BaseEducatorAgent):
    name = "chemistry_agent"
    description = "Tutor agent for chemistry, with a small built-in fact bank."
    agent_id = 26
    subject = "chemistry"
    facts = {
        'ph scale': 'pH ranges 0-14; below 7 is acidic, above 7 is basic, 7 is neutral.',
        "avogadro's number": '6.02214076 x 10^23 particles per mole.',
        'ideal gas law': 'PV = nRT.',
    }
