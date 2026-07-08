"""
educators/biology_agent.py
Agent #27: BiologyAgent -- biology tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class BiologyAgent(BaseEducatorAgent):
    name = "biology_agent"
    description = "Tutor agent for biology, with a small built-in fact bank."
    agent_id = 27
    subject = "biology"
    facts = {
        'photosynthesis': 'Plants convert CO2 + H2O + light energy into glucose + O2.',
        'dna': 'DNA is a double helix carrying genetic instructions via base pairs A-T and C-G.',
        'mitosis': 'Cell division producing two genetically identical daughter cells.',
    }
