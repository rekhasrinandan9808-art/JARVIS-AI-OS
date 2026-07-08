"""
supervisor_workflow.py
Supervisor Workflow - Handles system monitoring commands with STRICT routing
"""

from .base_workflow import BaseWorkflow


class SupervisorWorkflow(BaseWorkflow):
    """Workflow for supervisor/system monitoring commands."""
    
    # STRICT: Define allowed actions explicitly - NO FALLBACKS
    ALLOWED_ACTIONS = {
        "progress_report",
        "progress_report_full",
        "get_alerts",
        "check_all",
        "get_idle_agents",
        "get_unhealthy_agents",
        "get_busiest_agent",
        "get_least_used_agent",
    }

    async def run(self, **kwargs) -> dict:
        """
        Run supervisor workflow with STRICT routing.
        
        CRITICAL: 
        - Validates action against ALLOWED_ACTIONS
        - Passes action AS-IS to orchestrator
        - NO normalization or collapsing
        """
        # Get the action - default to progress_report ONLY if not specified
        action = kwargs.get("action", "progress_report")
        
        print(f"🔧 Supervisor workflow received: {action}")
        
        # STRICT VALIDATION: Check if action is allowed
        if action not in self.ALLOWED_ACTIONS:
            error_msg = f"Unknown supervisor action: '{action}'. Allowed: {sorted(self.ALLOWED_ACTIONS)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "action": action,
                "allowed_actions": sorted(self.ALLOWED_ACTIONS)
            }
        
        # CRITICAL: Pass action AS-IS - NO modification
        result = await self.orchestrator.run_capability(
            action,  # Pass through AS-IS
            kwargs
        )
        
        if hasattr(result, 'data'):
            data = result.data
        else:
            data = result
        
        # Check if the result indicates failure
        if data is None:
            return {
                "success": False,
                "error": "No response from orchestrator"
            }
        
        if isinstance(data, dict) and data.get("success") is False:
            return {
                "success": False,
                "error": data.get("error", "Unknown error")
            }
        
        # Format the result based on action
        return self._format_result(action, data)

    def _format_result(self, action: str, data: dict) -> dict:
        """Format supervisor results for display based on action."""
        if action == "progress_report":
            return self._format_progress_report(data, full=False)
        
        if action == "progress_report_full":
            return self._format_progress_report(data, full=True)
        
        if action == "get_alerts":
            return self._format_alerts(data)
        
        if action == "check_all":
            return self._format_check_all(data)
        
        if action == "get_idle_agents":
            return self._format_idle_agents(data)
        
        if action == "get_unhealthy_agents":
            return self._format_unhealthy(data)
        
        if action == "get_busiest_agent":
            return self._format_busiest(data)
        
        if action == "get_least_used_agent":
            return self._format_least_used(data)
        
        # Fallback - return data as-is
        return data

    def _format_progress_report(self, data: dict, full: bool = False) -> dict:
        """
        Format progress report for display.
        
        CRITICAL: Full mode returns ALL agents with their individual status.
        """
        # Handle case where data might be wrapped
        if "data" in data:
            data = data["data"]
        
        agents = data.get("agents", [])
        total_agents = data.get("total_agents", len(agents))
        healthy = data.get("healthy", 0)
        unhealthy = data.get("unhealthy", 0)
        
        if full:
            # =================================================
            # FULL REPORT - ITERATE THROUGH ALL AGENTS
            # =================================================
            agent_reports = []
            
            # Build detailed per-agent reports
            for agent in agents:
                icon = agent.get("icon", "🤖")
                name = agent.get("agent", "unknown")
                status = agent.get("status", "unknown")
                message = agent.get("message", "No status available")
                
                # Format each agent's report with status
                status_icon = "✅" if status == "healthy" else "⚠️" if status == "idle" else "❌"
                report = f"{icon} {name.capitalize()} Agent: {status_icon} {status.upper()} - {message}"
                agent_reports.append(report)
            
            # Build the full report with ALL agents
            full_report = "\n".join(agent_reports) if agent_reports else "No agent details available."
            
            # Summary line at the top
            summary = f"📊 System Status: {total_agents} agents loaded. {healthy} healthy. {unhealthy} unhealthy."
            
            return {
                "success": True,
                "answer": summary,
                "full_report": full_report,  # Complete with all agents
                "agents": agents,            # Full agent list
                "mode": "full",
                "total_agents": total_agents,
                "healthy": healthy,
                "unhealthy": unhealthy,
                "agent_count": len(agents)   # Explicit count for debugging
            }
        else:
            # =================================================
            # SHORT REPORT - SUMMARY ONLY
            # =================================================
            total_calls = data.get("total_calls", 0)
            success_rate = data.get("success_rate", 0)
            
            summary = f"📊 System Status: {total_agents} agents loaded. {healthy} healthy. "
            summary += f"{unhealthy} unhealthy. Total calls: {total_calls}. "
            summary += f"Success rate: {success_rate:.1f} percent."
            
            return {
                "success": True,
                "answer": summary,
                "agents": agents[:10],  # Show first 10 for preview
                "mode": "short",
                "total_agents": total_agents,
                "healthy": healthy,
                "unhealthy": unhealthy,
                "total_calls": total_calls,
                "success_rate": success_rate
            }

    def _format_alerts(self, data: dict) -> dict:
        """Format alerts with full details."""
        alerts = data.get("alerts", [])
        
        if not alerts:
            return {
                "success": True,
                "answer": "✅ No alerts. All systems healthy.",
                "alerts": []
            }
        
        # Build detailed alert list
        alert_lines = ["⚠️ System Alerts:"]
        for a in alerts:
            agent_name = a.get('agent', 'Unknown')
            error = a.get('error', 'Unknown error')
            alert_lines.append(f"  • {agent_name}: {error}")
        
        alert_text = "\n".join(alert_lines)
        
        return {
            "success": True,
            "answer": f"⚠️ {len(alerts)} alerts found.",
            "alerts": alerts,
            "alert_text": alert_text,
            "alert_count": len(alerts)
        }

    def _format_check_all(self, data: dict) -> dict:
        """Format check all results with details."""
        total = data.get("total", 0)
        healthy = data.get("healthy", 0)
        unhealthy = data.get("unhealthy", 0)
        
        # Build detailed health report
        details = data.get("details", {})
        detail_lines = []
        for agent_name, health in details.items():
            status = "✅" if health.get("healthy", False) else "❌"
            detail_lines.append(f"  {status} {agent_name}: {health.get('message', 'No status')}")
        
        answer = f"🔍 System check complete. {healthy} out of {total} agents healthy. {unhealthy} unhealthy."
        
        return {
            "success": True,
            "answer": answer,
            "total": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "details": details,
            "detail_report": "\n".join(detail_lines) if detail_lines else "No details available."
        }

    def _format_idle_agents(self, data: dict) -> dict:
        """Format idle agents with full list."""
        idle = data.get("idle_agents", [])
        
        if not idle:
            return {
                "success": True,
                "answer": "✅ No idle agents. All agents have been used.",
                "idle_agents": []
            }
        
        # Build full idle list
        idle_list = "\n".join([f"  • {agent}" for agent in idle])
        idle_summary = f"💤 {len(idle)} idle agents: {', '.join(idle[:5])}"
        if len(idle) > 5:
            idle_summary += f" ... and {len(idle) - 5} more"
        
        return {
            "success": True,
            "answer": idle_summary,
            "idle_agents": idle,
            "idle_count": len(idle),
            "idle_list": idle_list  # Full list for display
        }

    def _format_unhealthy(self, data: dict) -> dict:
        """Format unhealthy agents with full details."""
        unhealthy = data.get("unhealthy_agents", [])
        
        if not unhealthy:
            return {
                "success": True,
                "answer": "✅ All agents are healthy.",
                "unhealthy_agents": []
            }
        
        # Build full unhealthy list with errors
        unhealthy_lines = ["❌ Unhealthy Agents:"]
        for u in unhealthy:
            name = u.get("name", "unknown")
            error = u.get("error", "Unknown error")
            unhealthy_lines.append(f"  • {name}: {error}")
        
        return {
            "success": True,
            "answer": f"❌ {len(unhealthy)} unhealthy agents.",
            "unhealthy_agents": unhealthy,
            "unhealthy_count": len(unhealthy),
            "unhealthy_report": "\n".join(unhealthy_lines)
        }

    def _format_busiest(self, data: dict) -> dict:
        """Format busiest agent with details."""
        busiest = data.get("busiest_agent")
        
        if not busiest:
            return {
                "success": True,
                "answer": "📊 No agent usage data available.",
                "busiest_agent": None
            }
        
        name = busiest.get('name', 'Unknown')
        calls = busiest.get('calls', 0)
        rate = busiest.get('success_rate', 0)
        avg_duration = busiest.get('avg_duration_ms', 0)
        
        return {
            "success": True,
            "answer": f"🏆 Busiest agent: {name} with {calls} calls ({rate:.1f}% success rate, avg {avg_duration:.0f}ms).",
            "busiest_agent": busiest
        }

    def _format_least_used(self, data: dict) -> dict:
        """Format least used agent with details."""
        least = data.get("least_used_agent")
        
        if not least:
            return {
                "success": True,
                "answer": "📊 No agent usage data available.",
                "least_used_agent": None
            }
        
        name = least.get('name', 'Unknown')
        calls = least.get('calls', 0)
        rate = least.get('success_rate', 0)
        avg_duration = least.get('avg_duration_ms', 0)
        
        return {
            "success": True,
            "answer": f"🪫 Least used agent: {name} with {calls} calls ({rate:.1f}% success rate, avg {avg_duration:.0f}ms).",
            "least_used_agent": least
        }