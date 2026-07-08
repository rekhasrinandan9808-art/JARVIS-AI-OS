"""
educators/physics_agent.py
Agent #25: PhysicsAgent -- physics tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class PhysicsAgent(BaseEducatorAgent):
    name = "physics_agent"
    description = "Tutor agent for physics, with a small built-in fact bank."
    agent_id = 25
    subject = "physics"
    facts = {
        "newton's second law": 'F = m * a: force equals mass times acceleration.',
        'kinetic energy': 'KE = 1/2 * m * v^2.',
        'speed of light': 'c = 299,792,458 m/s in a vacuum.',
    }
