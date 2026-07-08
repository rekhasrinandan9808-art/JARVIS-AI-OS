import asyncio

from python.core.event_bus import EventBus, Event
from python.core.event_bus.subscriber import Subscriber


class Logger(Subscriber):

    async def handle(self, event):
        print(f"{event.source} -> {event.event_type}")


async def main():

    bus = EventBus()

    logger = Logger()

    bus.subscribe("*", logger)

    await bus.publish(
        Event(
            event_type="agent.started",
            source="planner",
            payload={"task": "Search Google"}
        )
    )

asyncio.run(main())