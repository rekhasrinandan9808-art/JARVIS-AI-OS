from abc import ABC, abstractmethod
from .event import Event


class Subscriber(ABC):

    @abstractmethod
    async def handle(self, event: Event):
        pass