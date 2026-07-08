"""
educators/philosophy_agent.py
Agent #31: PhilosophyAgent -- philosophy tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class PhilosophyAgent(BaseEducatorAgent):
    name = "philosophy_agent"
    description = "Tutor agent for philosophy, with a small built-in fact bank."
    agent_id = 31
    subject = "philosophy"
    facts = {
        'socratic method': 'Teaching through disciplined questioning to expose contradictions and refine understanding.',
        'categorical imperative': "Kant's principle: act only according to maxims you could will to be universal laws.",
    }
