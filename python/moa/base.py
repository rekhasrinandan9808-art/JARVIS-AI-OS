class BaseWorkflow:

    def __init__(self, registry):
        self.registry = registry

    async def run(self, **kwargs):
        raise NotImplementedError