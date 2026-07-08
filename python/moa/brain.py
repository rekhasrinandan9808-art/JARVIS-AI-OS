"""
moa/brain.py
JARVIS Brain - The decision engine that makes JARVIS intelligent
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("jarvis.brain")


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class BrainDecision:
    """A decision made by the Brain."""
    action: str
    priority: Priority
    reason: str
    confidence: float  # 0.0 - 1.0
    params: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class BrainState:
    """Current state of the system as seen by the Brain."""
    total_agents: int = 0
    healthy_agents: int = 0
    unhealthy_agents: int = 0
    idle_agents: int = 0
    overloaded_agents: int = 0
    agents_with_errors: List[str] = field(default_factory=list)
    agents_needing_attention: List[str] = field(default_factory=list)
    system_stability: str = "stable"  # stable, unstable, critical
    timestamp: str = ""


class Brain:
    """
    JARVIS Brain - Analyzes system state and makes decisions.
    
    The Brain is the core intelligence that:
    1. Reads system state from Supervisor
    2. Analyzes patterns and problems
    3. Makes decisions on what to do
    4. Generates action plans
    5. Provides recommendations
    """
    
    def __init__(self):
        self.state = BrainState()
        self.decision_history: List[BrainDecision] = []
        self.auto_mode = True
        
    def analyze(self, supervisor_data: Dict[str, Any]) -> BrainState:
        """
        Analyze supervisor data and update brain state.
        
        Args:
            supervisor_data: Raw data from supervisor agent
            
        Returns:
            BrainState: Current state analysis
        """
        agents = supervisor_data.get("agents", [])
        
        # Count agent statuses
        healthy = 0
        unhealthy = 0
        idle = 0
        overloaded = 0
        agents_with_errors = []
        agents_needing_attention = []
        
        for agent in agents:
            # Check health
            if agent.get("healthy", False):
                healthy += 1
            else:
                unhealthy += 1
                agents_with_errors.append(agent.get("agent", "unknown"))
            
            # Check if idle
            if agent.get("call_count", 0) == 0:
                idle += 1
            
            # Check if overloaded (more than 100 calls)
            if agent.get("call_count", 0) > 100:
                overloaded += 1
                agents_needing_attention.append(agent.get("agent", "unknown"))
            
            # Check for high failure rate (> 30%)
            calls = agent.get("call_count", 0)
            failures = agent.get("failure_count", 0)
            if calls > 0 and (failures / calls) > 0.3:
                agents_needing_attention.append(agent.get("agent", "unknown"))
        
        # Determine system stability
        if unhealthy > 5:
            stability = "critical"
        elif unhealthy > 2:
            stability = "unstable"
        elif overloaded > 3:
            stability = "unstable"
        else:
            stability = "stable"
        
        # Update brain state
        self.state = BrainState(
            total_agents=len(agents),
            healthy_agents=healthy,
            unhealthy_agents=unhealthy,
            idle_agents=idle,
            overloaded_agents=overloaded,
            agents_with_errors=agents_with_errors,
            agents_needing_attention=agents_needing_attention,
            system_stability=stability,
            timestamp=supervisor_data.get("timestamp", "")
        )
        
        return self.state
    
    def decide(self, state: BrainState) -> BrainDecision:
        """
        Make a decision based on the current state.
        
        This is the core decision logic that makes JARVIS intelligent.
        
        Args:
            state: Current brain state
            
        Returns:
            BrainDecision: The decision made
        """
        # =================================================
        # CRITICAL: Emergency situations
        # =================================================
        if state.unhealthy_agents > 5:
            return BrainDecision(
                action="emergency_response",
                priority=Priority.CRITICAL,
                reason=f"{state.unhealthy_agents} agents are unhealthy! System is in critical state.",
                confidence=1.0,
                params={
                    "unhealthy_agents": state.agents_with_errors,
                    "severity": "critical"
                },
                recommendations=[
                    "Check logs immediately",
                    "Restart unhealthy agents",
                    "Notify system administrator"
                ]
            )
        
        # =================================================
        # HIGH: Problems needing immediate attention
        # =================================================
        if state.unhealthy_agents > 0:
            return BrainDecision(
                action="show_alerts",
                priority=Priority.HIGH,
                reason=f"{state.unhealthy_agents} agents are unhealthy. Showing alerts.",
                confidence=0.95,
                params={"unhealthy_agents": state.agents_with_errors},
                recommendations=[
                    f"Focus on {', '.join(state.agents_with_errors[:3])}",
                    "Check error logs",
                    "Consider restarting affected agents"
                ]
            )
        
        if state.overloaded_agents > 3:
            return BrainDecision(
                action="rebalance_load",
                priority=Priority.HIGH,
                reason=f"{state.overloaded_agents} agents are overloaded. Need to redistribute tasks.",
                confidence=0.9,
                params={"overloaded_agents": state.overloaded_agents},
                recommendations=[
                    "Move tasks to idle agents",
                    "Scale up resources",
                    "Implement load balancing"
                ]
            )
        
        # =================================================
        # MEDIUM: Optimization opportunities
        # =================================================
        if state.idle_agents > 5:
            return BrainDecision(
                action="optimize_idle",
                priority=Priority.MEDIUM,
                reason=f"{state.idle_agents} agents are idle. Could optimize resource usage.",
                confidence=0.8,
                params={"idle_agents": state.idle_agents},
                recommendations=[
                    "Assign pending tasks to idle agents",
                    "Consider scaling down",
                    "Review agent utilization"
                ]
            )
        
        if state.agents_needing_attention:
            return BrainDecision(
                action="review_agents",
                priority=Priority.MEDIUM,
                reason=f"Some agents need attention: {', '.join(state.agents_needing_attention[:3])}",
                confidence=0.7,
                params={"agents": state.agents_needing_attention},
                recommendations=[
                    "Check performance metrics",
                    "Review error rates",
                    "Verify agent health"
                ]
            )
        
        # =================================================
        # LOW: Normal status - just report
        # =================================================
        return BrainDecision(
            action="system_status",
            priority=Priority.LOW,
            reason="All systems operating normally.",
            confidence=1.0,
            params={
                "healthy": state.healthy_agents,
                "total": state.total_agents,
                "idle": state.idle_agents
            },
            recommendations=[
                "System is stable",
                "Monitor for any changes",
                "Continue normal operation"
            ]
        )
    
    def generate_response(self, decision: BrainDecision, state: BrainState) -> str:
        """
        Generate a natural language response based on the decision.
        
        This makes JARVIS sound intelligent and proactive.
        
        Args:
            decision: The decision made
            state: The current state
            
        Returns:
            str: Natural language response
        """
        if decision.action == "emergency_response":
            return (f"⚠️ CRITICAL: {decision.reason} "
                   f"{state.unhealthy_agents} agents are down. "
                   f"Immediate action required. {decision.recommendations[0]}")
        
        if decision.action == "show_alerts":
            errors = ", ".join(state.agents_with_errors[:3])
            if len(state.agents_with_errors) > 3:
                errors += f" and {len(state.agents_with_errors) - 3} more"
            return (f"🔔 Alert: {state.unhealthy_agents} agents need attention. "
                   f"Affected: {errors}. {decision.recommendations[0]}")
        
        if decision.action == "rebalance_load":
            return (f"⚡ Load balancing recommended. {state.overloaded_agents} agents are overloaded. "
                   f"{state.idle_agents} agents are idle. {decision.recommendations[0]}")
        
        if decision.action == "optimize_idle":
            return (f"💡 Optimization opportunity: {state.idle_agents} agents are idle. "
                   f"Consider assigning tasks. {decision.recommendations[0]}")
        
        if decision.action == "review_agents":
            return (f"👀 Agents needing attention: {', '.join(state.agents_needing_attention[:3])}. "
                   f"{decision.recommendations[0]}")
        
        # Default: system_status
        return (f"✅ All systems normal. {state.total_agents} agents loaded. "
               f"{state.healthy_agents} healthy, {state.idle_agents} idle, "
               f"{state.unhealthy_agents} unhealthy.")
    
    async def process(self, supervisor_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full brain processing pipeline.
        
        Args:
            supervisor_data: Raw data from supervisor
            
        Returns:
            Dict: Complete brain analysis with decision and response
        """
        # Step 1: Analyze state
        state = self.analyze(supervisor_data)
        
        # Step 2: Make decision
        decision = self.decide(state)
        
        # Step 3: Generate response
        response = self.generate_response(decision, state)
        
        # Step 4: Store decision history
        self.decision_history.append(decision)
        
        # Step 5: Build complete output
        return {
            "state": {
                "total_agents": state.total_agents,
                "healthy_agents": state.healthy_agents,
                "unhealthy_agents": state.unhealthy_agents,
                "idle_agents": state.idle_agents,
                "overloaded_agents": state.overloaded_agents,
                "stability": state.system_stability,
                "agents_with_errors": state.agents_with_errors[:5],
                "agents_needing_attention": state.agents_needing_attention[:5]
            },
            "decision": {
                "action": decision.action,
                "priority": decision.priority.value,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "recommendations": decision.recommendations[:3]
            },
            "response": response,
            "timestamp": state.timestamp
        }