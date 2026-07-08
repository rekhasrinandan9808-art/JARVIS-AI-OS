"""
moa/system_monitor.py
System Monitoring Dashboard - CLI version
"""

import os
import sys
import time
import psutil
import platform
import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger("jarvis.system_monitor")


class SystemMonitor:
    """
    Real-time system monitoring with CLI dashboard.
    
    Monitors:
    - CPU usage per core
    - Memory usage
    - Disk usage
    - Network traffic
    - Processes
    - Battery status
    - System temperature
    """
    
    def __init__(self):
        self.history = {
            "cpu": deque(maxlen=60),
            "memory": deque(maxlen=60),
            "network": {"sent": 0, "recv": 0}
        }
        self.last_network = psutil.net_io_counters()
        self.running = False
    
    def get_stats(self) -> Dict:
        """
        Get current system stats.
        
        Returns:
            Dict containing all system metrics
        """
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
        cpu_avg = sum(cpu_percent) / len(cpu_percent)
        
        # Memory
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk
        disks = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "used": usage.used,
                    "total": usage.total,
                    "percent": usage.percent
                })
            except:
                continue
        
        # Network
        net = psutil.net_io_counters()
        net_sent = net.bytes_sent - self.last_network.bytes_sent
        net_recv = net.bytes_recv - self.last_network.bytes_recv
        self.last_network = net
        
        # Battery
        battery = None
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                battery = {
                    "percent": bat.percent,
                    "plugged": bat.power_plugged,
                    "time_left": bat.secsleft
                }
        
        # Temperature
        temps = []
        if hasattr(psutil, "sensors_temperatures"):
            for name, entries in psutil.sensors_temperatures().items():
                for entry in entries:
                    temps.append({
                        "name": name,
                        "current": entry.current,
                        "high": entry.high
                    })
        
        # 🔧 FIX: Wrap generator in list() to get actual count
        processes = len(list(psutil.process_iter()))
        
        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = time.time() - psutil.boot_time()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "total": cpu_avg,
                "cores": cpu_percent
            },
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "available": memory.available,
                "percent": memory.percent,
                "swap": swap.percent
            },
            "disk": disks,
            "network": {
                "sent": net_sent / 1024 / 1024,  # MB/s
                "recv": net_recv / 1024 / 1024   # MB/s
            },
            "battery": battery,
            "temperature": temps,
            "processes": processes,
            "uptime": uptime,
            "uptime_formatted": self._format_uptime(uptime),
            "boot_time": boot_time.isoformat()
        }
    
    def _format_uptime(self, seconds: float) -> str:
        """
        Format uptime into human-readable string.
        
        Args:
            seconds: Uptime in seconds
            
        Returns:
            Formatted string like "2d 4h 30m"
        """
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        return " ".join(parts) if parts else "< 1m"
    
    def display_dashboard(self):
        """
        Display a text-based dashboard with current system stats.
        """
        stats = self.get_stats()
        
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║                    JARVIS SYSTEM MONITOR                       ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print(f"║  Time: {stats['timestamp']}")
        print(f"║  Uptime: {stats['uptime_formatted']}")
        print("╠══════════════════════════════════════════════════════════════════╣")
        
        # CPU
        cpu = stats["cpu"]
        cpu_bar = "█" * int(cpu["total"] / 2) + "░" * (50 - int(cpu["total"] / 2))
        print(f"║  CPU: {cpu['total']:.1f}% [{cpu_bar}]")
        print(f"║  Cores: {' '.join([f'{c:.1f}%' for c in cpu['cores'][:8]])}")
        
        # Memory
        mem = stats["memory"]
        mem_bar = "█" * int(mem["percent"] / 2) + "░" * (50 - int(mem["percent"] / 2))
        print(f"║  Memory: {mem['percent']:.1f}% [{mem_bar}]")
        print(f"║  Used: {mem['used'] / 1024 / 1024 / 1024:.2f}GB / Total: {mem['total'] / 1024 / 1024 / 1024:.2f}GB")
        
        # Disk
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  Disks:")
        for disk in stats["disk"]:
            bar = "█" * int(disk["percent"] / 2) + "░" * (50 - int(disk["percent"] / 2))
            print(f"║    {disk['device']}: {disk['percent']:.1f}% [{bar}]")
        
        # Network
        net = stats["network"]
        print("╠══════════════════════════════════════════════════════════════════╣")
        print(f"║  Network: ↓ {net['recv']:.2f} MB/s  ↑ {net['sent']:.2f} MB/s")
        
        # Battery
        if stats["battery"]:
            bat = stats["battery"]
            bat_bar = "█" * int(bat["percent"] / 2) + "░" * (50 - int(bat["percent"] / 2))
            plugged = "🔌" if bat["plugged"] else "🔋"
            print(f"║  Battery: {bat['percent']}% [{bat_bar}] {plugged}")
        
        # Processes
        print(f"║  Processes: {stats['processes']}")
        
        # Temperature
        if stats["temperature"]:
            print("╠══════════════════════════════════════════════════════════════════╣")
            for temp in stats["temperature"]:
                print(f"║  {temp['name']}: {temp['current']:.1f}°C")
        
        print("╚══════════════════════════════════════════════════════════════════╝")
    
    def run_dashboard(self, interval: float = 2.0):
        """
        Run the dashboard in a continuous loop.
        
        Args:
            interval: Update interval in seconds (default: 2.0)
        """
        self.running = True
        try:
            while self.running:
                self.display_dashboard()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
        finally:
            self.running = False
    
    def get_alert(self, threshold: Dict) -> Optional[str]:
        """
        Check if any metrics exceed thresholds.
        
        Args:
            threshold: Dict with 'cpu', 'memory', 'battery' thresholds
            
        Returns:
            Alert message if threshold exceeded, None otherwise
        """
        stats = self.get_stats()
        
        if stats["cpu"]["total"] > threshold.get("cpu", 80):
            return f"⚠️ High CPU usage: {stats['cpu']['total']:.1f}%"
        
        if stats["memory"]["percent"] > threshold.get("memory", 80):
            return f"⚠️ High memory usage: {stats['memory']['percent']:.1f}%"
        
        if stats["battery"] and stats["battery"]["percent"] < threshold.get("battery", 20):
            return f"⚠️ Low battery: {stats['battery']['percent']}%"
        
        return None


def main():
    """Run the system monitor."""
    monitor = SystemMonitor()
    monitor.run_dashboard()


if __name__ == "__main__":
    main()