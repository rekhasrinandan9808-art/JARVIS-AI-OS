"""
moa/proactive_supervisor.py
Proactive Supervisor - Background monitoring with alerts
"""

import asyncio
import psutil
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("jarvis.proactive_supervisor")


@dataclass
class Alert:
    """System alert."""
    level: str  # info, warning, critical
    source: str
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = True
    alert_id: str = field(default_factory=lambda: str(time.time()))


class ProactiveSupervisor:
    """
    Background system monitoring with proactive alerts.
    
    Monitors:
    - CPU usage
    - Memory usage  
    - Disk usage
    - Network connectivity
    - Agent health
    - Battery status
    - System uptime
    """
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self._running = False
        self._task = None
        self._callbacks = []
        self.thresholds = {
            "cpu": 80,  # percent
            "memory": 80,  # percent
            "disk": 85,  # percent
            "battery": 20,  # percent
        }
        self.last_check = {}
        self.agent_health = {}
        self._alerted_conditions = set()  # Track active alerts to avoid duplicates
        self._alert_cooldown = {}  # Track when last alert was sent for each condition
        
        logger.info("Proactive Supervisor initialized")
    
    def register_callback(self, callback):
        """Register a callback for alerts (e.g., voice output)."""
        self._callbacks.append(callback)
    
    async def start(self, interval: int = 30):
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"🔍 Proactive Supervisor started (interval: {interval}s)")
    
    async def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Proactive Supervisor stopped")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_system()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)
    
    async def _check_system(self):
        """Check all system metrics."""
        current_time = time.time()
        
        # Track which conditions are currently active
        current_conditions = set()
        
        # Check CPU
        cpu = psutil.cpu_percent(interval=0.5)
        if cpu > self.thresholds["cpu"]:
            condition = f"cpu_{cpu:.0f}"
            current_conditions.add("cpu_high")
            if "cpu_high" not in self._alerted_conditions:
                # Only alert if not already active
                alert = Alert(
                    level="warning" if cpu < 90 else "critical",
                    source="CPU",
                    message=f"CPU usage is {cpu:.1f}% (threshold: {self.thresholds['cpu']}%)"
                )
                self._add_alert(alert)
                self._alerted_conditions.add("cpu_high")
        
        # Check Memory
        memory = psutil.virtual_memory()
        if memory.percent > self.thresholds["memory"]:
            current_conditions.add("memory_high")
            if "memory_high" not in self._alerted_conditions:
                alert = Alert(
                    level="warning" if memory.percent < 90 else "critical",
                    source="Memory",
                    message=f"Memory usage is {memory.percent:.1f}% (threshold: {self.thresholds['memory']}%)"
                )
                self._add_alert(alert)
                self._alerted_conditions.add("memory_high")
        
        # Check Disk
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                if usage.percent > self.thresholds["disk"]:
                    condition = f"disk_{partition.device}_{usage.percent:.0f}"
                    disk_key = f"disk_{partition.device}"
                    current_conditions.add(disk_key)
                    
                    if disk_key not in self._alerted_conditions:
                        alert = Alert(
                            level="warning" if usage.percent < 95 else "critical",
                            source="Disk",
                            message=f"Disk {partition.device} is {usage.percent:.1f}% full"
                        )
                        self._add_alert(alert)
                        self._alerted_conditions.add(disk_key)
            except:
                continue
        
        # Check Battery
        if hasattr(psutil, "sensors_battery"):
            battery = psutil.sensors_battery()
            if battery:
                if battery.percent < self.thresholds["battery"] and not battery.power_plugged:
                    current_conditions.add("battery_low")
                    if "battery_low" not in self._alerted_conditions:
                        alert = Alert(
                            level="warning",
                            source="Battery",
                            message=f"Battery is at {battery.percent}% (plug in soon)"
                        )
                        self._add_alert(alert)
                        self._alerted_conditions.add("battery_low")
        
        # Check Network
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            # Network is up
        except:
            current_conditions.add("network_down")
            if "network_down" not in self._alerted_conditions:
                alert = Alert(
                    level="critical",
                    source="Network",
                    message="Internet connection appears to be down"
                )
                self._add_alert(alert)
                self._alerted_conditions.add("network_down")
        
        # Remove conditions that are no longer active
        resolved_conditions = self._alerted_conditions - current_conditions
        for condition in resolved_conditions:
            self._alerted_conditions.remove(condition)
            # Add resolved notification
            if condition in ["cpu_high", "memory_high", "network_down", "battery_low"]:
                resolved_message = {
                    "cpu_high": "CPU usage returned to normal",
                    "memory_high": "Memory usage returned to normal",
                    "network_down": "Internet connection restored",
                    "battery_low": "Battery is now charging or above threshold"
                }.get(condition, "Condition resolved")
                logger.info(f"✅ Resolved: {resolved_message}")
                # Optionally notify
                for callback in self._callbacks:
                    try:
                        callback(Alert(
                            level="info",
                            source="System",
                            message=f"✅ {resolved_message}"
                        ))
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
        
        # Remove conditions that are no longer active from disk alerts
        current_disk_conditions = {c for c in current_conditions if c.startswith("disk_")}
        for condition in list(self._alerted_conditions):
            if condition.startswith("disk_") and condition not in current_disk_conditions:
                self._alerted_conditions.remove(condition)
                disk_name = condition.replace("disk_", "")
                logger.info(f"✅ Disk {disk_name} usage returned to normal")
                for callback in self._callbacks:
                    try:
                        callback(Alert(
                            level="info",
                            source="System",
                            message=f"✅ Disk {disk_name} usage returned to normal"
                        ))
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
    
    def _add_alert(self, alert: Alert):
        """Add an alert and notify callbacks."""
        self.alerts.append(alert)
        logger.warning(f"🔔 ALERT [{alert.level}]: {alert.message}")
        
        # Only notify if alert is active
        if alert.is_active:
            for callback in self._callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts."""
        return [{
            "level": a.level,
            "source": a.source,
            "message": a.message,
            "timestamp": a.timestamp,
            "is_active": a.is_active
        } for a in self.alerts[-limit:]]
    
    def get_status(self) -> Dict:
        """Get current system status."""
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        
        battery = None
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                battery = {
                    "percent": bat.percent,
                    "plugged": bat.power_plugged
                }
        
        return {
            "cpu": cpu,
            "memory": {
                "percent": memory.percent,
                "used": memory.used,
                "total": memory.total
            },
            "battery": battery,
            "uptime": time.time() - psutil.boot_time(),
            "alerts": len(self.alerts),
            "active_alerts": len(self._alerted_conditions)
        }
    
    def clear_alerts(self):
        """Clear all alerts."""
        self.alerts = []
        self._alerted_conditions = set()
        logger.info("All alerts cleared")