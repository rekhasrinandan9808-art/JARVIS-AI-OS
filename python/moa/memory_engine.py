"""
moa/memory_engine.py
Advanced Memory Engine - Vector-based memory with ChromaDB
Singleton pattern - only loads once
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("chromadb not installed. Run: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not installed. Run: pip install sentence-transformers")

logger = logging.getLogger("jarvis.memory_engine")

# =================================================
# SINGLETON INSTANCE
# =================================================
_engine_instance = None


def get_memory_engine(persist_dir: str = None):
    """Get the singleton MemoryEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MemoryEngine(persist_dir)
    return _engine_instance


class MemoryEngine:
    """
    Advanced memory system using ChromaDB for vector storage.
    Singleton - only loads models once.
    """
    
    def __init__(self, persist_dir: str = None):
        if not CHROMADB_AVAILABLE or not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error("ChromaDB or sentence-transformers not available")
            raise ImportError("Required packages not installed")
            
        if persist_dir is None:
            persist_dir = Path(__file__).parent.parent / "data" / "chromadb"
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        logger.info("Initializing ChromaDB...")
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize embedding model (local, fast) - ONLY LOADS ONCE
        logger.info("Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
        
        # Collections
        self.conversations = self.client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"}
        )
        self.facts = self.client.get_or_create_collection(
            name="facts",
            metadata={"hnsw:space": "cosine"}
        )
        self.preferences = self.client.get_or_create_collection(
            name="preferences",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Short-term memory buffer (last N conversations)
        self.short_term_buffer = []
        self.max_short_term = 20
        
        logger.info(f"MemoryEngine initialized with {self._count_collections()} total items")
    
    def _count_collections(self) -> int:
        """Count total items across all collections."""
        try:
            return (
                self.conversations.count() +
                self.facts.count() +
                self.preferences.count()
            )
        except:
            return 0
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text."""
        return self.embedder.encode(text).tolist()
    
    def _generate_id(self) -> str:
        """Generate a unique ID with timestamp."""
        return f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    # ==========================================
    # CONVERSATION MEMORY
    # ==========================================
    
    def add_conversation(self, user_input: str, response: str, metadata: Dict = None) -> str:
        """Store a conversation turn."""
        text = f"User: {user_input}\nAssistant: {response}"
        embedding = self._get_embedding(text)
        doc_id = self._generate_id()
        
        meta = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input[:500],
            "response": response[:500],
            "type": "conversation"
        }
        if metadata:
            meta.update(metadata)
        
        # Add to short-term buffer
        self.short_term_buffer.append({
            "user_input": user_input,
            "response": response,
            "timestamp": meta["timestamp"]
        })
        if len(self.short_term_buffer) > self.max_short_term:
            self.short_term_buffer.pop(0)
        
        # Add to long-term vector DB
        try:
            self.conversations.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[text]
            )
        except Exception as e:
            logger.error(f"Failed to add conversation: {e}")
        
        logger.debug(f"Added conversation: {doc_id}")
        return doc_id
    
    def get_recent_conversations(self, limit: int = 5) -> List[Dict]:
        """Get recent conversations from short-term buffer."""
        return self.short_term_buffer[-limit:] if self.short_term_buffer else []
    
    def search_conversations(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for relevant past conversations."""
        try:
            embedding = self._get_embedding(query)
            results = self.conversations.query(
                query_embeddings=[embedding],
                n_results=limit
            )
            
            conversations = []
            if results and results.get('metadatas'):
                for i in range(len(results['metadatas'][0])):
                    conversations.append({
                        'user_input': results['metadatas'][0][i].get('user_input', ''),
                        'response': results['metadatas'][0][i].get('response', ''),
                        'timestamp': results['metadatas'][0][i].get('timestamp', ''),
                        'distance': results['distances'][0][i] if results.get('distances') else None
                    })
            return conversations
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []
    
    def get_conversation_context(self, query: str, limit: int = 3) -> str:
        """Get formatted context from relevant past conversations."""
        conversations = self.search_conversations(query, limit)
        if not conversations:
            return ""
        
        context = "Previous relevant conversations:\n"
        for conv in conversations:
            context += f"- User: {conv['user_input']}\n"
            context += f"  Assistant: {conv['response']}\n"
        return context
    
    # ==========================================
    # FACT MEMORY
    # ==========================================
    
    def add_fact(self, key: str, value: str, category: str = "user") -> str:
        """Store a fact."""
        text = f"{category}.{key}: {value}"
        embedding = self._get_embedding(text)
        doc_id = self._generate_id()
        
        meta = {
            "key": key,
            "value": value,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "type": "fact"
        }
        
        try:
            self.facts.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[text]
            )
        except Exception as e:
            logger.error(f"Failed to add fact: {e}")
        
        logger.info(f"Added fact: {category}.{key} = {value}")
        return doc_id
    
    def recall_fact(self, query: str, limit: int = 5) -> List[Dict]:
        """Recall facts semantically."""
        try:
            embedding = self._get_embedding(query)
            results = self.facts.query(
                query_embeddings=[embedding],
                n_results=limit
            )
            
            facts = []
            if results and results.get('metadatas'):
                for i in range(len(results['metadatas'][0])):
                    facts.append({
                        'key': results['metadatas'][0][i].get('key', ''),
                        'value': results['metadatas'][0][i].get('value', ''),
                        'category': results['metadatas'][0][i].get('category', ''),
                        'distance': results['distances'][0][i] if results.get('distances') else None
                    })
            return facts
        except Exception as e:
            logger.error(f"Recall error: {e}")
            return []
    
    def recall_fact_by_key(self, key: str) -> Optional[str]:
        """Recall a specific fact by key."""
        try:
            results = self.facts.get(where={"key": key})
            if results and results.get('metadatas'):
                for meta in results['metadatas']:
                    if meta.get('key') == key:
                        return meta.get('value')
            return None
        except Exception as e:
            logger.error(f"Recall by key error: {e}")
            return None
    
    # ==========================================
    # PREFERENCE LEARNING
    # ==========================================
    
    def learn_preference(self, key: str, value: Any, context: str = "") -> str:
        """Learn a user preference."""
        text = f"Preference: {key} = {value}"
        if context:
            text += f" (Context: {context})"
        
        embedding = self._get_embedding(text)
        doc_id = self._generate_id()
        
        meta = {
            "key": key,
            "value": str(value),
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "type": "preference",
            "confidence": 0.5
        }
        
        # Check if preference exists
        existing = self.get_preference(key)
        if existing:
            meta["confidence"] = min(1.0, existing.get("confidence", 0.5) + 0.1)
            self._delete_preference(key)
        
        try:
            self.preferences.add(
                ids=[doc_id],
                embeddings=[embedding],
                metadatas=[meta],
                documents=[text]
            )
        except Exception as e:
            logger.error(f"Failed to learn preference: {e}")
        
        logger.info(f"Learned preference: {key} = {value} (confidence: {meta['confidence']})")
        return doc_id
    
    def get_preference(self, key: str) -> Optional[Dict]:
        """Get a specific preference."""
        try:
            results = self.preferences.get(where={"key": key})
            if results and results.get('metadatas'):
                for meta in results['metadatas']:
                    if meta.get('key') == key:
                        return {
                            "key": meta.get('key'),
                            "value": meta.get('value'),
                            "confidence": meta.get('confidence', 0.5),
                            "timestamp": meta.get('timestamp')
                        }
            return None
        except Exception as e:
            logger.error(f"Get preference error: {e}")
            return None
    
    def get_all_preferences(self) -> List[Dict]:
        """Get all learned preferences."""
        try:
            results = self.preferences.get()
            preferences = []
            if results and results.get('metadatas'):
                for meta in results['metadatas']:
                    if meta.get('type') == 'preference':
                        preferences.append({
                            "key": meta.get('key'),
                            "value": meta.get('value'),
                            "confidence": meta.get('confidence', 0.5)
                        })
            return preferences
        except Exception as e:
            logger.error(f"Get all preferences error: {e}")
            return []
    
    def _delete_preference(self, key: str) -> None:
        """Delete a preference by key."""
        try:
            results = self.preferences.get(where={"key": key})
            if results and results.get('ids'):
                self.preferences.delete(ids=results['ids'])
        except Exception as e:
            logger.error(f"Delete preference error: {e}")
    
    def infer_preferences(self, user_input: str, response: str) -> None:
        """Infer preferences from conversation."""
        text = user_input.lower()
        
        preference_patterns = [
            (r"i like (\w+)", "likes"),
            (r"i love (\w+)", "likes"),
            (r"i prefer (\w+)", "preference"),
            (r"my favorite (\w+) is (\w+)", "favorite"),
            (r"i use (\w+)", "tools"),
            (r"i work with (\w+)", "tools"),
            (r"i live in (\w+)", "location"),
            (r"i'm from (\w+)", "location"),
            (r"my name is (\w+)", "identity"),
            (r"call me (\w+)", "identity"),
        ]
        
        import re
        for pattern, category in preference_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    key = f"{category}.{match.group(1)}"
                    value = match.group(1)
                else:
                    key = f"{category}.{match.group(1)}"
                    value = match.group(2)
                
                self.learn_preference(key, value, context=user_input)
                logger.info(f"Inferred preference: {key} = {value}")
    
    # ==========================================
    # CONTEXT AUGMENTATION
    # ==========================================
    
    def get_augmented_context(self, query: str, include_preferences: bool = True) -> str:
        """Get augmented context."""
        context_parts = []
        
        recent = self.get_recent_conversations(limit=3)
        if recent:
            context_parts.append("Recent conversation:\n")
            for conv in recent:
                context_parts.append(f"User: {conv['user_input']}")
                context_parts.append(f"Assistant: {conv['response']}")
            context_parts.append("")
        
        past = self.search_conversations(query, limit=2)
        if past:
            context_parts.append("Relevant past conversations:\n")
            for conv in past:
                context_parts.append(f"User: {conv['user_input']}")
                context_parts.append(f"Assistant: {conv['response']}")
            context_parts.append("")
        
        if include_preferences:
            preferences = self.get_all_preferences()
            if preferences:
                context_parts.append("Known user preferences:\n")
                for pref in preferences:
                    if pref.get('confidence', 0) > 0.6:
                        context_parts.append(f"- {pref['key']}: {pref['value']}")
                context_parts.append("")
        
        return "\n".join(context_parts)
    
    # ==========================================
    # MAINTENANCE
    # ==========================================
    
    def clear_short_term(self) -> None:
        """Clear short-term memory buffer."""
        self.short_term_buffer = []
    
    def clear_all(self) -> None:
        """Clear all memory (dangerous!)."""
        try:
            if self.conversations.get() and self.conversations.get()['ids']:
                self.conversations.delete(ids=self.conversations.get()['ids'])
            if self.facts.get() and self.facts.get()['ids']:
                self.facts.delete(ids=self.facts.get()['ids'])
            if self.preferences.get() and self.preferences.get()['ids']:
                self.preferences.delete(ids=self.preferences.get()['ids'])
        except Exception as e:
            logger.error(f"Clear all error: {e}")
        
        self.short_term_buffer = []
        logger.warning("All memory cleared!")
    
    def get_stats(self) -> Dict[str, int]:
        """Get memory statistics."""
        return {
            "conversations": self.conversations.count(),
            "facts": self.facts.count(),
            "preferences": self.preferences.count(),
            "short_term": len(self.short_term_buffer)
        }