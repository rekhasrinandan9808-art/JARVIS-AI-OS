"""
runtime/event_router/router.py
Async pub/sub event bus. Agents and services publish events (e.g.
"agent.task.completed", "user.voice.detected") and anything can subscribe.
This is what turns 39 isolated agents into one reactive system --
e.g. the supervisor agent subscribes to "agent.task.failed" instead of
being polled constantly.
"""

from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List

logger = logging.getLogger("jarvis.event_router")

Handler = Callable[["Event"], Awaitable[None]]


@dataclass
class Event:
    topic: str
    payload: Any
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)


class EventRouter:
    def __init__(self):
        self._subscribers: Dict[str, List[Handler]] = {}
        self._history: List[Event] = []
        self._history_limit = 500

    def subscribe(self, topic: str, handler: Handler) -> None:
        """topic supports a trailing '*' wildcard, e.g. 'agent.*' matches 'agent.task.completed'."""
        self._subscribers.setdefault(topic, []).append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        if topic in self._subscribers:
            self._subscribers[topic] = [h for h in self._subscribers[topic] if h != handler]

    def _matching_handlers(self, topic: str) -> List[Handler]:
        out: List[Handler] = []
        for pattern, handlers in self._subscribers.items():
            if pattern == topic:
                out.extend(handlers)
            elif pattern.endswith("*") and topic.startswith(pattern[:-1]):
                out.extend(handlers)
        return out

    async def publish(self, topic: str, payload: Any, source: str = "unknown") -> None:
        event = Event(topic=topic, payload=payload, source=source)
        self._history.append(event)
        if len(self._history) > self._history_limit:
            self._history.pop(0)

        handlers = self._matching_handlers(topic)
        if not handlers:
            logger.debug("No subscribers for topic '%s'", topic)
            return

        results = await asyncio.gather(
            *(h(event) for h in handlers), return_exceptions=True
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error("Handler %s for topic '%s' raised: %s", handler, topic, result)

    def recent_events(self, topic_prefix: str = "", limit: int = 50) -> List[Event]:
        events = [e for e in self._history if e.topic.startswith(topic_prefix)]
        return events[-limit:]
