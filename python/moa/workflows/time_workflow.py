"""
moa/workflows/time_workflow.py
Time Workflow - Gets current time
"""

from .base_workflow import BaseWorkflow
from datetime import datetime
import pytz


class TimeWorkflow(BaseWorkflow):
    """Workflow for getting current time."""
    
    async def run(self, **kwargs) -> dict:
        """Get current time."""
        now = datetime.now()
        
        # Format time
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %d %B %Y")
        full_str = f"{date_str} at {time_str}"
        
        return {
            "success": True,
            "answer": f"🕒 Current time: {time_str}",
            "full": full_str,
            "time": time_str,
            "date": date_str,
            "timestamp": now.isoformat(),
            "mode": "time"
        }