"""
educators/math_agent.py
Agent #24: MathAgent -- math tutor agent
"""

from __future__ import annotations
from typing import Any, Dict, List
from .base_educator import BaseEducatorAgent


class MathAgent(BaseEducatorAgent):
    name = "math_agent"
    description = "Tutor agent for math, with a small built-in fact bank."
    agent_id = 24
    subject = "math"
    facts = {
        'pythagorean theorem': 'a^2 + b^2 = c^2 for a right triangle with legs a, b and hypotenuse c.',
        'derivative': 'The derivative measures the instantaneous rate of change of a function.',
        'quadratic formula': 'x = (-b +/- sqrt(b^2 - 4ac)) / 2a solves ax^2+bx+c=0.',
    }
