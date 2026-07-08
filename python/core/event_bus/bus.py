import asyncio
from collections import defaultdict

from .event import Event


class EventBus:

    def __init__(self):
        self.subscribers = defaultdict(list)
        self.history = []

    def subscribe(self, event_type, subscriber):
        self.subscribers[event_type].append(subscriber)

    async def publish(self, event: Event):

        self.history.append(event)

        if len(self.history) > 100:
            self.history.pop(0)

        tasks = []

        for sub in self.subscribers.get(event.event_type, []):
            tasks.append(sub.handle(event))

        for sub in self.subscribers.get("*", []):
            tasks.append(sub.handle(event))

        if tasks:
            await asyncio.gather(*tasks)