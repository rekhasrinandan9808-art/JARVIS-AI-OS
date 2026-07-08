"""
moa/performance_monitor.py
Agent Performance Monitoring - Tracks response times, success rates, resource usage
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict, deque
import json
import logging

logger = logging.getLogger("jarvis.performance_monitor")


class PerformanceMonitor:
    """Track agent performance metrics."""
    
    def __init__(self):
        # Store performance data
        self.agent_stats: Dict[str, Dict] = defaultdict(lambda: {
            "calls": 0,
            "success": 0,
            "failures": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "recent_times": deque(maxlen=100),
            "last_error": None,
            "last_call": None,
            "health_score": 100
        })
        self.system_metrics = {
            "cpu": [],
            "memory": [],
            "disk": [],
            "network": []
        }
        self.alert_thresholds = {
            "max_response_time": 5.0,  # seconds
            "failure_rate": 0.3,  # 30%
            "min_health_score": 70
        }
        self._running = False
        self._monitor_thread = None
    
    def record_call(self, agent_name: str, success: bool, duration: float, error: str = None):
        """Record a call to an agent."""
        stats = self.agent_stats[agent_name]
        stats["calls"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["failures"] += 1
            stats["last_error"] = error
        
        stats["total_time"] += duration
        stats["recent_times"].append(duration)
        stats["avg_time"] = stats["total_time"] / stats["calls"]
        if duration < stats["min_time"]:
            stats["min_time"] = duration
        if duration > stats["max_time"]:
            stats["max_time"] = duration
        stats["last_call"] = datetime.now().isoformat()
        
        # Update health score
        self._update_health_score(agent_name)
    
    def _update_health_score(self, agent_name: str):
        """Calculate health score for an agent."""
        stats = self.agent_stats[agent_name]
        score = 100
        
        # Failure rate penalty
        if stats["calls"] > 0:
            failure_rate = stats["failures"] / stats["calls"]
            if failure_rate > 0.1:
                score -= failure_rate * 50  # Up to 50 points penalty
        
        # Response time penalty
        if stats["avg_time"] > 2.0:
            score -= (stats["avg_time"] - 2.0) * 10
        
        # Recent failures penalty
        if stats["recent_times"]:
            recent_failures = sum(1 for t in stats["recent_times"] if t > self.alert_thresholds["max_response_time"])
            if recent_failures > 0:
                score -= recent_failures * 5
        
        stats["health_score"] = max(0, min(100, score))
    
    def get_stats(self, agent_name: str = None) -> Dict:
        """Get performance statistics."""
        if agent_name:
            return self.agent_stats.get(agent_name, {})
        return dict(self.agent_stats)
    
    def get_health_report(self) -> Dict:
        """Get comprehensive health report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "agents": {},
            "summary": {
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "total": len(self.agent_stats)
            },
            "system": self._get_system_metrics()
        }
        
        for name, stats in self.agent_stats.items():
            health = stats.get("health_score", 100)
            status = "healthy"
            if health < 50:
                status = "critical"
                report["summary"]["critical"] += 1
            elif health < 70:
                status = "warning"
                report["summary"]["warning"] += 1
            else:
                report["summary"]["healthy"] += 1
            
            report["agents"][name] = {
                "health_score": health,
                "status": status,
                "calls": stats.get("calls", 0),
                "success_rate": stats.get("success", 0) / max(1, stats.get("calls", 1)),
                "avg_response_time": stats.get("avg_time", 0),
                "last_error": stats.get("last_error"),
                "last_call": stats.get("last_call")
            }
        
        return report
    
    def _get_system_metrics(self) -> Dict:
        """Get system metrics."""
        return {
            "cpu": psutil.cpu_percent(interval=0.5),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent,
            "processes": len(psutil.process_iter())
        }
    
    def start_monitoring(self, interval: int = 30):
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        logger.info(f"Performance monitoring started (interval: {interval}s)")
    
    def _monitor_loop(self, interval: int):
        """Background monitoring loop."""
        while self._running:
            try:
                # Check for alerts
                alerts = self._check_alerts()
                if alerts:
                    for alert in alerts:
                        logger.warning(f"🔔 Performance Alert: {alert}")
                        self._trigger_alert(alert)
                
                # Collect system metrics
                self.system_metrics["cpu"].append(psutil.cpu_percent())
                self.system_metrics["memory"].append(psutil.virtual_memory().percent)
                if len(self.system_metrics["cpu"]) > 100:
                    self.system_metrics["cpu"].pop(0)
                    self.system_metrics["memory"].pop(0)
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            time.sleep(interval)
    
    def _check_alerts(self) -> List[str]:
        """Check for alerts."""
        alerts = []
        
        for name, stats in self.agent_stats.items():
            health = stats.get("health_score", 100)
            if health < 50:
                alerts.append(f"Agent '{name}' is CRITICAL (health: {health})")
            elif health < 70:
                alerts.append(f"Agent '{name}' is WARNING (health: {health})")
            
            # Check for recent failures
            if stats.get("failures", 0) > 5 and stats.get("calls", 1) > 10:
                failure_rate = stats["failures"] / stats["calls"]
                if failure_rate > 0.3:
                    alerts.append(f"Agent '{name}' has high failure rate: {failure_rate:.1%}")
        
        return alerts
    
    def _trigger_alert(self, alert: str):
        """Trigger an alert (can be overridden for voice/UI)."""
        # This can be hooked up to voice output
        pass
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)