"""
moa/real_time_assistant.py
Real-Time Conversational Assistant - Full streaming pipeline
"""

import asyncio
import threading
import time
import logging
import re
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from moa.real_time_audio import RealTimeAudio
from moa.streaming_stt import StreamingSTT
from moa.intent_router import IntentRouter
from moa.orchestrator import Orchestrator
from moa.planner import Planner

logger = logging.getLogger("jarvis.real_time_assistant")


class RealTimeAssistant:
    """
    Complete real-time conversational assistant with:
    - Continuous microphone with VAD
    - Streaming transcription
    - Intent routing (commands vs conversation)
    - Streaming responses
    - Interruption support (barge-in)
    """
    
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator
        self.audio = RealTimeAudio()
        self.stt = StreamingSTT()
        self.router = IntentRouter()
        self.planner = Planner()  # Use planner for proper routing
        
        self.is_running = False
        self.is_speaking = False
        self.is_listening = False
        self.current_transcription = ""
        self.last_activity = time.time()
        self.conversation_mode = False
        
        # Callbacks
        self.callbacks = []
        
        # Interruption support
        self.interrupt_flag = False
        self.current_task = None
        
        # Search patterns for detection
        self.search_patterns = [
            r"who is (.+)",
            r"what is (.+)",
            r"where is (.+)",
            r"when is (.+)",
            r"how is (.+)",
            r"tell me about (.+)",
            r"search for (.+)",
            r"find (.+)",
            r"current (.+)",
            r"latest (.+)",
        ]
        
        # Register audio callbacks
        self.audio.register_callback(self._on_audio_event)
        self.stt.register_callback(self._on_transcription)
        
        logger.info("Real-Time Conversational Assistant initialized")
    
    def register_callback(self, callback: Callable):
        """Register a callback for events."""
        self.callbacks.append(callback)
    
    def start(self):
        """Start the real-time assistant."""
        if self.is_running:
            return
        
        self.is_running = True
        self.conversation_mode = True
        
        # Start audio capture
        self.audio.start()
        
        # Start processing thread
        self.process_thread = threading.Thread(target=self._process_loop, daemon=True)
        self.process_thread.start()
        
        logger.info("🎤 Real-Time Assistant started")
        self._notify("assistant_started", {"status": "running"})
    
    def stop(self):
        """Stop the real-time assistant."""
        self.is_running = False
        self.conversation_mode = False
        self.audio.stop()
        
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()
        
        logger.info("🛑 Real-Time Assistant stopped")
        self._notify("assistant_stopped", {"status": "stopped"})
    
    def _on_audio_event(self, event_type: str, data: Dict[str, Any]):
        """Handle audio events."""
        if event_type == "speech_end":
            # Speech ended - process the audio
            audio_data = data.get("audio", b"")
            duration = data.get("duration", 0)
            
            if len(audio_data) > 0:
                self._process_speech(audio_data, duration)
        
        elif event_type == "vad_state":
            speaking = data.get("speaking", False)
            if speaking:
                self.is_listening = True
                self.last_activity = time.time()
            else:
                self.is_listening = False
    
    def _on_transcription(self, result):
        """Handle transcription result."""
        self.current_transcription = result.text
        
        if result.is_final:
            logger.info(f"📝 Final: {result.text}")
            self._process_command(result.text)
        
        self._notify("transcription", {
            "text": result.text,
            "is_final": result.is_final,
            "confidence": result.confidence
        })
    
    def _process_speech(self, audio_data: bytes, duration: float):
        """Process speech audio with streaming transcription."""
        if not audio_data or len(audio_data) < 1000:
            return
        
        self.is_speaking = True
        self._notify("processing", {"duration": duration})
        
        # Transcribe using streaming STT
        def transcribe_async():
            try:
                # Save to temp file for transcription
                temp_path = self.stt.save_audio_to_file(audio_data)
                if temp_path:
                    text = self.stt.transcribe_file(temp_path)
                    
                    if text:
                        self.current_transcription = text
                        self._process_command(text)
                        self._notify("speech_processed", {
                            "text": text,
                            "duration": duration
                        })
                    
                    # Cleanup
                    try:
                        import os
                        os.remove(temp_path)
                    except:
                        pass
            except Exception as e:
                logger.error(f"Speech processing error: {e}")
            finally:
                self.is_speaking = False
        
        threading.Thread(target=transcribe_async, daemon=True).start()
    
    def _is_search_query(self, text: str) -> bool:
        """Check if text is a search query."""
        for pattern in self.search_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        # Check for question words
        question_words = ["who", "what", "where", "when", "why", "how"]
        words = text.lower().split()
        if words and words[0] in question_words:
            return True
        
        return False
    
    def _process_command(self, command: str):
        """Process a command with proper routing."""
        if not command or not command.strip():
            return
        
        logger.info(f"🎯 Processing: {command}")
        self._notify("command", {"command": command})
        
        # Check for interrupt commands
        interrupt_phrases = ["wait", "stop", "cancel", "nevermind", "ignore"]
        if any(phrase in command.lower() for phrase in interrupt_phrases):
            self.interrupt_flag = True
            self._notify("interrupt", {"command": command})
            return
        
        # Check for exit command
        if "exit" in command.lower() or "quit" in command.lower():
            if "mode" in command.lower() or "voice" in command.lower():
                self.stop()
                return
        
        # =================================================
        # DETECT SEARCH QUERIES FIRST
        # =================================================
        if self._is_search_query(command):
            logger.info(f"🔍 Search query detected: {command}")
            self._execute_search(command)
            return
        
        # =================================================
        # USE PLANNER FOR ROUTING
        # =================================================
        try:
            plan = self.planner.plan(command)
            
            if plan and plan.capability:
                # If it's a "think" (LLM) capability, check if it should be search
                if plan.capability == "think" and self._is_search_query(command):
                    self._execute_search(command)
                    return
                
                # Execute through orchestrator
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if plan.capability == "think":
                    # Send to LLM for conversation
                    result = loop.run_until_complete(self.orchestrator.process(command))
                else:
                    # Execute command
                    result = loop.run_until_complete(self.orchestrator.process(command))
                
                loop.close()
                
                if result and result.success:
                    response = ""
                    if result.data:
                        if isinstance(result.data, dict):
                            response = result.data.get("answer", "") or result.data.get("response", "") or str(result.data)
                        elif isinstance(result.data, str):
                            response = result.data
                    
                    if response:
                        self._notify("response", {"text": response, "result": result.data})
                else:
                    error_msg = result.error if result else "Unknown error"
                    self._notify("error", {"error": error_msg})
            else:
                # Fallback: send to LLM
                self._send_to_llm(command)
                
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            self._notify("error", {"error": str(e)})
    
    def _execute_search(self, query: str):
        """Execute a search query directly."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Use the search workflow directly
            result = loop.run_until_complete(self.orchestrator.process(query))
            loop.close()
            
            if result and result.success:
                response = ""
                if result.data:
                    if isinstance(result.data, dict):
                        response = result.data.get("answer", "") or result.data.get("response", "") or str(result.data)
                    elif isinstance(result.data, str):
                        response = result.data
                
                if response:
                    self._notify("response", {"text": response, "result": result.data, "is_search": True})
            else:
                error_msg = result.error if result else "Unknown error"
                self._notify("error", {"error": error_msg})
                
        except Exception as e:
            logger.error(f"Search execution error: {e}")
            self._notify("error", {"error": str(e)})
    
    def _send_to_llm(self, text: str):
        """Send to LLM for conversational response."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(self.orchestrator.process(text))
            loop.close()
            
            if result and result.success:
                response = ""
                if result.data:
                    if isinstance(result.data, dict):
                        response = result.data.get("answer", "") or result.data.get("response", "") or str(result.data)
                    elif isinstance(result.data, str):
                        response = result.data
                
                if response:
                    self._notify("response", {"text": response, "is_llm": True})
            else:
                error_msg = result.error if result else "Unknown error"
                self._notify("error", {"error": error_msg})
                
        except Exception as e:
            logger.error(f"LLM error: {e}")
            self._notify("error", {"error": str(e)})
    
    def _notify(self, event: str, data: Dict[str, Any]):
        """Notify all callbacks."""
        for callback in self.callbacks:
            try:
                callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _process_loop(self):
        """Main processing loop."""
        while self.is_running:
            time.sleep(0.1)
    
    def get_status(self) -> Dict[str, Any]:
        """Get assistant status."""
        return {
            "is_running": self.is_running,
            "is_listening": self.is_listening,
            "is_speaking": self.is_speaking,
            "conversation_mode": self.conversation_mode,
            "current_transcription": self.current_transcription,
            "last_activity": datetime.fromtimestamp(self.last_activity).isoformat()
        }