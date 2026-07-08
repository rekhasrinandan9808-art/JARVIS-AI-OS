"""
moa/workflows/brain_workflow.py
Brain Workflow - Uses the Brain to analyze and respond to system state
"""

from .base_workflow import BaseWorkflow
from moa.brain import Brain
import logging

logger = logging.getLogger("jarvis.brain_workflow")


class BrainWorkflow(BaseWorkflow):
    """Workflow that uses the Brain to analyze system state."""
    
    def __init__(self, orchestrator):
        super().__init__(orchestrator)
        self.brain = Brain()
    
    async def run(self, **kwargs) -> dict:
        """
        Run the brain analysis workflow.
        
        This workflow:
        1. Gets supervisor data
        2. Analyzes it with the Brain
        3. Makes a decision
        4. Generates a response
        """
        # Step 1: Get supervisor data
        supervisor_result = await self.orchestrator.run_capability(
            "progress_report_full",
            kwargs
        )
        
        # Extract data
        if hasattr(supervisor_result, 'data'):
            data = supervisor_result.data
        else:
            data = supervisor_result
        
        if not data or not data.get("success", False):
            return {
                "success": False,
                "error": "Failed to get supervisor data",
                "brain_response": "Unable to analyze system state."
            }
        
        # Step 2: Process with Brain
        brain_output = await self.brain.process(data)
        
        # Step 3: Format output
        return {
            "success": True,
            "answer": brain_output["response"],
            "brain": brain_output,
            "mode": "brain"
        }