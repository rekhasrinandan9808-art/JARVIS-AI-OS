"""
moa/workflows/launch_workflow.py
Launch Workflow - Opens applications using AppController
"""

from .base_workflow import BaseWorkflow
from moa.app_controller import AppController
import logging

logger = logging.getLogger("jarvis.launch_workflow")


class LaunchWorkflow(BaseWorkflow):
    """Workflow for launching applications."""
    
    def __init__(self, orchestrator):
        super().__init__(orchestrator)
        self.app_controller = AppController()
    
    async def run(self, **kwargs) -> dict:
        """Launch an application."""
        app = kwargs.get("app", "").strip()
        
        if not app:
            return {
                "success": False,
                "answer": "What would you like me to open?",
                "error": "No app specified"
            }
        
        logger.info(f"Launching: {app}")
        
        # Launch the app
        result = self.app_controller.launch(app)
        
        # Log the result
        if result["success"]:
            logger.info(f"Successfully launched {app}")
        else:
            logger.error(f"Failed to launch {app}: {result.get('error', 'Unknown error')}")
        
        return {
            "success": result["success"],
            "answer": result["message"],
            "app": result.get("app"),
            "path": result.get("path"),
            "error": result.get("error")
        }