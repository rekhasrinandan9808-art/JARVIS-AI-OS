from moa.workflows.research_workflow import ResearchWorkflow
from moa.workflows.browser_workflow import BrowserWorkflow
from moa.workflows.coding_workflow import CodingWorkflow
from moa.workflows.voice_workflow import VoiceWorkflow
from moa.workflows.llm_workflow import LLMWorkflow
from moa.workflows.supervisor_workflow import SupervisorWorkflow
from moa.workflows.brain_workflow import BrainWorkflow
from moa.workflows.agent_check_workflow import AgentCheckWorkflow
from moa.workflows.memory_workflow import MemoryWorkflow
from moa.workflows.launch_workflow import LaunchWorkflow
from moa.workflows.close_workflow import CloseWorkflow
from moa.workflows.time_workflow import TimeWorkflow
from moa.workflows.date_workflow import DateWorkflow
from moa.workflows.desktop_workflow import DesktopWorkflow  # NEW


class WorkflowRegistry:

    def __init__(self, orchestrator):
        self.workflows = {
            # Research & Browser
            "research": ResearchWorkflow(orchestrator),
            "browser": BrowserWorkflow(orchestrator),
            "search": BrowserWorkflow(orchestrator),
            "fetch": BrowserWorkflow(orchestrator),
            "plan": ResearchWorkflow(orchestrator),
            
            # Coding
            "coding": CodingWorkflow(orchestrator),
            
            # Voice
            "voice": VoiceWorkflow(orchestrator),
            "speak": VoiceWorkflow(orchestrator),
            "listen": VoiceWorkflow(orchestrator),
            "say_and_listen": VoiceWorkflow(orchestrator),
            "transcribe": VoiceWorkflow(orchestrator),
            
            # LLM
            "llm": LLMWorkflow(orchestrator),
            "think": LLMWorkflow(orchestrator),
            "chat": LLMWorkflow(orchestrator),
            
            # Supervisor
            "supervisor": SupervisorWorkflow(orchestrator),
            "progress_report": SupervisorWorkflow(orchestrator),
            "progress_report_full": SupervisorWorkflow(orchestrator),
            "check_all": SupervisorWorkflow(orchestrator),
            "get_alerts": SupervisorWorkflow(orchestrator),
            "get_idle_agents": SupervisorWorkflow(orchestrator),
            "get_unhealthy_agents": SupervisorWorkflow(orchestrator),
            "get_busiest_agent": SupervisorWorkflow(orchestrator),
            "get_least_used_agent": SupervisorWorkflow(orchestrator),
            
            # Brain
            "brain_analyze": BrainWorkflow(orchestrator),
            
            # Agent Check
            "check_agent": AgentCheckWorkflow(orchestrator),
            
            # Memory
            "remember_fact": MemoryWorkflow(orchestrator),
            "recall_fact": MemoryWorkflow(orchestrator),
            "get_all_memory": MemoryWorkflow(orchestrator),
            "remember_facts": MemoryWorkflow(orchestrator),
            "remember_name": MemoryWorkflow(orchestrator),
            "get_name": MemoryWorkflow(orchestrator),
            "set_user": MemoryWorkflow(orchestrator),
            "clear_memory": MemoryWorkflow(orchestrator),
            
            # Advanced Memory
            "add_conversation": MemoryWorkflow(orchestrator),
            "search_conversations": MemoryWorkflow(orchestrator),
            "learn_preference": MemoryWorkflow(orchestrator),
            "get_preference": MemoryWorkflow(orchestrator),
            "get_all_preferences": MemoryWorkflow(orchestrator),
            "get_context": MemoryWorkflow(orchestrator),
            "get_stats": MemoryWorkflow(orchestrator),
            
            # Launch
            "launch_app": LaunchWorkflow(orchestrator),
            "open": LaunchWorkflow(orchestrator),
            "start": LaunchWorkflow(orchestrator),
            "run": LaunchWorkflow(orchestrator),
            
            # Close
            "close_app": CloseWorkflow(orchestrator),
            "close": CloseWorkflow(orchestrator),
            "kill": CloseWorkflow(orchestrator),
            "stop_app": CloseWorkflow(orchestrator),
            
            # Time & Date
            "get_time": TimeWorkflow(orchestrator),
            "get_date": DateWorkflow(orchestrator),
            "time": TimeWorkflow(orchestrator),
            "date": DateWorkflow(orchestrator),
            
            # Desktop - NEW
            "desktop": DesktopWorkflow(orchestrator),
            "desktop_agent": DesktopWorkflow(orchestrator),
        }

    def get(self, capability):
        """
        Get a workflow by capability name.
        
        Args:
            capability: The capability name (e.g., "research", "search", "fetch")
            
        Returns:
            The workflow instance or None if not found
        """
        return self.workflows.get(capability)

    def register(self, capability, workflow):
        """
        Register a new workflow dynamically.
        
        Args:
            capability: The capability name
            workflow: The workflow instance
        """
        self.workflows[capability] = workflow

    def unregister(self, capability):
        """
        Unregister a workflow.
        
        Args:
            capability: The capability name to remove
        """
        if capability in self.workflows:
            del self.workflows[capability]

    def list_workflows(self):
        """
        List all registered workflows.
        
        Returns:
            List[str]: List of capability names
        """
        return list(self.workflows.keys())

    def has(self, capability):
        """
        Check if a workflow exists for a capability.
        
        Args:
            capability: The capability name
            
        Returns:
            bool: True if workflow exists, False otherwise
        """
        return capability in self.workflows