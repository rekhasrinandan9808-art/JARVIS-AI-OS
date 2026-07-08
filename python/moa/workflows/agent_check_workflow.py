"""
moa/workflows/agent_check_workflow.py
Agent Check Workflow - Check individual agent status
"""

from .base_workflow import BaseWorkflow


class AgentCheckWorkflow(BaseWorkflow):
    """Workflow for checking individual agent status."""
    
    async def run(self, **kwargs) -> dict:
        """
        Check a specific agent's status.
        
        Args:
            agent_name: The name of the agent to check
        """
        agent_name = kwargs.get("agent_name", "").lower()
        
        if not agent_name:
            return {
                "success": False,
                "error": "No agent name provided",
                "answer": "Please specify which agent to check."
            }
        
        print(f"🔍 Checking agent: {agent_name}")
        
        # First, try to get supervisor data
        supervisor_result = await self.orchestrator.run_capability(
            "progress_report_full",
            {}
        )
        
        if hasattr(supervisor_result, 'data'):
            data = supervisor_result.data
        else:
            data = supervisor_result
        
        if not data or not data.get("success", False):
            return {
                "success": False,
                "error": "Failed to get agent data",
                "answer": f"Unable to check {agent_name} agent."
            }
        
        # Find the agent in the data
        agents = data.get("agents", [])
        found_agent = None
        
        for agent in agents:
            if agent.get("agent", "").lower() == agent_name:
                found_agent = agent
                break
        
        if not found_agent:
            # Check if agent exists in registry
            all_agents = self.orchestrator.list_agents()
            agent_names = [a.get("agent", "").lower() for a in all_agents]
            
            if agent_name in agent_names:
                # Agent exists but might not have data yet
                return {
                    "success": True,
                    "answer": f"🤖 {agent_name.capitalize()} Agent is registered but has no activity yet.",
                    "agent": agent_name,
                    "status": "registered",
                    "message": "No activity recorded yet"
                }
            else:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' not found",
                    "answer": f"❌ Agent '{agent_name}' not found. Use 'agents' to see available agents."
                }
        
        # Build agent status report
        icon = found_agent.get("icon", "🤖")
        name = found_agent.get("agent", "unknown")
        healthy = found_agent.get("healthy", False)
        status = found_agent.get("status", "unknown")
        call_count = found_agent.get("call_count", 0)
        success_count = found_agent.get("success_count", 0)
        failure_count = found_agent.get("failure_count", 0)
        avg_duration = found_agent.get("avg_duration_ms", 0)
        
        # Build status display
        if healthy:
            if call_count == 0:
                status_display = "💤 IDLE"
                message = "Agent is ready and waiting for tasks."
            else:
                status_display = "✅ HEALTHY"
                success_rate = (success_count / call_count * 100) if call_count > 0 else 0
                message = f"{call_count} calls, {success_rate:.0f}% success rate, avg {avg_duration:.0f}ms response time"
        else:
            status_display = "❌ UNHEALTHY"
            last_error = found_agent.get("last_error", "Unknown error")
            message = f"Agent is unhealthy. Last error: {last_error}"
        
        # Build response
        response = f"{icon} {name.capitalize()} Agent: {status_display}\n"
        response += f"📊 {message}"
        
        return {
            "success": True,
            "answer": response,
            "agent": name,
            "status": status,
            "healthy": healthy,
            "call_count": call_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "avg_duration_ms": avg_duration,
            "message": message,
            "mode": "agent_check"
        }