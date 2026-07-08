"""
moa/workflows/memory_workflow.py
Memory Workflow - Generic personal memory system
"""

from .base_workflow import BaseWorkflow
import json
import os
from pathlib import Path


class MemoryWorkflow(BaseWorkflow):
    """Workflow for generic personal memory storage and recall."""
    
    def __init__(self, orchestrator):
        super().__init__(orchestrator)
        self.memory_file = Path(__file__).parent.parent / "data" / "user_memory.json"
        self.memory_file.parent.mkdir(exist_ok=True)
        self._load_memory()
    
    def _load_memory(self):
        """Load user memory from file."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r') as f:
                    self.memory = json.load(f)
            except:
                self.memory = {}
        else:
            self.memory = {}
    
    def _save_memory(self):
        """Save user memory to file."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def _format_key(self, key: str) -> str:
        """Format a key for display."""
        key_map = {
            "user.name": "Name",
            "user.birthday": "Birthday",
            "user.occupation": "Occupation",
            "user.pet": "Pet Name",
            "family.mother": "Mother's Name",
            "family.father": "Father's Name",
            "location.city": "City",
            "preferences.favorite_color": "Favorite Color",
            "preferences.favorite_food": "Favorite Food",
            "preferences.likes": "Likes",
        }
        return key_map.get(key, key.replace("_", " ").title())
    
    async def run(self, **kwargs) -> dict:
        """Run memory workflow."""
        action = kwargs.get("action", "")
        
        if action == "remember_fact":
            key = kwargs.get("key", "").strip()
            value = kwargs.get("value", "").strip()
            
            if not key or not value:
                return {
                    "success": False,
                    "error": "Missing key or value",
                    "answer": "I need both a key and a value to remember.",
                    "mode": "memory"
                }
            
            # Store the fact
            self.memory[key] = value
            self._save_memory()
            
            formatted_key = self._format_key(key)
            return {
                "success": True,
                "answer": f"✅ I'll remember that! Your {formatted_key} is {value}.",
                "mode": "memory",
                "action": "remember_fact",
                "key": key,
                "value": value
            }
        
        elif action == "remember_facts":
            facts = kwargs.get("facts", [])
            if not facts:
                return {
                    "success": False,
                    "error": "No facts provided",
                    "answer": "What would you like me to remember?",
                    "mode": "memory"
                }
            
            remembered = []
            for fact in facts:
                if isinstance(fact, dict):
                    key = fact.get("key")
                    value = fact.get("value")
                else:
                    key = getattr(fact, "key", None)
                    value = getattr(fact, "value", None)
                
                if key and value:
                    self.memory[key] = value
                    remembered.append(f"{self._format_key(key)}: {value}")
            
            self._save_memory()
            
            if remembered:
                fact_list = "\n".join([f"  • {f}" for f in remembered])
                return {
                    "success": True,
                    "answer": f"✅ I've remembered {len(remembered)} facts about you!\n\n📝 Updated Profile:\n{fact_list}",
                    "mode": "memory",
                    "action": "remember_facts",
                    "facts": remembered
                }
            else:
                return {
                    "success": False,
                    "error": "No valid facts to remember",
                    "answer": "I couldn't extract any facts from that.",
                    "mode": "memory"
                }
        
        elif action == "recall_fact":
            key = kwargs.get("key", "").strip()
            
            if not key:
                return {
                    "success": False,
                    "error": "Missing key",
                    "answer": "What would you like me to recall?",
                    "mode": "memory"
                }
            
            value = self.memory.get(key)
            formatted_key = self._format_key(key)
            
            if value:
                return {
                    "success": True,
                    "answer": f"Your {formatted_key} is {value}. I remember! 👋",
                    "mode": "memory",
                    "action": "recall_fact",
                    "key": key,
                    "value": value
                }
            else:
                return {
                    "success": False,
                    "answer": f"I don't know your {formatted_key} yet. Tell me to remember it!",
                    "mode": "memory",
                    "action": "recall_fact",
                    "key": key,
                    "value": None
                }
        
        elif action == "clear_memory":
            old_memory = self.memory.copy()
            self.memory = {}
            self._save_memory()
            
            if old_memory:
                fact_count = len(old_memory)
                return {
                    "success": True,
                    "answer": f"🧹 I've forgotten everything about you! ({fact_count} facts cleared)",
                    "mode": "memory",
                    "action": "clear_memory",
                    "cleared": old_memory
                }
            else:
                return {
                    "success": True,
                    "answer": "🧹 Memory was already empty. Nothing to clear.",
                    "mode": "memory",
                    "action": "clear_memory"
                }
        
        elif action == "get_all_memory":
            if self.memory:
                facts = []
                for key, value in self.memory.items():
                    formatted_key = self._format_key(key)
                    facts.append(f"  • {formatted_key}: {value}")
                
                fact_list = "\n".join(facts)
                return {
                    "success": True,
                    "answer": f"📝 Here's what I remember about you:\n{fact_list}",
                    "mode": "memory",
                    "action": "get_all_memory",
                    "memory": self.memory
                }
            else:
                return {
                    "success": True,
                    "answer": "📝 I don't remember anything about you yet. Tell me some facts!",
                    "mode": "memory",
                    "action": "get_all_memory",
                    "memory": {}
                }
        
        else:
            return {
                "success": False,
                "error": f"Unknown memory action: {action}",
                "answer": "I don't understand that memory command.",
                "mode": "memory"
            }