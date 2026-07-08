from agents.registry import AgentRegistry


class Commander:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def execute(self, action: str, params: dict):

        agents = self.registry.find_by_capability(action)

        if not agents:
            raise RuntimeError(f"No agent supports '{action}'")

        agent = self.registry.get(agents[0])

        return await agent.execute(action, params)