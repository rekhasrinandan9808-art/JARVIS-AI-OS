"""
educators/law_agent.py
Agent #36: LawAgent -- law tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class LawAgent(BaseEducatorAgent):
    name = "law_agent"
    description = "Tutor agent for law, with a small built-in fact bank."
    agent_id = 36
    subject = "law"
    facts = {
        'burden of proof': "The obligation to prove a disputed claim; varies by jurisdiction and case type (e.g. 'beyond reasonable doubt' in criminal law).",
    }
