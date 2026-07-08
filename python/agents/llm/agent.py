"""
llm/agent.py
Agent #41: LLMAgent -- Handles LLM interactions via Groq API
"""

from __future__ import annotations
import asyncio
import logging
import os
import sys
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent, AgentCapability

# Force load .env
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ LLM Agent: Loaded .env from {env_file}")
except Exception as e:
    print(f"⚠️ LLM Agent: Error loading .env: {e}")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️ requests not installed. Run: pip install requests")

logger = logging.getLogger("jarvis.llm")


class LLMAgent(BaseAgent):
    name = "llm"
    description = "LLM Agent for natural language understanding via Groq API"
    agent_id = 41

    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = "llama-3.3-70b-versatile"
        
        if self.api_key:
            print(f"✅ LLM Agent: API key found: {self.api_key[:8]}...")
        else:
            print(f"❌ LLM Agent: API key NOT found")

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("think", "Think about a query and generate a response", {"query": "str"}),
            AgentCapability("chat", "Have a conversation with JARVIS", {"message": "str"}),
        ]

    def _call_groq(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Call Groq API with messages."""
        if not self.api_key:
            logger.error("GROQ_API_KEY not set")
            return None

        if not HAS_REQUESTS:
            logger.error("requests not installed")
            return None

        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 150,
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content:
                    return content.strip()
                else:
                    logger.error("Groq returned empty response")
                    return None
            else:
                logger.error(f"Groq API error {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None

    def _think_sync(self, query: str) -> str:
        """Synchronous thinking with improved system prompt."""
        if not query:
            return "No query provided."

        messages = [
            {"role": "system", "content": """You are JARVIS, an advanced AI assistant.

IMPORTANT RULES:
1. If you do not know a current fact with confidence, say "I'm not sure" instead of guessing.
2. Do not invent current political leaders, news, sports results, or prices.
3. For time-sensitive information (current events, elections, weather, sports), say that a web search is needed.
4. Be helpful, intelligent, and concise. Keep responses under 300 characters.
5. If asked about something that changes frequently, suggest checking recent sources."""},
            {"role": "user", "content": query}
        ]

        response = self._call_groq(messages)
        
        if response:
            return response
        
        return "I'm having trouble connecting to my AI engine. Please try again."

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "think":
            query = params.get("query", "")
            if not query:
                return {"success": False, "error": "No query provided", "response": None}
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._think_sync, query)
            
            return {
                "success": True, 
                "response": result, 
                "query": query
            }

        if action == "chat":
            message = params.get("message", "")
            if not message:
                return {"success": False, "error": "No message provided", "response": None}
                
            messages = [
                {"role": "system", "content": "You are JARVIS, an advanced AI assistant. Be conversational and helpful."},
                {"role": "user", "content": message}
            ]
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._call_groq, messages)
            
            return {
                "success": True, 
                "response": result or "I couldn't process that.", 
                "message": message
            }

        return {"success": False, "error": f"Unknown action: {action}", "response": None}