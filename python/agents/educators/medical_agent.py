"""
educators/medical_agent.py
Agent #37: MedicalAgent -- medical education tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class MedicalAgent(BaseEducatorAgent):
    name = "medical_agent"
    description = "Tutor agent for medical education, with a small built-in fact bank."
    agent_id = 37
    subject = "medical_education"
    facts = {
        'general note': 'This agent provides general educational information only and is not a substitute for professional medical advice, diagnosis, or treatment.',
    }
