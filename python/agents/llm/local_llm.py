"""
agents/llm/local_llm.py
Local LLM Integration with Ollama
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jarvis.local_llm")


class LocalLLM:
    """
    Local LLM integration using Ollama.
    Supports models like llama2, mistral, codellama, etc.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self.base_url = base_url
        self.model = model
        self._available = False
        self._check_availability()
    
    def _check_availability(self):
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if self.model in model_names or any(self.model in m for m in model_names):
                    self._available = True
                    logger.info(f"✅ Local LLM '{self.model}' available")
                else:
                    logger.warning(f"⚠️ Model '{self.model}' not found. Available: {model_names}")
                    self._available = False
            else:
                logger.warning("⚠️ Ollama not responding")
                self._available = False
        except:
            logger.warning("⚠️ Ollama not running. Install from https://ollama.ai")
            self._available = False
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, system_prompt: str = None, temperature: float = 0.7) -> Dict:
        """Generate a response using local LLM."""
        if not self._available:
            return {"success": False, "error": "Ollama not available"}
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "stream": False
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", ""),
                    "model": self.model,
                    "source": "ollama"
                }
            else:
                return {"success": False, "error": f"Ollama error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> Dict:
        """Chat with local LLM."""
        if not self._available:
            return {"success": False, "error": "Ollama not available"}
        
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("message", {}).get("content", ""),
                    "model": self.model,
                    "source": "ollama"
                }
            else:
                return {"success": False, "error": f"Ollama error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_models(self) -> List[str]:
        """List available models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except:
            pass
        return []
    
    def pull_model(self, model: str) -> Dict:
        """Pull a model from Ollama registry."""
        try:
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                stream=True,
                timeout=300
            )
            if response.status_code == 200:
                return {"success": True, "model": model}
            else:
                return {"success": False, "error": f"Pull failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}