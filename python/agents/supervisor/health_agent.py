"""
supervisor/health_agent.py
Agent #39: SupervisorAgent -- Monitors and reports on all agents with STRICT routing
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent, AgentCapability

logger = logging.getLogger("jarvis.supervisor")


class SupervisorAgent(BaseAgent):
    name = "supervisor"
    description = "Monitors all agents, health, progress, alerts, and healing"
    agent_id = 39

    def __init__(self):
        super().__init__()
        self.registry = None  # Set by orchestrator after init
        
        # STRICT: Define handler mapping - NO FALLBACKS
        self.handlers = {
            "check_all": self._check_all,
            "get_alerts": self._get_alerts,
            "progress_report": lambda: self._progress_report(short=True),
            "progress_report_full": lambda: self._progress_report(short=False),
            "get_idle_agents": self._get_idle_agents,
            "get_unhealthy_agents": self._get_unhealthy_agents,
            "get_busiest_agent": self._get_busiest_agent,
            "get_least_used_agent": self._get_least_used_agent,
            "check_agent": self._check_agent,  # NEW
        }

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("check_all", "Check all agents health", {}),
            AgentCapability("get_alerts", "Get system alerts", {}),
            AgentCapability("progress_report", "Get progress report of all agents (summary)", {}),
            AgentCapability("progress_report_full", "Get detailed per-agent progress report with full status", {}),
            AgentCapability("get_idle_agents", "Get idle agents", {}),
            AgentCapability("get_unhealthy_agents", "Get unhealthy agents", {}),
            AgentCapability("get_busiest_agent", "Get the busiest agent", {}),
            AgentCapability("get_least_used_agent", "Get the least used agent", {}),
            AgentCapability("check_agent", "Check a specific agent's status", {"agent_name": "str"}),  # NEW
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        """
        Execute supervisor action with STRICT routing.
        
        CRITICAL: 
        - Uses strict handler mapping
        - NO fallbacks or default handlers
        - Unknown actions return clear errors
        """
        print(f"[SUPERVISOR] Received action: {action}")
        
        # STRICT VALIDATION: Check if action exists in handlers
        if action not in self.handlers:
            error_msg = f"Unknown supervisor action: '{action}'. Allowed: {sorted(self.handlers.keys())}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "action": action,
                "allowed_actions": sorted(self.handlers.keys())
            }
        
        # Execute the handler
        try:
            handler = self.handlers[action]
            # Pass params to handler if it accepts them
            if action == "check_agent":
                result = handler(params)
            else:
                result = handler()
            
            # Ensure result has success flag
            if isinstance(result, dict) and "success" not in result:
                result["success"] = True
            
            return result
        except Exception as e:
            error_msg = f"Error executing {action}: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "action": action
            }

    def _check_all(self) -> Dict[str, Any]:
        """Check health of all agents."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        agents = self.registry.list_agents()
        results = {}
        
        for name in agents:
            agent = self.registry.get(name)
            if agent:
                health = agent.health()
                results[name] = health
        
        healthy = sum(1 for r in results.values() if r.get("healthy", False))
        
        return {
            "success": True,
            "total": len(results),
            "healthy": healthy,
            "unhealthy": len(results) - healthy,
            "details": results
        }

    def _check_agent(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check a specific agent's status."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        # Get agent name from params
        agent_name = params.get("agent_name") if params else None
        
        if not agent_name:
            return {"success": False, "error": "No agent name provided"}
        
        # Check if agent exists
        if agent_name not in self.registry.list_agents():
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found",
                "answer": f"❌ Agent '{agent_name}' not found. Use 'check all agents' to see available agents."
            }
        
        agent = self.registry.get(agent_name)
        if not agent:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' not found",
                "answer": f"❌ Agent '{agent_name}' not found."
            }
        
        # Get agent info
        health = agent.health()
        progress = agent.progress()
        
        # Determine status
        is_healthy = health.get("healthy", False)
        status = "healthy" if is_healthy else "unhealthy"
        call_count = progress.get("call_count", 0)
        
        # Format response
        icon = self._get_agent_icon(agent_name)
        status_icon = "✅" if is_healthy else "❌"
        
        if call_count == 0:
            message = "No calls yet - ready and waiting"
        else:
            success_rate = (progress.get("success_count", 0) / call_count * 100) if call_count > 0 else 0
            avg_duration = progress.get("avg_duration_ms", 0)
            message = f"{call_count} calls, {success_rate:.0f}% success, avg {avg_duration:.0f}ms"
        
        return {
            "success": True,
            "answer": f"{icon} {agent_name.capitalize()} Agent: {status_icon} {status.upper()} - {message}",
            "agent": agent_name,
            "status": status,
            "healthy": is_healthy,
            "call_count": call_count,
            "message": message,
            "mode": "agent_check"
        }

    def _get_alerts(self) -> Dict[str, Any]:
        """Get system alerts (unhealthy agents)."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        agents = self.registry.list_agents()
        alerts = []
        
        for name in agents:
            agent = self.registry.get(name)
            if agent:
                health = agent.health()
                if not health.get("healthy", False):
                    alerts.append({
                        "agent": name,
                        "error": health.get("last_error", "Unknown error"),
                        "last_error": health.get("last_error")
                    })
        
        return {
            "success": True,
            "alerts": alerts,
            "alert_count": len(alerts),
            "has_alerts": len(alerts) > 0
        }

    def _progress_report(self, short: bool = True) -> Dict[str, Any]:
        """
        Get detailed progress report of all agents.
        
        Args:
            short: If True, return summary only. If False, return full per-agent reports.
        """
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        agents = self.registry.list_agents()
        progress_data = []
        total_calls = 0
        total_success = 0
        total_failed = 0
        total_duration = 0.0
        healthy_count = 0
        
        for name in agents:
            agent = self.registry.get(name)
            if agent:
                progress = agent.progress()
                health = agent.health()
                
                # =================================================
                # CRITICAL: Add status field for each agent
                # =================================================
                # Determine agent status
                if health.get("healthy", False):
                    status = "healthy"
                else:
                    status = "unhealthy"
                
                # Add status and other useful fields to progress
                progress["status"] = status
                progress["healthy"] = health.get("healthy", False)
                progress["last_error"] = health.get("last_error", None)
                progress["icon"] = self._get_agent_icon(name)
                
                progress_data.append(progress)
                
                total_calls += progress.get("call_count", 0)
                total_success += progress.get("success_count", 0)
                total_failed += progress.get("failure_count", 0)
                total_duration += progress.get("avg_duration_ms", 0) * progress.get("call_count", 0)
                
                if progress.get("healthy", False):
                    healthy_count += 1
        
        avg_duration = (total_duration / total_calls) if total_calls > 0 else 0
        
        # Sort by call count (busiest first)
        progress_data.sort(key=lambda x: x.get("call_count", 0), reverse=True)
        
        if short:
            summary_message = f"System Status. {len(agents)} agents loaded. {healthy_count} healthy. "
            summary_message += f"{len(agents) - healthy_count} unhealthy. Total calls: {total_calls}. "
            summary_message += f"Success rate: {(total_success / total_calls * 100) if total_calls > 0 else 0:.1f} percent."
            
            return {
                "success": True,
                "summary": summary_message,
                "total_agents": len(agents),
                "healthy": healthy_count,
                "unhealthy": len(agents) - healthy_count,
                "total_calls": total_calls,
                "success_rate": (total_success / total_calls * 100) if total_calls > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "agents": progress_data[:5],
                "mode": "short"
            }
        else:
            # =================================================
            # FULL REPORT - All agents with complete data
            # =================================================
            return {
                "success": True,
                "total_agents": len(agents),
                "healthy": healthy_count,
                "unhealthy": len(agents) - healthy_count,
                "total_calls": total_calls,
                "success_rate": (total_success / total_calls * 100) if total_calls > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "agents": progress_data,  # Now includes status, healthy, icon, etc.
                "mode": "full"
            }

    def _get_agent_icon(self, agent_name: str) -> str:
        """Get icon for agent."""
        icons = {
            "memory": "🧠",
            "browser": "🌐",
            "voice": "🎤",
            "vision": "👁️",
            "llm": "🤖",
            "supervisor": "🔧",
            "search": "🔍",
            "weather": "🌤️",
            "location": "📍",
            "code": "💻",
            "translation": "🔤",
            "research": "📚",
            "rag": "📄",
            "api": "🔌",
            "database": "🗄️",
            "file": "📁",
            "image": "🖼️",
            "video": "🎬",
            "audio": "🎵",
            "speech": "🗣️",
            "text": "📝",
            "math": "📐",
            "logic": "🧩",
            "planning": "📋",
            "scheduler": "⏰",
            "monitor": "📊",
            "logger": "📝",
            "cache": "💾",
            "config": "⚙️",
            "security": "🔒",
            "auth": "🔑",
            "network": "🌐",
            "storage": "💿",
            "compute": "⚡",
            "analytics": "📈",
            "reporting": "📊",
            "dashboard": "📉",
            "alert": "🔔",
            "notification": "📢",
            "admin": "👑",
            "app_controller": "🎮",
            "art_agent": "🎨",
            "biology_agent": "🧬",
            "chemistry_agent": "⚗️",
            "physics_agent": "⚛️",
            "math_agent": "📐",
            "history_agent": "📜",
            "geography_agent": "🌍",
            "literature_agent": "📖",
            "philosophy_agent": "💭",
            "cs_agent": "💻",
            "lang_agent": "🗣️",
            "economics_agent": "💰",
            "law_agent": "⚖️",
            "medical_agent": "🏥",
            "coding": "💻",
            "debugging": "🐛",
            "testing": "🧪",
            "documentation": "📝",
            "files": "📁",
            "windows": "🪟",
            "linux": "🐧",
            "networking": "🌐",
            "robotics": "🤖",
            "iot": "📡",
            "plugins": "🔌",
            "learning": "📚",
            "communications": "📡",
            "ocr": "👁️",
        }
        return icons.get(agent_name, "🤖")

    def _get_idle_agents(self) -> Dict[str, Any]:
        """Get agents that haven't been used."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        idle = []
        agents = self.registry.list_agents()
        
        for name in agents:
            agent = self.registry.get(name)
            if agent:
                progress = agent.progress()
                if progress.get("call_count", 0) == 0:
                    idle.append(name)
        
        return {
            "success": True,
            "idle_agents": idle,
            "idle_count": len(idle)
        }

    def _get_unhealthy_agents(self) -> Dict[str, Any]:
        """Get unhealthy agents."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        unhealthy = []
        agents = self.registry.list_agents()
        
        for name in agents:
            agent = self.registry.get(name)
            if agent:
                health = agent.health()
                if not health.get("healthy", False):
                    unhealthy.append({
                        "name": name,
                        "error": health.get("last_error", "Unknown")
                    })
        
        return {
            "success": True,
            "unhealthy_agents": unhealthy,
            "unhealthy_count": len(unhealthy)
        }

    def _get_busiest_agent(self) -> Dict[str, Any]:
        """Get the busiest agent."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        busiest = None
        max_calls = 0
        
        for name in self.registry.list_agents():
            agent = self.registry.get(name)
            if agent:
                progress = agent.progress()
                calls = progress.get("call_count", 0)
                if calls > max_calls:
                    max_calls = calls
                    busiest = {
                        "name": name,
                        "calls": calls,
                        "success_rate": (progress.get("success_count", 0) / calls * 100) if calls > 0 else 0,
                        "avg_duration_ms": progress.get("avg_duration_ms", 0)
                    }
        
        return {
            "success": True,
            "busiest_agent": busiest
        }

    def _get_least_used_agent(self) -> Dict[str, Any]:
        """Get the least used agent (excluding idle)."""
        if not self.registry:
            return {"success": False, "error": "Registry not set"}
        
        least_used = None
        min_calls = float('inf')
        
        for name in self.registry.list_agents():
            agent = self.registry.get(name)
            if agent:
                progress = agent.progress()
                calls = progress.get("call_count", 0)
                if 0 < calls < min_calls:
                    min_calls = calls
                    least_used = {
                        "name": name,
                        "calls": calls,
                        "success_rate": (progress.get("success_count", 0) / calls * 100) if calls > 0 else 0,
                        "avg_duration_ms": progress.get("avg_duration_ms", 0)
                    }
        
        return {
            "success": True,
            "least_used_agent": least_used
        }