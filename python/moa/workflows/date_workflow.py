"""
moa/workflows/date_workflow.py
Date Workflow - Gets current date
"""

from .base_workflow import BaseWorkflow
from datetime import datetime


class DateWorkflow(BaseWorkflow):
    """Workflow for getting current date."""
    
    async def run(self, **kwargs) -> dict:
        """Get current date."""
        now = datetime.now()
        
        date_str = now.strftime("%A, %d %B %Y")
        day = now.strftime("%A")
        date = now.strftime("%d")
        month = now.strftime("%B")
        year = now.strftime("%Y")
        
        return {
            "success": True,
            "answer": f"📅 Today is {date_str}",
            "day": day,
            "date": date,
            "month": month,
            "year": year,
            "full": date_str,
            "timestamp": now.isoformat(),
            "mode": "date"
        }