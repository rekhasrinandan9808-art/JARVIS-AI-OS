"""
registry.py
Central place agents are registered. The orchestrator only talks to
this registry -- it never imports individual agent classes -- so
adding agent #40 later means adding one line here, nothing else.
"""

from __future__ import annotations
from typing import Dict, List, Optional

from .base_agent import BaseAgent


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        self._agents[agent.name] = agent

    def get(self, name: str) -> Optional[BaseAgent]:
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        return sorted(self._agents.keys())

    def describe_all(self) -> List[dict]:
        return [a.describe() for a in self._agents.values()]

    def health_all(self) -> List[dict]:
        return [a.health() for a in self._agents.values()]

    def progress_all(self) -> List[dict]:
        return [a.progress() for a in self._agents.values()]

    def find_by_capability(self, action: str) -> List[str]:
        """Which agents support a given action name -- used for routing."""
        out = []
        for a in self._agents.values():
            if any(c.name == action for c in a.capabilities()):
                out.append(a.name)
        return out


def build_default_registry() -> AgentRegistry:
    """
    Build the default agent registry.
    
    Single source of truth: all agents are defined in all_agents.py.
    This function imports that list and registers every agent.
    """
    from .all_agents import REGISTRY_AGENT_CLASSES

    registry = AgentRegistry()
    
    print(f"📡 Registering {len(REGISTRY_AGENT_CLASSES)} agents...")
    
    # Register all agents from all_agents.py
    for cls in REGISTRY_AGENT_CLASSES:
        try:
            agent = cls()
            registry.register(agent)
            agent_id = getattr(agent, 'agent_id', 'N/A')
            print(f"   ✅ {agent.name} (ID: {agent_id})")
        except Exception as e:
            print(f"   ⚠️ Failed to register {cls.__name__}: {e}")
    
    # =================================================
    # Verify all expected agents are registered
    # =================================================
    registered = registry.list_agents()
    print(f"✅ Total agents registered: {len(registered)}")
    
    # List all registered agents for debugging
    if len(registered) > 0:
        print(f"📋 Agents: {', '.join(registered[:10])}" + 
              (f" +{len(registered)-10} more" if len(registered) > 10 else ""))
    
    return registry