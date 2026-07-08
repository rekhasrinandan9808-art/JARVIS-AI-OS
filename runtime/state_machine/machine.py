"""
runtime/state_machine/machine.py
Tracks JARVIS's overall operating mode (booting, idle, listening,
executing, offline/locked-down) and enforces legal transitions so
agents can't run while the system is e.g. mid-shutdown or locked.
"""

from __future__ import annotations
import logging
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

logger = logging.getLogger("jarvis.state_machine")


class SystemState(str, Enum):
    BOOTING = "booting"
    IDLE = "idle"
    LISTENING = "listening"
    EXECUTING = "executing"
    LOCKED = "locked"          # e.g. failed auth, or automatic_offline_mode tripped
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


# Legal transitions -- prevents e.g. jumping straight from BOOTING to EXECUTING,
# or doing anything at all while LOCKED except unlocking.
ALLOWED_TRANSITIONS: Dict[SystemState, Set[SystemState]] = {
    SystemState.BOOTING: {SystemState.IDLE, SystemState.LOCKED, SystemState.OFFLINE},
    SystemState.IDLE: {SystemState.LISTENING, SystemState.EXECUTING, SystemState.LOCKED, SystemState.SHUTTING_DOWN},
    SystemState.LISTENING: {SystemState.IDLE, SystemState.EXECUTING, SystemState.LOCKED},
    SystemState.EXECUTING: {SystemState.IDLE, SystemState.LISTENING, SystemState.LOCKED},
    SystemState.LOCKED: {SystemState.IDLE, SystemState.OFFLINE},  # must explicitly unlock
    SystemState.SHUTTING_DOWN: {SystemState.OFFLINE},
    SystemState.OFFLINE: {SystemState.BOOTING},
}


class StateMachine:
    def __init__(self):
        self._state = SystemState.BOOTING
        self._listeners: List[Callable[[SystemState, SystemState], None]] = []

    @property
    def state(self) -> SystemState:
        return self._state

    def on_transition(self, listener: Callable[[SystemState, SystemState], None]) -> None:
        self._listeners.append(listener)

    def can_transition(self, target: SystemState) -> bool:
        return target in ALLOWED_TRANSITIONS.get(self._state, set())

    def transition(self, target: SystemState, reason: str = "") -> None:
        if not self.can_transition(target):
            raise ValueError(
                f"Illegal transition: {self._state.value} -> {target.value}. "
                f"Allowed from {self._state.value}: {[s.value for s in ALLOWED_TRANSITIONS.get(self._state, set())]}"
            )
        old = self._state
        self._state = target
        logger.info("State transition: %s -> %s (%s)", old.value, target.value, reason or "no reason given")
        for listener in self._listeners:
            listener(old, target)

    def is_operational(self) -> bool:
        """Agents should only be allowed to execute when this is True."""
        return self._state in (SystemState.IDLE, SystemState.LISTENING, SystemState.EXECUTING)
