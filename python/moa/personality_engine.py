"""
moa/personality_engine.py
Personality Engine - Advanced User Profiling and Personalization
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger("jarvis.personality_engine")


class PersonalityEngine:
    """
    Advanced Personality Engine that learns user preferences and adapts responses.
    
    Features:
    - User profiling (name, age, location, occupation)
    - Personality trait detection
    - Preference learning
    - Behavior analysis
    - Emotional memory
    - Context awareness
    - Personalized responses
    - Memory Agent protection (prevents overriding memory responses)
    """
    
    def __init__(self, memory_file: Optional[str] = None):
        self.memory_file = memory_file or str(Path(__file__).parent.parent / "data" / "advanced_memory.json")
        self.user_profile = {}
        self.conversation_history = []
        self.current_context = {}
        self._load_memory()
        
        # Personality traits with default values
        self.personality_traits = {
            "curious": 0.5,
            "analytical": 0.5,
            "creative": 0.5,
            "empathic": 0.5,
            "humorous": 0.5,
            "formal": 0.5,
            "verbose": 0.5,
        }
        
        # User memory reference
        self.user_memory = None
        
        # Memory triggers - responses from memory agent that should NOT be modified
        self.memory_triggers = [
            "I remember",
            "Your name is",
            "Your favorite",
            "Your mother",
            "Your father",
            "Your birthday",
            "Your pet",
            "Your occupation",
            "I don't know your",
            "Tell me to remember",
            "Here's what I remember",
            "Your City is",
            "Your Job is",
            "I'll remember that",
            "I've forgotten",
            "Memory was already empty",
            "Nothing to clear",
        ]
        
    def set_user_memory(self, memory_instance):
        """Link to AdvancedMemory instance."""
        self.user_memory = memory_instance
        
    def _load_memory(self):
        """Load memory from file."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_profile = data.get("user_profile", {})
                    self.conversation_history = data.get("conversation_history", [])
                    self.current_context = data.get("current_context", {})
                    logger.info(f"Loaded personality memory from {self.memory_file}")
            else:
                self._init_default_memory()
        except Exception as e:
            logger.error(f"Error loading personality memory: {e}")
            self._init_default_memory()
    
    def _init_default_memory(self):
        """Initialize default memory structure."""
        self.user_profile = {
            "name": None,
            "age": None,
            "location": None,
            "occupation": None,
            "interests": [],
            "expertise": {},
            "personality": {
                "traits": {},
                "mood": "neutral",
                "communication_style": "formal",
                "emotional_state": "neutral"
            },
            "preferences": {
                "response_length": "medium",
                "tone": "professional",
                "formality": "moderate",
                "topic_focus": []
            },
            "behavior": {
                "conversation_count": 0,
                "avg_question_length": 0,
                "frequent_topics": [],
                "peak_hours": [],
                "response_time_avg": 0,
                "learning_style": "visual",
                "curiosity_level": 0.5,
                "analytical_level": 0.5,
                "creativity_level": 0.5
            },
            "memory": {
                "short_term": [],
                "long_term": [],
                "emotional_memory": [],
                "knowledge_gaps": []
            }
        }
        self.conversation_history = []
        self.current_context = {
            "topic": None,
            "last_response": None,
            "follow_up_needed": False,
            "emotional_tone": "neutral",
            "complexity_level": 0.5,
            "engagement_level": 0.5
        }
    
    def save_profile(self) -> bool:
        """Save personality profile to file."""
        try:
            data = {
                "user_profile": self.user_profile,
                "conversation_history": self.conversation_history[-100:],
                "current_context": self.current_context,
                "updated_at": datetime.now().isoformat()
            }
            
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Personality profile saved to {self.memory_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving personality profile: {e}")
            return False
    
    def analyze_interaction(self, user_input: str, response: str) -> None:
        """Analyze a conversation interaction and update user profile."""
        try:
            self.user_profile["behavior"]["conversation_count"] += 1
            
            topics = self._extract_topics(user_input)
            if topics:
                for topic in topics:
                    if topic not in self.user_profile["interests"]:
                        self.user_profile["interests"].append(topic)
                    freq_topics = self.user_profile["behavior"]["frequent_topics"]
                    if topic not in freq_topics:
                        freq_topics.append(topic)
            
            self._analyze_personality(user_input, response)
            self._update_preferences(response)
            self._detect_emotional_tone(user_input, response)
            
            self.current_context["topic"] = topics[0] if topics else None
            self.current_context["last_response"] = response[:200] if response else None
            
            if user_input and response:
                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "user_input": user_input[:200],
                    "response": response[:200],
                    "topics": topics
                })
                if len(self.conversation_history) > 100:
                    self.conversation_history = self.conversation_history[-100:]
            
            if self.user_profile["behavior"]["conversation_count"] % 10 == 0:
                self.save_profile()
                
        except Exception as e:
            logger.error(f"Error analyzing interaction: {e}")
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from user input."""
        topics = []
        topic_keywords = {
            "science": ["science", "scientific", "research", "experiment", "lab", "physics", "chemistry", "biology"],
            "technology": ["tech", "technology", "computer", "software", "hardware", "coding", "programming", "AI", "artificial intelligence", "machine learning"],
            "space": ["space", "astronomy", "cosmos", "galaxy", "planet", "star", "moon", "sun", "universe"],
            "music": ["music", "song", "album", "artist", "band", "concert", "melody", "harmony"],
            "movies": ["movie", "film", "cinema", "actor", "actress", "director", "hollywood", "bollywood"],
            "books": ["book", "novel", "author", "reading", "literature", "fiction", "nonfiction"],
            "sports": ["sport", "game", "player", "team", "match", "tournament", "championship"],
            "food": ["food", "meal", "cook", "recipe", "restaurant", "cuisine", "dish", "delicious"],
            "travel": ["travel", "trip", "vacation", "journey", "adventure", "destination", "tour"],
            "business": ["business", "company", "startup", "entrepreneur", "investment", "market", "finance"],
            "health": ["health", "fitness", "exercise", "wellness", "medical", "doctor", "hospital"],
            "education": ["education", "school", "college", "university", "student", "teacher", "professor"],
            "art": ["art", "artist", "painting", "sculpture", "gallery", "museum", "creative"],
            "philosophy": ["philosophy", "think", "thought", "mind", "consciousness", "existence", "meaning"],
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    topics.append(topic)
                    break
        
        return topics[:3]
    
    def _analyze_personality(self, user_input: str, response: str):
        """Analyze personality traits from interaction."""
        text = user_input.lower()
        
        question_words = ["why", "how", "what", "where", "when", "who", "which"]
        question_count = sum(1 for word in question_words if word in text)
        if question_count > 0:
            self.personality_traits["curious"] = min(1.0, self.personality_traits["curious"] + 0.05 * question_count)
        
        analytical_words = ["because", "therefore", "thus", "hence", "consequently", "analysis", "logical", "reason"]
        analytical_count = sum(1 for word in analytical_words if word in text)
        if analytical_count > 0:
            self.personality_traits["analytical"] = min(1.0, self.personality_traits["analytical"] + 0.05 * analytical_count)
        
        creative_words = ["imagine", "create", "dream", "vision", "idea", "innovate", "invent", "original"]
        creative_count = sum(1 for word in creative_words if word in text)
        if creative_count > 0:
            self.personality_traits["creative"] = min(1.0, self.personality_traits["creative"] + 0.05 * creative_count)
        
        empathic_words = ["feel", "understand", "sorry", "care", "concerned", "worried", "happy", "sad", "angry"]
        empathic_count = sum(1 for word in empathic_words if word in text)
        if empathic_count > 0:
            self.personality_traits["empathic"] = min(1.0, self.personality_traits["empathic"] + 0.05 * empathic_count)
        
        self.user_profile["personality"]["traits"] = self.personality_traits.copy()
        self.user_profile["behavior"]["curiosity_level"] = self.personality_traits["curious"]
        self.user_profile["behavior"]["analytical_level"] = self.personality_traits["analytical"]
        self.user_profile["behavior"]["creativity_level"] = self.personality_traits["creative"]
    
    def _update_preferences(self, response: str):
        """Update user preferences based on response."""
        response_length = len(response)
        
        if response_length < 100:
            self.user_profile["preferences"]["response_length"] = "short"
        elif response_length < 300:
            self.user_profile["preferences"]["response_length"] = "medium"
        else:
            self.user_profile["preferences"]["response_length"] = "long"
        
        if "!" in response or "amazing" in response or "awesome" in response:
            self.user_profile["preferences"]["tone"] = "enthusiastic"
        elif "maybe" in response or "perhaps" in response or "could" in response:
            self.user_profile["preferences"]["tone"] = "cautious"
        elif "definitely" in response or "certainly" in response or "absolutely" in response:
            self.user_profile["preferences"]["tone"] = "confident"
    
    def _detect_emotional_tone(self, user_input: str, response: str):
        """Detect emotional tone from interaction."""
        text = user_input.lower()
        
        positive_words = ["happy", "great", "excellent", "wonderful", "amazing", "awesome", "good", "nice", "love"]
        negative_words = ["sad", "bad", "terrible", "awful", "horrible", "angry", "upset", "frustrated", "annoyed"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            self.user_profile["personality"]["emotional_state"] = "positive"
            self.current_context["emotional_tone"] = "positive"
        elif negative_count > positive_count:
            self.user_profile["personality"]["emotional_state"] = "negative"
            self.current_context["emotional_tone"] = "negative"
        else:
            self.user_profile["personality"]["emotional_state"] = "neutral"
            self.current_context["emotional_tone"] = "neutral"
    
    def get_personalized_response(self, base_response: str, user_input: str = "") -> str:
        """
        Get a personalized version of a response based on user profile.
        
        IMPORTANT: If the response is from the Memory Agent, return it unchanged.
        """
        if not base_response:
            return base_response
        
        # 🔧 CRITICAL FIX: If Memory Agent already provided a direct answer, DO NOT override it.
        if any(trigger in base_response for trigger in self.memory_triggers):
            return base_response
        
        try:
            name = self.user_profile.get("name")
            
            # Handle name recall requests directly
            if user_input and any(phrase in user_input.lower() for phrase in ["my name", "tell me my name", "what is my name", "who am i"]):
                if name:
                    return f"Your name is {name}. I remember! 👋"
                else:
                    return "I don't know your name yet. Please tell me and I'll remember it!"
            
            # Handle greetings with name
            greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
            is_greeting = any(g in user_input.lower() for g in greetings) if user_input else False
            
            if is_greeting and name:
                hour = datetime.now().hour
                if "good morning" in user_input.lower():
                    return f"Good morning, {name}! 🌅 How can I assist you today?"
                elif "good afternoon" in user_input.lower():
                    return f"Good afternoon, {name}! ☀️ What can I help you with?"
                elif "good evening" in user_input.lower():
                    return f"Good evening, {name}! 🌆 How may I assist you?"
                else:
                    return f"Hello, {name}! 👋 How can I help you?"
            
            return base_response
            
        except Exception as e:
            logger.error(f"Error personalizing response: {e}")
            return base_response
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get the full user profile."""
        return self.user_profile
    
    def get_personality_traits(self) -> Dict[str, float]:
        """Get personality traits."""
        return self.personality_traits.copy()
    
    def get_conversation_analytics(self) -> Dict[str, Any]:
        """Get conversation analytics."""
        try:
            total = self.user_profile["behavior"]["conversation_count"]
            avg_length = self.user_profile["behavior"]["avg_question_length"]
            engagement = self.current_context.get("engagement_level", 0.5)
            
            freq_topics = self.user_profile["behavior"]["frequent_topics"]
            topic_counts = {}
            for topic in freq_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            return {
                "total_conversations": total,
                "avg_length": avg_length,
                "engagement_score": engagement,
                "frequent_topics": topic_counts,
                "personality_trend": self.personality_traits
            }
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        return self.current_context.copy()
    
    def update_context(self, key: str, value: Any):
        """Update a context value."""
        self.current_context[key] = value
    
    def reset_context(self):
        """Reset conversation context."""
        self.current_context = {
            "topic": None,
            "last_response": None,
            "follow_up_needed": False,
            "emotional_tone": "neutral",
            "complexity_level": 0.5,
            "engagement_level": 0.5
        }