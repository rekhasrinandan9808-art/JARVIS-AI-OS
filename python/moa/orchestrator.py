"""
orchestrator.py
JARVIS OS v2 - PURE ROUTER with Intent Router and Execution Engine
"""

from __future__ import annotations
import logging
import sys
import os
from typing import Any, Dict, List, Optional

_PYTHON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_PYTHON_DIR)
sys.path.insert(0, _PYTHON_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from agents.registry import build_default_registry, AgentRegistry
from agents.base_agent import AgentResult
from runtime.event_router.router import EventRouter
from runtime.state_machine.machine import StateMachine, SystemState
from runtime.process_manager.manager import ProcessManager
from runtime.scheduler.scheduler import Scheduler

# NEW IMPORTS
from moa.intent_router import IntentRouter, Intent
from moa.execution_engine import ExecutionEngine

# FileSystem Agent
try:
    from agents.filesystem.agent import FileSystemAgent
    FILESYSTEM_AVAILABLE = True
except ImportError:
    FILESYSTEM_AVAILABLE = False
    print("⚠️ FileSystemAgent not available")

logger = logging.getLogger("jarvis.orchestrator")


class Orchestrator:
    """
    JARVIS OS v2 Orchestrator - PURE ROUTER.
    
    RULES:
    1. NO intelligence - just routing
    2. NO fallback to LLM for system actions
    3. LLM is ONLY used when IntentRouter says so
    """

    def __init__(self, auto_boot: bool = True):
        self.registry: AgentRegistry = build_default_registry()
        self.events = EventRouter()
        self.state = StateMachine()
        self.process_manager = ProcessManager()
        self.scheduler = Scheduler()
        
        # NEW: Intent Router and Execution Engine
        self.intent_router = IntentRouter()
        self.execution_engine = ExecutionEngine()
        
        # FileSystem Agent
        self.filesystem_agent = None
        if FILESYSTEM_AVAILABLE:
            try:
                self.filesystem_agent = FileSystemAgent()
                logger.info("✅ FileSystemAgent loaded")
            except Exception as e:
                logger.error(f"⚠️ FileSystemAgent init error: {e}")

        # Wire the supervisor agent to the live registry
        supervisor = self.registry.get("supervisor")
        if supervisor is not None:
            supervisor.registry = self.registry

        if auto_boot:
            self.state.transition(SystemState.IDLE, reason="orchestrator init complete")

    async def process(self, text: str) -> AgentResult:
        """
        Process user input through the correct pipeline.
        
        Pipeline:
        1. Route intent (NO LLM for system actions)
        2. Execute system action (NO LLM)
        3. Only use LLM for language tasks
        """
        if not text or not text.strip():
            return AgentResult(
                success=False,
                error="Empty input",
                agent="orchestrator"
            )
        
        # Step 1: Route intent
        intent = self.intent_router.route(text)
        
        # Step 2: Execute based on intent
        return await self._execute_intent(intent)

    async def _execute_intent(self, intent: Intent) -> AgentResult:
        """
        Execute the intent.
        
        RULE: System actions NEVER use LLM.
        """
        capability = intent.capability
        params = intent.params
        
        print(f"[ORCHESTRATOR] Executing: {capability} -> {params}")
        
        # =================================================
        # SYSTEM ACTIONS - REAL OS CALLS (NO LLM)
        # =================================================
        
        # Time
        if capability == "get_time":
            result = self.execution_engine.get_time()
            return AgentResult(
                success=result.get("success", True),
                data=result,
                agent="system"
            )
        
        # Date
        if capability == "get_date":
            result = self.execution_engine.get_date()
            return AgentResult(
                success=result.get("success", True),
                data=result,
                agent="system"
            )
        
        # Weather
        if capability == "weather":
            city = params.get("city", "London")
            result = self.execution_engine.get_weather(city)
            return AgentResult(
                success=result.get("success", False),
                data=result,
                agent="system"
            )
        
        # Location
        if capability == "my_location":
            result = self.execution_engine.get_location()
            return AgentResult(
                success=result.get("success", False),
                data=result,
                agent="system"
            )
        
        # Launch App
        if capability in ["launch_app", "open", "start", "run"]:
            app = params.get("app", "")
            result = self.execution_engine.launch_app(app)
            return AgentResult(
                success=result.get("success", False),
                data=result,
                agent="system"
            )
        
        # Close App
        if capability in ["close_app", "close", "kill", "stop_app"]:
            app = params.get("app", "")
            force = params.get("force", False)
            result = self.execution_engine.close_app(app, force)
            return AgentResult(
                success=result.get("success", False),
                data=result,
                agent="system"
            )
        
        # =================================================
        # LIST APPS
        # =================================================
        if capability == "list_apps":
            result = self.execution_engine.list_installed_apps()
            return AgentResult(
                success=result.get("success", True),
                data=result,
                agent="system"
            )
        
        # =================================================
        # FILESYSTEM ACTIONS
        # =================================================
        if capability == "filesystem":
            if not self.filesystem_agent:
                return AgentResult(
                    success=False,
                    error="FileSystemAgent not available",
                    data={"answer": "⚠️ FileSystemAgent not available"},
                    agent="filesystem"
                )
            
            action = params.get("action", "")
            fs_params = params.get("params", {})
            
            try:
                result = await self.filesystem_agent._run(action, fs_params)
                # Ensure result has answer field for display
                if isinstance(result, dict):
                    if "answer" not in result:
                        if result.get("success"):
                            result["answer"] = result.get("message", f"✅ {action} completed")
                        else:
                            result["answer"] = f"❌ {result.get('error', 'Unknown error')}"
                return AgentResult(
                    success=result.get("success", False),
                    data=result,
                    agent="filesystem"
                )
            except Exception as e:
                logger.error(f"FileSystem error: {e}")
                return AgentResult(
                    success=False,
                    error=str(e),
                    data={"answer": f"❌ FileSystem error: {str(e)}"},
                    agent="filesystem"
                )
        
        # =================================================
        # SUPERVISOR / AGENT ACTIONS
        # =================================================
        if capability in [
            "progress_report", "progress_report_full", "check_all",
            "get_alerts", "get_idle_agents", "get_unhealthy_agents",
            "get_busiest_agent", "get_least_used_agent", "brain_analyze"
        ]:
            return await self._route_to_supervisor(capability, params)
        
        if capability == "check_agent":
            return await self._route_to_supervisor(capability, params)
        
        # =================================================
        # MEMORY ACTIONS
        # =================================================
        if capability in [
            "remember_fact", "recall_fact", "get_all_memory",
            "clear_memory", "remember_name", "get_name", "set_user"
        ]:
            return await self._route_to_memory(capability, params)
        
        # =================================================
        # SEARCH
        # =================================================
        if capability == "search":
            return await self._route_to_search(params)
        
        # =================================================
        # DESKTOP ACTIONS
        # =================================================
        if capability == "desktop":
            action = params.get("action")
            desktop_params = params.get("params", {})
            result = await self._route_to_desktop(action, desktop_params)
            # Ensure result is a dict with success
            if result is None:
                return AgentResult(
                    success=False,
                    error="Desktop workflow returned None",
                    data={"answer": "❌ Desktop operation failed"},
                    agent="system"
                )
            return AgentResult(
                success=result.get("success", False),
                data=result,
                agent="system"
            )
        
        # =================================================
        # LLM (ONLY FOR LANGUAGE TASKS)
        # =================================================
        if capability == "think":
            return await self._route_to_llm(params)
        
        # =================================================
        # UNKNOWN
        # =================================================
        return AgentResult(
            success=False,
            error=f"Unknown capability: {capability}",
            agent="orchestrator"
        )

    async def _route_to_supervisor(self, capability: str, params: Dict) -> AgentResult:
        """Route to supervisor agent."""
        try:
            from agents.supervisor.health_agent import SupervisorAgent
            agent = SupervisorAgent()
            agent.registry = self.registry
            return await agent.execute(capability, params)
        except ImportError as e:
            logger.error(f"Supervisor import error (health_agent): {e}")
            try:
                from agents.supervisor.agent import SupervisorAgent
                agent = SupervisorAgent()
                agent.registry = self.registry
                return await agent.execute(capability, params)
            except ImportError as e2:
                logger.error(f"Supervisor import error (agent): {e2}")
                return AgentResult(
                    success=False,
                    error=f"Supervisor agent not found. Please check the import path.",
                    agent="supervisor"
                )
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            return AgentResult(
                success=False,
                error=f"Supervisor error: {str(e)}",
                agent="supervisor"
            )

    async def _route_to_memory(self, capability: str, params: Dict) -> AgentResult:
        """Route to memory agent."""
        try:
            from agents.memory.agent import MemoryAgent
            agent = MemoryAgent()
            return await agent.execute(capability, params)
        except Exception as e:
            logger.error(f"Memory error: {e}")
            return AgentResult(
                success=False,
                error=f"Memory error: {str(e)}",
                agent="memory"
            )

    async def _route_to_search(self, params: Dict) -> AgentResult:
        """Route to search agent."""
        try:
            from agents.search.agent import SearchAgent
            agent = SearchAgent()
            return await agent.execute("search", params)
        except ImportError:
            try:
                from agents.browser.agent import BrowserAgent
                agent = BrowserAgent()
                return await agent.execute("search", params)
            except Exception as e:
                return AgentResult(
                    success=False,
                    error=f"Search error: {str(e)}",
                    agent="search"
                )
        except Exception as e:
            logger.error(f"Search error: {e}")
            return AgentResult(
                success=False,
                error=f"Search error: {str(e)}",
                agent="search"
            )

    async def _route_to_llm(self, params: Dict) -> AgentResult:
        """Route to LLM agent (ONLY for language tasks)."""
        try:
            from agents.llm.agent import LLMAgent
            agent = LLMAgent()
            return await agent.execute("think", params)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return AgentResult(
                success=False,
                error=f"LLM error: {str(e)}",
                agent="llm"
            )

    async def _route_to_desktop(self, action: str, params: Dict) -> Dict:
        """Route to desktop workflow with comprehensive error handling."""
        try:
            from moa.workflows.desktop_workflow import DesktopWorkflow
            workflow = DesktopWorkflow(self)
            result = await workflow.run(action=action, params=params)
            
            # Defensive check: ensure result is a dict
            if result is None:
                return {
                    "success": False,
                    "error": "Desktop workflow returned None",
                    "answer": "❌ Desktop operation failed"
                }
            
            # Ensure result has 'answer' field
            if isinstance(result, dict) and "answer" not in result:
                if result.get("success"):
                    result["answer"] = f"✅ Desktop: {action} completed"
                else:
                    result["answer"] = f"❌ Desktop error: {result.get('error', 'Unknown')}"
            
            return result
            
        except ImportError as e:
            logger.error(f"Desktop workflow import error: {e}")
            return {
                "success": False,
                "error": "Desktop Controller not available. Install: pip install psutil pyautogui pygetwindow Pillow pycaw screen-brightness-control pywin32",
                "answer": "⚠️ Desktop Controller not available. Please install required packages."
            }
        except Exception as e:
            logger.error(f"Desktop error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "answer": f"❌ Desktop error: {str(e)}"
            }

    # =================================================
    # LEGACY METHODS (Keep for backward compatibility)
    # =================================================

    async def run(self, agent_name: str, action: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        """
        Run a specific agent with a given action and parameters.
        Legacy method - kept for backward compatibility.
        """
        if not self.state.is_operational():
            return AgentResult(
                success=False,
                error=f"System state is '{self.state.state.value}' -- agents cannot run right now.",
                agent=agent_name,
            )

        agent = self.registry.get(agent_name)
        if agent is None:
            return AgentResult(
                success=False,
                error=f"No agent named '{agent_name}'. Available: {self.registry.list_agents()}",
                agent=agent_name,
            )

        logger.info(f"Routing action '{action}' to agent '{agent_name}'")
        print(f"[ORCHESTRATOR] Agent: {agent_name}, Action: {action} (RAW)")
        
        result = await agent.execute(action, params or {})

        topic = "agent.task.completed" if result.success else "agent.task.failed"
        await self.events.publish(topic, result.to_dict(), source=agent_name)

        return result

    async def run_capability(self, action: str, params: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Legacy method - kept for backward compatibility."""
        if not self.state.is_operational():
            return AgentResult(
                success=False,
                error=f"System state is '{self.state.state.value}' -- agents cannot run right now.",
                agent="orchestrator",
            )

        print(f"[ORCHESTRATOR] Looking for agent supporting: '{action}' (RAW)")
        
        agents = self.find_agents_for(action)

        if not agents:
            return AgentResult(
                success=False,
                error=f"No agent supports '{action}'",
                agent="orchestrator",
            )

        agent_name = agents[0]
        logger.info(f"Capability '{action}' routed to agent '{agent_name}'")
        
        return await self.run(agent_name, action, params or {})

    def list_agents(self) -> List[dict]:
        """Get a list of all registered agents."""
        return self.registry.describe_all()

    def health(self) -> List[dict]:
        """Get health status of all agents."""
        return self.registry.health_all()

    def find_agents_for(self, action: str) -> List[str]:
        """Find all agents that support a given capability/action."""
        return self.registry.find_by_capability(action)

    def get_agent(self, agent_name: str):
        """Get a specific agent by name."""
        return self.registry.get(agent_name)

    async def shutdown(self):
        """Gracefully shutdown the orchestrator and all agents."""
        logger.info("Shutting down orchestrator...")
        self.state.transition(SystemState.SHUTTING_DOWN, reason="shutdown requested")
        await self.process_manager.cleanup()
        await self.scheduler.stop()
        self.state.transition(SystemState.SHUTDOWN, reason="shutdown complete")
        logger.info("Orchestrator shutdown complete")

    async def lock(self, reason: str = "manual lock"):
        """Lock the orchestrator."""
        self.state.transition(SystemState.LOCKED, reason=reason)
        logger.info(f"Orchestrator locked: {reason}")

    async def unlock(self, reason: str = "manual unlock"):
        """Unlock the orchestrator."""
        if self.state.state == SystemState.LOCKED:
            self.state.transition(SystemState.IDLE, reason=reason)
            logger.info(f"Orchestrator unlocked: {reason}")
        else:
            logger.warning(f"Orchestrator is not locked (current state: {self.state.state.value})")

    def get_state(self) -> str:
        """Get the current system state."""
        return self.state.state.value

    def is_operational(self) -> bool:
        """Check if the orchestrator is in an operational state."""
        return self.state.is_operational()

    async def broadcast_event(self, topic: str, data: Any, source: str = "orchestrator"):
        """Broadcast an event to all subscribers."""
        await self.events.publish(topic, data, source=source)

    def register_agent(self, agent):
        """Register a new agent dynamically."""
        self.registry.register(agent)
        logger.info(f"Agent '{agent.name}' registered dynamically")

    def unregister_agent(self, agent_name: str):
        """Unregister an agent."""
        self.registry.unregister(agent_name)
        logger.info(f"Agent '{agent_name}' unregistered")

    def get_registry_stats(self) -> Dict[str, int]:
        """Get statistics about the agent registry."""
        agents = self.registry.list_agents()
        capabilities = set()
        for agent_name in agents:
            agent = self.registry.get(agent_name)
            if agent:
                capabilities.update(agent.get_capabilities())
        
        return {
            "total_agents": len(agents),
            "total_capabilities": len(capabilities),
            "state": self.state.state.value
        }

    async def run_multi_capability(self, actions: List[tuple]) -> List[AgentResult]:
        """Run multiple capabilities in sequence."""
        results = []
        for action, params in actions:
            result = await self.run_capability(action, params)
            results.append(result)
            if not result.success:
                break
        return results