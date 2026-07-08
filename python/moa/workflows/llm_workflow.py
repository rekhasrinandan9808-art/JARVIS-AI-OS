"""
llm_workflow.py
LLM Workflow - Handles LLM-powered conversations and reasoning
"""

from .base_workflow import BaseWorkflow


class LLMWorkflow(BaseWorkflow):
    """Workflow for LLM-powered interactions."""

    async def run(self, **kwargs) -> dict:
        """Run LLM workflow."""
        action = kwargs.get("action", "think")
        
        if action == "think":
            query = kwargs.get("query", "")
            print(f"🧠 Thinking about: {query[:50]}...")
            
            result = await self.orchestrator.run_capability(
                "think",
                {"query": query}
            )
            
            print(f"📦 LLM Workflow received: {result}")
            
            # Extract data from AgentResult
            if hasattr(result, 'data'):
                data = result.data
                print(f"📦 Data from result.data: {data}")
            else:
                data = result
                print(f"📦 Data is result: {data}")
            
            # Check if data is None
            if data is None:
                print(f"❌ Error: LLM returned None")
                return {"success": False, "error": "LLM returned None", "response": None}
            
            # Check if data is a dict
            if not isinstance(data, dict):
                print(f"❌ Error: Invalid response type: {type(data)}")
                return {"success": False, "error": f"Invalid response type: {type(data)}", "response": None}
            
            # Check for response
            if data.get("response"):
                response = data["response"]
                print(f"🧠 JARVIS: {response}")
                return data
            else:
                error_msg = data.get("error", "No response from LLM")
                print(f"❌ Error: {error_msg}")
                return {"success": False, "error": error_msg, "response": None}

        if action == "chat":
            message = kwargs.get("message", "")
            
            result = await self.orchestrator.run_capability(
                "chat",
                {"message": message}
            )
            
            if hasattr(result, 'data'):
                data = result.data
            else:
                data = result
            
            if data is None:
                print(f"❌ Error: LLM returned None")
                return {"success": False, "error": "LLM returned None", "response": None}
            
            if isinstance(data, dict) and data.get("response"):
                print(f"🧠 JARVIS: {data['response']}")
                return data
            
            return {"success": False, "error": "No response from LLM", "response": None}

        return {"success": False, "error": f"Unknown action: {action}", "response": None}