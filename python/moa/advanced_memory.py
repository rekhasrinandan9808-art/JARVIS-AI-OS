"""
Advanced Memory System for JARVIS
Tracks user behavior, personality, preferences, and conversation patterns
Like ChatGPT/Gemini - remembers everything and adapts responses
"""

import json
import os
import time
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import numpy as np
from pathlib import Path

logger = logging.getLogger("jarvis.advanced_memory")

class AdvancedMemory:
    """
    Advanced memory system that tracks:
    - User behavior patterns
    - Personality traits
    - Conversation style
    - Preferences and interests
    - Emotional state
    - Learning patterns
    - Response style adaptation
    """
    
    def __init__(self, memory_file: str = None):
        self.memory_file = memory_file or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            "advanced_memory.json"
        )
        
        # Ensure directory exists
        Path(self.memory_file).parent.mkdir(parents=True, exist_ok=True)
        
        # User profile
        self.user_profile = {
            "name": None,
            "age": None,
            "location": None,
            "occupation": None,
            "interests": [],
            "expertise": {},
            "personality": {
                "traits": {},  # e.g., "curious": 0.8, "analytical": 0.7
                "mood": "neutral",
                "communication_style": "formal",  # formal, casual, technical, simple
                "emotional_state": "neutral"
            },
            "preferences": {
                "response_length": "medium",  # short, medium, detailed
                "tone": "professional",  # professional, casual, friendly, humorous
                "formality": "moderate",  # formal, moderate, casual
                "topic_focus": [],  # topics user frequently asks about
            },
            "behavior": {
                "conversation_count": 0,
                "avg_question_length": 0,
                "frequent_topics": [],
                "peak_hours": [],  # times user is most active
                "response_time_avg": 0,  # average time to respond
                "learning_style": "visual",  # visual, auditory, reading, kinesthetic
                "curiosity_level": 0.5,
                "analytical_level": 0.5,
                "creativity_level": 0.5,
            },
            "memory": {
                "short_term": [],  # recent conversations (last 20)
                "long_term": [],  # important facts
                "emotional_memory": [],  # emotional responses
                "knowledge_gaps": [],  # topics user struggled with
            }
        }
        
        # Conversation history
        self.conversation_history = []
        self.max_history = 100
        
        # Context tracking
        self.current_context = {
            "topic": None,
            "last_response": None,
            "follow_up_needed": False,
            "emotional_tone": "neutral",
            "complexity_level": 0.5,  # 0-1, how complex the conversation is
            "engagement_level": 0.5,  # 0-1, how engaged the user is
        }
        
        # Load existing memory
        self.load()
        
    def load(self):
        """Load memory from file."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.user_profile = data.get("user_profile", self.user_profile)
                    self.conversation_history = data.get("conversation_history", [])
                    self.current_context = data.get("current_context", self.current_context)
                logger.info(f"📂 Loaded advanced memory: {len(self.conversation_history)} conversations")
        except Exception as e:
            logger.warning(f"Could not load advanced memory: {e}")
    
    def save(self):
        """Save memory to file."""
        try:
            data = {
                "user_profile": self.user_profile,
                "conversation_history": self.conversation_history[-100:],  # Keep last 100
                "current_context": self.current_context,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.memory_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save advanced memory: {e}")
    
    def process_interaction(self, user_input: str, response: str, emotion: str = None):
        """
        Process a conversation interaction and update all memory systems.
        This is called every time JARVIS talks to the user.
        """
        # Add to history
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response,
            "emotion": emotion or self._detect_emotion(user_input),
            "user_profile_snapshot": self.get_user_summary()
        }
        self.conversation_history.append(interaction)
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Update user behavior
        self._update_behavior(user_input, response)
        
        # Update personality based on interactions
        self._update_personality(user_input, response)
        
        # Update preferences based on patterns
        self._update_preferences(user_input, response)
        
        # Extract facts and store in memory
        self._extract_facts(user_input, response)
        
        # Update context
        self._update_context(user_input, response)
        
        # Save
        self.save()
    
    def _detect_emotion(self, text: str) -> str:
        """Detect emotion from text using keyword analysis."""
        text_lower = text.lower()
        
        # Joy
        if any(word in text_lower for word in ['happy', 'great', 'awesome', 'wonderful', 'amazing', 'excellent', 'love', 'glad', 'perfect']):
            return "joyful"
        
        # Sadness
        if any(word in text_lower for word in ['sad', 'unfortunate', 'unhappy', 'depressed', 'lonely', 'sorry', 'regret', 'cry', 'hurt']):
            return "sad"
        
        # Anger
        if any(word in text_lower for word in ['angry', 'frustrated', 'annoyed', 'irritated', 'mad', 'upset', 'furious']):
            return "angry"
        
        # Fear
        if any(word in text_lower for word in ['scared', 'fear', 'anxious', 'worried', 'terrified', 'nervous']):
            return "fearful"
        
        # Surprise
        if any(word in text_lower for word in ['surprised', 'shocked', 'amazed', 'astonished', 'unexpected']):
            return "surprised"
        
        # Curiosity
        if any(word in text_lower for word in ['curious', 'wonder', 'how', 'why', 'what', 'explain', 'tell me']):
            return "curious"
        
        return "neutral"
    
    def _update_behavior(self, user_input: str, response: str):
        """Update user behavior patterns."""
        behavior = self.user_profile["behavior"]
        
        # Update conversation count
        behavior["conversation_count"] += 1
        
        # Update average question length
        words = len(user_input.split())
        if behavior["avg_question_length"] == 0:
            behavior["avg_question_length"] = words
        else:
            behavior["avg_question_length"] = (
                behavior["avg_question_length"] * 0.8 + words * 0.2
            )
        
        # Extract topics
        topics = self._extract_topics(user_input)
        for topic in topics:
            if topic not in behavior["frequent_topics"]:
                behavior["frequent_topics"].append(topic)
        
        # Update curiosity level
        if any(word in user_input.lower() for word in ['why', 'how', 'what', 'explain', 'tell me', 'curious', 'wonder']):
            behavior["curiosity_level"] = min(1.0, behavior["curiosity_level"] + 0.05)
        else:
            behavior["curiosity_level"] = max(0.1, behavior["curiosity_level"] - 0.01)
        
        # Update analytical level
        if any(word in user_input.lower() for word in ['analyze', 'compare', 'contrast', 'evaluate', 'assess', 'calculate']):
            behavior["analytical_level"] = min(1.0, behavior["analytical_level"] + 0.05)
        
        # Update creativity level
        if any(word in user_input.lower() for word in ['imagine', 'create', 'design', 'innovate', 'creative', 'idea', 'brainstorm']):
            behavior["creativity_level"] = min(1.0, behavior["creativity_level"] + 0.05)
    
    def _update_personality(self, user_input: str, response: str):
        """Update personality traits based on interactions."""
        traits = self.user_profile["personality"]["traits"]
        
        # Track personality traits from user input
        trait_keywords = {
            "curious": ["why", "how", "what", "explain", "tell me", "curious", "wonder"],
            "analytical": ["analyze", "compare", "contrast", "evaluate", "assess", "calculate", "data", "proof"],
            "creative": ["imagine", "create", "design", "innovate", "creative", "idea", "brainstorm", "artistic"],
            "practical": ["practical", "realistic", "useful", "application", "implement", "real world"],
            "theoretical": ["theory", "concept", "principle", "abstract", "philosophical", "conceptual"],
            "social": ["people", "community", "collaborate", "team", "social", "interact", "relationship"],
            "independent": ["myself", "alone", "self", "independent", "own", "personal"],
            "adventurous": ["adventure", "explore", "new", "experience", "travel", "discover"],
            "cautious": ["careful", "risk", "danger", "safe", "protect", "avoid", "safety"],
            "optimistic": ["hope", "future", "positive", "opportunity", "believe", "trust"],
            "pessimistic": ["worry", "doubt", "negative", "risk", "problem", "issue", "concern"],
        }
        
        text_lower = user_input.lower()
        for trait, keywords in trait_keywords.items():
            if any(word in text_lower for word in keywords):
                if trait not in traits:
                    traits[trait] = 0.0
                traits[trait] = min(1.0, traits[trait] + 0.03)
            else:
                if trait in traits:
                    traits[trait] = max(0.0, traits[trait] - 0.005)
        
        # Update emotional state from response
        emotion = self._detect_emotion(user_input)
        if emotion != "neutral":
            self.user_profile["personality"]["emotional_state"] = emotion
    
    def _update_preferences(self, user_input: str, response: str):
        """Update user preferences based on patterns."""
        preferences = self.user_profile["preferences"]
        
        # Detect preferred response length
        word_count = len(user_input.split())
        if word_count < 5:
            preferences["response_length"] = "short"
        elif word_count < 15:
            preferences["response_length"] = "medium"
        else:
            preferences["response_length"] = "detailed"
        
        # Detect communication style
        text_lower = user_input.lower()
        if any(word in text_lower for word in ['algorithm', 'code', 'function', 'parameter', 'variable', 'syntax']):
            preferences["tone"] = "technical"
        elif any(word in text_lower for word in ['please', 'thank you', 'kindly', 'appreciate']):
            preferences["tone"] = "professional"
        elif any(word in text_lower for word in ['lol', 'haha', 'cool', 'awesome', 'great']):
            preferences["tone"] = "friendly"
        
        # Detect formality
        if any(word in text_lower for word in ['sir', 'madam', 'would you', 'could you', 'may i']):
            preferences["formality"] = "formal"
        elif any(word in text_lower for word in ['hey', 'yo', 'sup', 'whats up']):
            preferences["formality"] = "casual"
        
        # Track topic focus
        topics = self._extract_topics(user_input)
        for topic in topics:
            if topic not in preferences["topic_focus"]:
                preferences["topic_focus"].append(topic)
            if len(preferences["topic_focus"]) > 20:
                preferences["topic_focus"] = preferences["topic_focus"][-20:]
    
    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text."""
        topics = []
        topic_keywords = {
            "technology": ["tech", "computer", "software", "hardware", "internet", "ai", "ml", "data", "coding", "programming"],
            "science": ["physics", "chemistry", "biology", "astronomy", "math", "science", "research", "experiment"],
            "business": ["business", "startup", "marketing", "sales", "finance", "money", "investment", "entrepreneur"],
            "education": ["school", "college", "university", "learning", "study", "course", "degree", "exam"],
            "health": ["health", "fitness", "exercise", "diet", "nutrition", "wellness", "medical", "doctor"],
            "entertainment": ["movie", "music", "game", "show", "actor", "artist", "performance", "entertain"],
            "politics": ["government", "policy", "election", "leader", "political", "law", "regulation"],
            "travel": ["travel", "vacation", "destination", "trip", "hotel", "flight", "tourist", "adventure"],
            "food": ["food", "cooking", "recipe", "restaurant", "cuisine", "meal", "chef", "kitchen"],
            "sports": ["sport", "game", "team", "player", "match", "tournament", "score", "athlete"],
            "philosophy": ["philosophy", "ethics", "moral", "virtue", "logic", "reason", "truth", "existence"],
            "art": ["art", "design", "drawing", "painting", "sculpture", "creative", "artist", "gallery"],
            "psychology": ["psychology", "mind", "behavior", "emotion", "thought", "mental", "therapy", "cognitive"],
            "history": ["history", "ancient", "historical", "civilization", "war", "king", "empire", "archaeology"],
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:3]  # Return top 3 topics
    
    def _extract_facts(self, user_input: str, response: str):
        """Extract and store important facts about the user."""
        facts = []
        
        # Name extraction
        name_match = re.search(r'my name is (\w+)', user_input, re.IGNORECASE)
        if name_match:
            name = name_match.group(1)
            self.user_profile["name"] = name
            facts.append({"type": "name", "value": name})
        
        # Age extraction
        age_match = re.search(r'i am (\d+) years old|age (\d+)', user_input, re.IGNORECASE)
        if age_match:
            age = age_match.group(1) or age_match.group(2)
            self.user_profile["age"] = age
            facts.append({"type": "age", "value": age})
        
        # Location extraction
        location_match = re.search(r'i (?:live|am from) in (\w+)', user_input, re.IGNORECASE)
        if location_match:
            location = location_match.group(1)
            self.user_profile["location"] = location
            facts.append({"type": "location", "value": location})
        
        # Occupation extraction
        occupation_match = re.search(r'(?:i am|i work as) (?:a|an)?\s*(\w+)', user_input, re.IGNORECASE)
        if occupation_match and not any(x in occupation_match.group(1).lower() for x in ['student', 'teacher', 'developer']):
            occupation = occupation_match.group(1)
            self.user_profile["occupation"] = occupation
            facts.append({"type": "occupation", "value": occupation})
        
        # Store facts in memory
        if facts:
            for fact in facts:
                # Check if fact already exists
                exists = False
                for mem in self.user_profile["memory"]["long_term"]:
                    if mem.get("type") == fact["type"]:
                        mem["value"] = fact["value"]
                        mem["updated"] = datetime.now().isoformat()
                        exists = True
                        break
                if not exists:
                    self.user_profile["memory"]["long_term"].append({
                        "type": fact["type"],
                        "value": fact["value"],
                        "added": datetime.now().isoformat()
                    })
        
        # Store emotional memory
        emotion = self._detect_emotion(user_input)
        if emotion != "neutral":
            self.user_profile["memory"]["emotional_memory"].append({
                "emotion": emotion,
                "trigger": user_input[:50],
                "timestamp": datetime.now().isoformat()
            })
            if len(self.user_profile["memory"]["emotional_memory"]) > 50:
                self.user_profile["memory"]["emotional_memory"] = self.user_profile["memory"]["emotional_memory"][-50:]
    
    def _update_context(self, user_input: str, response: str):
        """Update current conversation context."""
        # Detect topic
        topics = self._extract_topics(user_input)
        if topics:
            self.current_context["topic"] = topics[0]
        
        # Detect complexity level
        word_count = len(user_input.split())
        if word_count > 20:
            self.current_context["complexity_level"] = min(1.0, self.current_context["complexity_level"] + 0.1)
        elif word_count < 5:
            self.current_context["complexity_level"] = max(0.1, self.current_context["complexity_level"] - 0.05)
        
        # Detect engagement level
        if any(word in user_input.lower() for word in ['tell me', 'explain', 'describe', 'elaborate', 'more']):
            self.current_context["engagement_level"] = min(1.0, self.current_context["engagement_level"] + 0.1)
        elif any(word in user_input.lower() for word in ['ok', 'okay', 'fine', 'sure']):
            self.current_context["engagement_level"] = max(0.1, self.current_context["engagement_level"] - 0.05)
        
        # Store last response
        self.current_context["last_response"] = response
        
        # Check if follow-up is needed
        if '?' in user_input:
            self.current_context["follow_up_needed"] = False
        else:
            self.current_context["follow_up_needed"] = True
    
    def get_user_summary(self) -> Dict[str, Any]:
        """Get a comprehensive user summary."""
        return {
            "name": self.user_profile["name"],
            "age": self.user_profile["age"],
            "location": self.user_profile["location"],
            "occupation": self.user_profile["occupation"],
            "interests": self.user_profile["interests"],
            "personality": self.user_profile["personality"],
            "preferences": self.user_profile["preferences"],
            "behavior": self.user_profile["behavior"],
            "conversation_count": len(self.conversation_history),
            "recent_topics": self.current_context.get("topic"),
            "engagement": self.current_context.get("engagement_level", 0.5),
            "complexity": self.current_context.get("complexity_level", 0.5),
            "emotional_state": self.user_profile["personality"].get("emotional_state", "neutral"),
        }
    
    def get_personalized_response_style(self) -> Dict[str, Any]:
        """
        Get personalized response style based on user profile.
        This tells JARVIS HOW to respond to the user.
        """
        style = {
            "length": self.user_profile["preferences"].get("response_length", "medium"),
            "tone": self.user_profile["preferences"].get("tone", "professional"),
            "formality": self.user_profile["preferences"].get("formality", "moderate"),
            "curiosity_level": self.user_profile["behavior"].get("curiosity_level", 0.5),
            "analytical_level": self.user_profile["behavior"].get("analytical_level", 0.5),
            "creativity_level": self.user_profile["behavior"].get("creativity_level", 0.5),
            "emotional_state": self.user_profile["personality"].get("emotional_state", "neutral"),
            "frequent_topics": self.user_profile["behavior"].get("frequent_topics", [])[:5],
        }
        
        # Add personal facts if known
        if self.user_profile["name"]:
            style["name"] = self.user_profile["name"]
        if self.user_profile["location"]:
            style["location"] = self.user_profile["location"]
        if self.user_profile["occupation"]:
            style["occupation"] = self.user_profile["occupation"]
        
        # Determine greeting style
        if style["formality"] == "formal":
            style["greeting"] = "sir" if self.user_profile.get("name") else "sir"
        else:
            style["greeting"] = self.user_profile.get("name", "there")
        
        return style
    
    def get_personalized_response(self, base_response: str, user_input: str) -> str:
        """
        Take a base response and personalize it based on user profile.
        """
        style = self.get_personalized_response_style()
        response = base_response
        
        # Add name if known and appropriate
        if style.get("name") and not any(x in response.lower() for x in [style["name"].lower(), "sir"]):
            if len(response) > 50:
                # Add name naturally in the response
                parts = response.split('.')
                if len(parts) > 2:
                    response = f"{parts[0]}, {style['name']}.{' '.join(parts[1:])}"
                else:
                    response = f"{response}, {style['name']}."
        
        # Adjust response length based on preference
        if style["length"] == "short" and len(response) > 150:
            response = '. '.join(response.split('.')[:3]) + '.'
        elif style["length"] == "detailed" and len(response) < 50:
            # Add more context if response is too short
            response = response + " Let me know if you'd like more details on this."
        
        # Adjust tone based on preference
        if style["tone"] == "professional":
            # Already professional, keep as is
            pass
        elif style["tone"] == "friendly":
            # Make it more conversational
            if not any(word in response.lower() for word in ['hey', 'hi', 'thanks']):
                if response and response[0].upper():
                    response = response + " Let me know if that helps!"
        
        # Add curiosity engagement
        if style["curiosity_level"] > 0.7:
            if '?' not in response and len(response) > 20:
                response = response + " What else would you like to know about this?"
        
        # Add analytical engagement
        if style["analytical_level"] > 0.7:
            if len(response) > 30:
                response = response + " I can provide more detailed analysis if you're interested."
        
        # Add creativity engagement
        if style["creativity_level"] > 0.7:
            if not any(word in response for word in ['imagine', 'think', 'creative']):
                response = response + " There's also some interesting creative applications for this."
        
        return response
    
    def get_relevant_memory(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Get relevant conversation history based on query.
        Simple keyword matching for now.
        """
        relevant = []
        query_lower = query.lower()
        
        for conv in reversed(self.conversation_history):
            # Check if any keywords match
            if any(word in conv.get("user_input", "").lower() for word in query_lower.split() if len(word) > 3):
                relevant.append(conv)
                if len(relevant) >= limit:
                    break
        
        return relevant
    
    def get_emotional_context(self) -> Dict:
        """
        Get emotional context based on recent conversations.
        """
        emotions = []
        for conv in self.conversation_history[-20:]:
            if conv.get("emotion"):
                emotions.append(conv["emotion"])
        
        if not emotions:
            return {"current": "neutral", "trend": "stable"}
        
        # Count emotions
        emotion_counts = defaultdict(int)
        for e in emotions:
            emotion_counts[e] += 1
        
        most_common = max(emotion_counts.items(), key=lambda x: x[1])
        
        # Determine trend
        if len(emotions) > 10:
            recent = emotions[-5:]
            if all(e == most_common[0] for e in recent):
                trend = "consistent"
            elif any(e in ["joyful", "curious"] for e in recent) and any(e in ["sad", "angry"] for e in recent):
                trend = "fluctuating"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "current": most_common[0],
            "frequency": most_common[1],
            "trend": trend,
            "recent": emotions[-5:]
        }
    
    def get_conversation_analytics(self) -> Dict:
        """
        Get advanced conversation analytics.
        """
        history = self.conversation_history
        if not history:
            return {"message": "No conversation data yet"}
        
        # Calculate statistics
        total = len(history)
        user_words = sum(len(conv.get("user_input", "").split()) for conv in history)
        response_words = sum(len(conv.get("response", "").split()) for conv in history)
        
        # Time analysis
        times = []
        for conv in history:
            if conv.get("timestamp"):
                try:
                    dt = datetime.fromisoformat(conv["timestamp"])
                    times.append(dt.hour)
                except:
                    pass
        
        if times:
            hour_counts = defaultdict(int)
            for h in times:
                hour_counts[h] += 1
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else None
            peak_time = f"{peak_hour}:00" if peak_hour is not None else "Unknown"
        else:
            peak_time = "Unknown"
        
        # Topic analysis
        topics = []
        for conv in history:
            extracted = self._extract_topics(conv.get("user_input", ""))
            topics.extend(extracted)
        
        topic_counts = defaultdict(int)
        for t in topics:
            topic_counts[t] += 1
        frequent_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Emotion analysis
        emotions = []
        for conv in history:
            if conv.get("emotion"):
                emotions.append(conv["emotion"])
        
        emotion_counts = defaultdict(int)
        for e in emotions:
            emotion_counts[e] += 1
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else "neutral"
        
        return {
            "total_conversations": total,
            "user_words": user_words,
            "response_words": response_words,
            "avg_user_words": user_words / total if total > 0 else 0,
            "avg_response_words": response_words / total if total > 0 else 0,
            "peak_activity_time": peak_time,
            "frequent_topics": frequent_topics,
            "dominant_emotion": dominant_emotion,
            "emotional_trend": self.get_emotional_context().get("trend", "stable")
        }