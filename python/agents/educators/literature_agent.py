"""
educators/literature_agent.py
Agent #30: LiteratureAgent -- literature tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class LiteratureAgent(BaseEducatorAgent):
    name = "literature_agent"
    description = "Tutor agent for literature, with a small built-in fact bank."
    agent_id = 30
    subject = "literature"
    facts = {
        'iambic pentameter': 'A poetic meter with five iambs (unstressed-stressed syllable pairs) per line, common in Shakespeare.',
        'foreshadowing': 'A literary device hinting at events that will occur later in the narrative.',
    }
