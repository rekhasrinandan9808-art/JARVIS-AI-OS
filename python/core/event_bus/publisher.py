from .event import Event


class Publisher:

    def __init__(self, bus):
        self.bus = bus

    async def publish(self, event: Event):
        await self.bus.publish(event)