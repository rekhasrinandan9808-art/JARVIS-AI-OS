from abc import ABC, abstractmethod


class BaseWorkflow(ABC):

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    @abstractmethod
    async def run(self, **kwargs):
        pass