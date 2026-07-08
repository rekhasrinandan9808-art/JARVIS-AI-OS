"""
voice_workflow.py
Voice Workflow - Handles voice interaction with JARVIS
"""

import re
from .base_workflow import BaseWorkflow


class VoiceWorkflow(BaseWorkflow):
    """Workflow for voice interaction."""

    async def run(self, **kwargs) -> dict:
        """
        Run voice workflow.
        
        Args:
            text: Text to speak (for speak action)
            listen: Whether to listen for voice input
            duration_seconds: Recording duration for listen
            model_size: Whisper model size
            
        Returns:
            dict: Voice interaction results
        """
        # Extract parameters
        text = kwargs.get("text", "")
        listen_mode = kwargs.get("listen", False)
        duration = kwargs.get("duration_seconds", 5)
        model_size = kwargs.get("model_size", "base")
        save_path = kwargs.get("save_path", None)
        rate = kwargs.get("rate", None)
        volume = kwargs.get("volume", None)
        casual = kwargs.get("casual", True)
        style = kwargs.get("style", "friendly")
        
        results = {}
        
        # If text provided and listen is False, just speak
        if text and not listen_mode:
            print(f"🗣️ JARVIS: {text}")
            speak_result = await self.orchestrator.run_capability(
                "speak",
                {
                    "text": text,
                    "save_path": save_path,
                    "rate": rate,
                    "volume": volume,
                    "casual": casual,
                    "style": style
                }
            )
            
            if hasattr(speak_result, 'data'):
                results = speak_result.data
            else:
                results = speak_result
            
            return results
        
        # If listen mode, record and transcribe
        if listen_mode:
            print("🎤 Listening... (speak now, you have {} seconds)".format(duration))
            listen_result = await self.orchestrator.run_capability(
                "listen",
                {
                    "duration": duration,  # Changed from duration_seconds to duration
                    "model_size": model_size
                }
            )
            
            if hasattr(listen_result, 'data'):
                response = listen_result.data
            else:
                response = listen_result
            
            results = response
            
            # If we got text, echo it back
            if results.get("text"):
                print(f"📝 You said: {results['text']}")
                
                # Check if this is a command
                from moa.planner import Planner
                planner = Planner()
                plan = planner.plan(results['text'])
                
                if plan.capability:
                    print(f"🔄 Detected capability: {plan.capability}")
                    results["capability"] = plan.capability
                    results["params"] = plan.params
                    results["is_command"] = True
                
                # Optional: auto-respond with what was heard
                if kwargs.get("echo", True):
                    echo_text = f"I heard you say: {results['text']}"
                    await self.orchestrator.run_capability(
                        "speak",
                        {"text": echo_text, "casual": casual}
                    )
            else:
                print("No speech detected")
                results = {"error": "No speech detected"}
            
            return results
        
        # If both speak and listen (interactive)
        if text and listen_mode:
            print(f"🗣️ JARVIS: {text}")
            await self.orchestrator.run_capability(
                "speak",
                {"text": text, "casual": casual, "style": style}
            )
            
            print("🎤 Listening for your response...")
            listen_result = await self.orchestrator.run_capability(
                "listen",
                {
                    "duration": duration,
                    "model_size": model_size
                }
            )
            
            if hasattr(listen_result, 'data'):
                response = listen_result.data
            else:
                response = listen_result
            
            if response and response.get("text"):
                print(f"📝 You said: {response['text']}")
                
                # Check if this is a command
                from moa.planner import Planner
                planner = Planner()
                plan = planner.plan(response['text'])
                
                if plan.capability:
                    response["capability"] = plan.capability
                    response["params"] = plan.params
                    response["is_command"] = True
                
                return response
            else:
                return {"error": "No speech detected"}
        
        return {"error": "No action specified"}

    async def say_and_listen(self, text: str, duration: float = 10) -> str:
        """
        Say something and listen for a response.
        
        Args:
            text: Text to speak
            duration: Recording duration in seconds
            
        Returns:
            str: The user's spoken response
        """
        result = await self.run(
            text=text,
            listen=True,
            duration_seconds=duration,
            echo=False
        )
        
        if isinstance(result, dict) and result.get("text"):
            return result["text"]
        
        return None