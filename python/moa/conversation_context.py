"""
moa/conversation_context.py
Multi-turn Conversation Context Management
"""

import logging
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger("jarvis.conversation_context")


class ConversationContext:
    """
    Manages multi-turn conversation context.
    
    Features:
    - Tracks conversation history
    - Resolves references ("it", "that", "there")
    - Maintains topic context
    - Handles follow-up questions
    """
    
    def __init__(self, max_history: int = 20):
        self.history: List[Dict] = []
        self.max_history = max_history
        self.current_topic: Optional[str] = None
        self.entities: Dict[str, Any] = {}
        self.preferences: Dict[str, Any] = {}
        logger.info("Conversation Context initialized")
    
    def add_turn(self, user_input: str, response: str, intent: str = None):
        """Add a conversation turn."""
        self.history.append({
            "user": user_input,
            "response": response,
            "intent": intent,
            "timestamp": __import__('time').time()
        })
        
        # Trim history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Extract entities
        self._extract_entities(user_input)
        
        # Update topic
        self._update_topic(user_input)
    
    def _extract_entities(self, text: str):
        """Extract entities from text."""
        import re
        
        # Name patterns
        name_match = re.search(r"(?:my name is|call me|I'm)\s+(\w+)", text, re.IGNORECASE)
        if name_match:
            self.entities["user_name"] = name_match.group(1)
        
        # Location patterns
        loc_match = re.search(r"(?:in|from|at)\s+(\w+)", text, re.IGNORECASE)
        if loc_match and len(loc_match.group(1)) > 2:
            self.entities["location"] = loc_match.group(1)
    
    def _update_topic(self, text: str):
        """Update current topic."""
        import re
        
        # Detect topic from question
        topic_patterns = [
            r"what is (.+)",
            r"who is (.+)",
            r"tell me about (.+)",
            r"explain (.+)",
        ]
        
        for pattern in topic_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.current_topic = match.group(1).strip()
                break
    
    def resolve_reference(self, text: str) -> str:
        """Resolve references like 'it', 'that', 'there'."""
        resolved = text
        
        # Handle "it", "that", "this" references
        if text.lower().startswith("what about it") or text.lower().startswith("tell me about it"):
            if self.current_topic:
                resolved = f"tell me about {self.current_topic}"
        
        elif text.lower().startswith("and what about"):
            if self.current_topic:
                resolved = f"what about {self.current_topic}"
        
        elif "that" in text.lower() and self.current_topic:
            resolved = text.replace("that", self.current_topic)
        
        return resolved
    
    def get_context(self, query: str = None) -> str:
        """Get context for the current conversation."""
        context_parts = []
        
        # Add current topic
        if self.current_topic:
            context_parts.append(f"Current topic: {self.current_topic}")
        
        # Add entities
        if self.entities:
            entities = ", ".join([f"{k}: {v}" for k, v in self.entities.items()])
            context_parts.append(f"Known: {entities}")
        
        # Add recent history
        recent = self.history[-3:] if self.history else []
        if recent:
            context_parts.append("Recent conversation:")
            for turn in recent:
                context_parts.append(f"User: {turn['user']}")
                context_parts.append(f"Assistant: {turn['response']}")
        
        return "\n".join(context_parts)
    
    def clear(self):
        """Clear context."""
        self.history = []
        self.current_topic = None
        self.entities = {}
        logger.info("Context cleared")
    
    def get_recent_turns(self, count: int = 5) -> List[Dict]:
        """Get recent conversation turns."""
        return self.history[-count:] if self.history else []
    
    def get_stats(self) -> Dict:
        """Get context statistics."""
        return {
            "history_length": len(self.history),
            "current_topic": self.current_topic,
            "entities": len(self.entities),
            "preferences": len(self.preferences)
        }