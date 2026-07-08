"""
base_agent.py
Every one of the 39 JARVIS agents inherits from BaseAgent.
This is the single contract the orchestrator relies on -- keeping it
uniform is what lets agents be added/removed/hot-swapped without
touching orchestrator code.
"""

from __future__ import annotations
import abc
import asyncio
import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


logger = logging.getLogger("jarvis.agent")


@dataclass
class AgentResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    agent: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "agent": self.agent,
            "duration_ms": self.duration_ms,
        }


@dataclass
class AgentCapability:
    name: str
    description: str
    params: Dict[str, str] = field(default_factory=dict)  # param_name -> type/desc


class BaseAgent(abc.ABC):
    """
    All agents implement `capabilities()` and `_run(task)`.
    Do NOT override `execute()` -- it provides uniform error handling,
    timing, and logging for every agent in the system.
    """

    name: str = "base"
    description: str = "Base agent"
    agent_id: int = 0  # matches numbering in architecture doc

    def __init__(self):
        self._healthy = True
        self._last_error: Optional[str] = None
        self._call_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_duration_ms = 0.0
        self._last_used: Optional[float] = None
        self._last_action: Optional[str] = None

    # ---- required overrides -------------------------------------------------
    @abc.abstractmethod
    def capabilities(self) -> List[AgentCapability]:
        """Return the list of actions this agent supports."""
        raise NotImplementedError

    @abc.abstractmethod
    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        """Actual agent logic. Raise exceptions on failure; execute() wraps them."""
        raise NotImplementedError

    # ---- shared machinery -----------------------------------------------------
    async def execute(self, action: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        params = params or {}
        start = time.perf_counter()
        self._call_count += 1
        self._last_used = time.time()
        self._last_action = action
        try:
            valid_actions = {c.name for c in self.capabilities()}
            if action not in valid_actions:
                raise ValueError(
                    f"Agent '{self.name}' has no action '{action}'. "
                    f"Valid actions: {sorted(valid_actions)}"
                )
            data = await self._run(action, params)
            self._healthy = True
            self._last_error = None
            self._success_count += 1
            duration = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration
            return AgentResult(
                success=True,
                data=data,
                agent=self.name,
                duration_ms=duration,
            )
        except Exception as exc:  # noqa: BLE001 - agents must never crash the orchestrator
            self._healthy = False
            self._last_error = str(exc)
            self._failure_count += 1
            duration = (time.perf_counter() - start) * 1000
            self._total_duration_ms += duration
            logger.error("Agent %s failed on action %s: %s", self.name, action, exc)
            logger.debug(traceback.format_exc())
            return AgentResult(
                success=False,
                error=str(exc),
                agent=self.name,
                duration_ms=duration,
            )

    def _get_voice(self) -> str:
        """Get the voice for this agent."""
        voices = {
            "memory": "Microsoft Zira",
            "browser": "Microsoft David",
            "research": "Microsoft Mark",
            "coding": "Microsoft David",
            "voice": "Microsoft Zira",
            "vision": "Microsoft Mark",
            "supervisor": "Microsoft David",
            "llm": "Microsoft Zira",
            "security": "Microsoft David",
            "networking": "Microsoft Mark",
            "files": "Microsoft David",
            "windows": "Microsoft Mark",
            "linux": "Microsoft David",
            "rag": "Microsoft Zira",
            "learning": "Microsoft Zira",
            "location": "Microsoft Mark",
            "app_controller": "Microsoft David",
            "communications": "Microsoft Zira",
            "translation": "Microsoft Zira",
            "ocr": "Microsoft Mark",
            "plugins": "Microsoft David",
            "supervisor": "Microsoft David",
            "testing": "Microsoft Zira",
            "debugging": "Microsoft David",
            "documentation": "Microsoft Zira",
            "educators": "Microsoft Zira",
            "math_agent": "Microsoft David",
            "physics_agent": "Microsoft Mark",
            "chemistry_agent": "Microsoft Zira",
            "biology_agent": "Microsoft David",
            "history_agent": "Microsoft Mark",
            "geography_agent": "Microsoft Zira",
            "literature_agent": "Microsoft David",
            "philosophy_agent": "Microsoft Mark",
            "cs_agent": "Microsoft Zira",
            "lang_agent": "Microsoft David",
            "art_agent": "Microsoft Zira",
            "economics_agent": "Microsoft Mark",
            "law_agent": "Microsoft David",
            "medical_agent": "Microsoft Zira",
        }
        return voices.get(self.name, "Microsoft David")

    def _get_icon(self) -> str:
        """Get the icon for this agent."""
        icons = {
            "memory": "🧠",
            "browser": "🌐",
            "research": "🔬",
            "coding": "💻",
            "voice": "🎤",
            "vision": "👁️",
            "supervisor": "🛡️",
            "llm": "🧠",
            "security": "🔒",
            "networking": "📡",
            "files": "📁",
            "windows": "🪟",
            "linux": "🐧",
            "rag": "📚",
            "learning": "📖",
            "location": "📍",
            "app_controller": "📱",
            "communications": "📧",
            "translation": "🌍",
            "ocr": "📄",
            "plugins": "🔌",
            "testing": "🧪",
            "debugging": "🐛",
            "documentation": "📝",
            "math_agent": "➗",
            "physics_agent": "⚛️",
            "chemistry_agent": "🧪",
            "biology_agent": "🧬",
            "history_agent": "📜",
            "geography_agent": "🌍",
            "literature_agent": "📚",
            "philosophy_agent": "🤔",
            "cs_agent": "💻",
            "lang_agent": "🗣️",
            "art_agent": "🎨",
            "economics_agent": "💰",
            "law_agent": "⚖️",
            "medical_agent": "🏥",
        }
        return icons.get(self.name, "🤖")

    def _generate_status_message(self) -> str:
        """Generate a spoken status message for this agent."""
        if self._call_count == 0:
            return f"{self.name.capitalize()} agent is ready, waiting for tasks."
        
        status_word = "operational" if self._healthy else "needs attention"
        avg_time = (self._total_duration_ms / self._call_count) if self._call_count else 0
        
        message = f"{self.name.capitalize()} agent {status_word}. "
        message += f"Processed {self._call_count} tasks. "
        
        if self._success_count > 0:
            message += f"{self._success_count} successful. "
        if self._failure_count > 0:
            message += f"{self._failure_count} failures. "
        
        if self._call_count > 0:
            message += f"Average response time {avg_time:.0f} milliseconds."
        
        return message

    def progress(self) -> Dict[str, Any]:
        """Usage/progress metrics for this agent with structured reporting."""
        avg_ms = (self._total_duration_ms / self._call_count) if self._call_count else 0.0
        
        # Build a spoken report message
        status = "healthy" if self._healthy else "unhealthy"
        message = self._generate_status_message()
        
        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "call_count": self._call_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "avg_duration_ms": round(avg_ms, 3),
            "last_action": self._last_action,
            "last_used": self._last_used,
            "healthy": self._healthy,
            "status": status,
            "message": message,
            "voice": self._get_voice(),
            "icon": self._get_icon(),
        }

    def health(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "healthy": self._healthy,
            "last_error": self._last_error,
        }

    def describe(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "agent_id": self.agent_id,
            "description": self.description,
            "capabilities": [
                {"name": c.name, "description": c.description, "params": c.params}
                for c in self.capabilities()
            ],
        }