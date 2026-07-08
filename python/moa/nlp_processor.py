"""
moa/nlp_processor.py
Natural Language Processing Layer - Smarter understanding before planning
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ExtractedFact:
    """A fact extracted from natural language."""
    key: str
    value: str
    confidence: float = 1.0


@dataclass
class NLPResult:
    """Result from NLP processing."""
    intent: str
    facts: List[ExtractedFact] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    command: Optional[str] = None
    confidence: float = 1.0
    original_text: str = ""


class NLPProcessor:
    """
    Natural Language Processing Layer for JARVIS.
    
    Handles:
    - Text normalization and autocorrection
    - Intent detection
    - Entity extraction
    - Multi-fact extraction
    - Reference resolution
    """
    
    # Common spelling corrections
    SPELLING_CORRECTIONS = {
        "wmy": "my",
        "whaty": "what",
        "wats": "what's",
        "wat": "what",
        "nmae": "name",
        "anme": "name",
        "amne": "name",
        "mather": "mother",
        "fahter": "father",
        "favarite": "favorite",
        "favourite": "favorite",
        "collor": "color",
        "colour": "color",
        "citty": "city",
        "hyderbad": "hyderabad",
        "banaglore": "bangalore",
        "mumbia": "mumbai",
        "delhi": "delhi",
        "chennai": "chennai",
        "calcutta": "kolkata",
        "wise": "voice",
        "exsit": "exit",
        "quit": "exit",
        "stap": "stop",
    }
    
    # Fact extraction patterns
    FACT_PATTERNS = [
        # "my name is nandan" -> user.name
        {
            "pattern": r"my\s+name\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "user.name",
            "priority": 10
        },
        # "my mother's name is jayalaxmi" -> family.mother
        {
            "pattern": r"my\s+mother['']?s?\s+name\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "family.mother",
            "priority": 10
        },
        # "my father's name is john" -> family.father
        {
            "pattern": r"my\s+father['']?s?\s+name\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "family.father",
            "priority": 10
        },
        # "my favorite color is blue" -> preferences.favorite_color
        {
            "pattern": r"my\s+favorite\s+color\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "preferences.favorite_color",
            "priority": 9
        },
        # "my favorite food is pizza" -> preferences.favorite_food
        {
            "pattern": r"my\s+favorite\s+food\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "preferences.favorite_food",
            "priority": 9
        },
        # "i live in hyderabad" -> location.city
        {
            "pattern": r"i\s+live\s+in\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "location.city",
            "priority": 8
        },
        # "i am from hyderabad" -> location.city
        {
            "pattern": r"i\s+am\s+from\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "location.city",
            "priority": 8
        },
        # "i like pizza" -> preferences.likes
        {
            "pattern": r"i\s+like\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "preferences.likes",
            "priority": 7
        },
        # "my birthday is january 1st" -> user.birthday
        {
            "pattern": r"my\s+birthday\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "user.birthday",
            "priority": 8
        },
        # "my pet name is max" -> user.pet
        {
            "pattern": r"my\s+pet\s+name\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "user.pet",
            "priority": 8
        },
        # "my occupation is engineer" -> user.occupation
        {
            "pattern": r"my\s+occupation\s+is\s+(.+?)(?:\s*$|\.|\!|\?)",
            "key": "user.occupation",
            "priority": 8
        },
    ]
    
    # Question patterns for recall
    RECALL_PATTERNS = [
        {
            "pattern": r"what\s+is\s+my\s+name",
            "key": "user.name",
            "question": "what is my name"
        },
        {
            "pattern": r"what['']?s\s+my\s+name",
            "key": "user.name",
            "question": "what's my name"
        },
        {
            "pattern": r"what\s+is\s+my\s+mother['']?s?\s+name",
            "key": "family.mother",
            "question": "what is my mother's name"
        },
        {
            "pattern": r"what['']?s\s+my\s+mother['']?s?\s+name",
            "key": "family.mother",
            "question": "what's my mother's name"
        },
        {
            "pattern": r"what\s+is\s+my\s+father['']?s?\s+name",
            "key": "family.father",
            "question": "what is my father's name"
        },
        {
            "pattern": r"what\s+is\s+my\s+favorite\s+color",
            "key": "preferences.favorite_color",
            "question": "what is my favorite color"
        },
        {
            "pattern": r"where\s+do\s+i\s+live",
            "key": "location.city",
            "question": "where do i live"
        },
        {
            "pattern": r"where\s+am\s+i\s+from",
            "key": "location.city",
            "question": "where am i from"
        },
        {
            "pattern": r"what\s+do\s+i\s+like",
            "key": "preferences.likes",
            "question": "what do i like"
        },
        {
            "pattern": r"when\s+is\s+my\s+birthday",
            "key": "user.birthday",
            "question": "when is my birthday"
        },
        {
            "pattern": r"what\s+is\s+my\s+pet\s+name",
            "key": "user.pet",
            "question": "what is my pet name"
        },
        {
            "pattern": r"what\s+is\s+my\s+occupation",
            "key": "user.occupation",
            "question": "what is my occupation"
        },
    ]
    
    def __init__(self):
        self.fact_patterns = self.FACT_PATTERNS
        self.recall_patterns = self.RECALL_PATTERNS
        self.spell_corrections = self.SPELLING_CORRECTIONS
    
    def normalize_text(self, text: str) -> str:
        """
        Normalize text for processing.
        
        Steps:
        1. Lowercase
        2. Remove extra spaces
        3. Basic spelling correction for common typos
        """
        # Lowercase
        text = text.lower().strip()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Split into words for spelling correction
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Check if word needs correction
            if word in self.spell_corrections:
                corrected_words.append(self.spell_corrections[word])
            else:
                # Check for partial matches (e.g., "exsit" -> "exit")
                corrected = False
                for wrong, right in self.spell_corrections.items():
                    if word.startswith(wrong) or word.endswith(wrong):
                        # Replace the wrong part
                        if word.startswith(wrong):
                            corrected_words.append(right + word[len(wrong):])
                        else:
                            corrected_words.append(word[:len(word)-len(wrong)] + right)
                        corrected = True
                        break
                if not corrected:
                    corrected_words.append(word)
        
        return " ".join(corrected_words)
    
    def extract_facts(self, text: str) -> List[ExtractedFact]:
        """
        Extract facts from text.
        
        Returns:
            List of ExtractedFact objects
        """
        facts = []
        text_lower = text.lower()
        
        # Sort patterns by priority (higher first)
        sorted_patterns = sorted(self.fact_patterns, key=lambda x: x.get("priority", 0), reverse=True)
        
        for pattern_info in sorted_patterns:
            pattern = pattern_info["pattern"]
            key = pattern_info["key"]
            
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up the value
                value = re.sub(r'[,;.!?]+$', '', value).strip()
                if value and len(value) > 0:
                    facts.append(ExtractedFact(
                        key=key,
                        value=value,
                        confidence=0.95
                    ))
                    # Remove this fact from text to avoid duplicate extraction
                    text_lower = text_lower.replace(match.group(0), "")
        
        return facts
    
    def extract_multiple_facts(self, text: str) -> List[ExtractedFact]:
        """
        Extract multiple facts from a single sentence.
        
        Handles:
        - "My name is Nandan and my mother's name is Jayalaxmi"
        - "My name is Nandan, my mother's name is Jayalaxmi, and I live in Hyderabad"
        """
        # First, try to split on common separators
        separators = [" and ", ", and ", ", ", "; "]
        
        # Try to split the text
        segments = [text]
        for sep in separators:
            new_segments = []
            for seg in segments:
                if sep in seg:
                    parts = seg.split(sep)
                    new_segments.extend(parts)
                else:
                    new_segments.append(seg)
            segments = new_segments
        
        # Also try splitting on periods
        if len(segments) == 1:
            segments = text.split(".")
        
        # Extract facts from each segment
        all_facts = []
        for segment in segments:
            segment = segment.strip()
            if segment:
                facts = self.extract_facts(segment)
                all_facts.extend(facts)
        
        return all_facts
    
    def detect_recall_intent(self, text: str) -> Optional[str]:
        """
        Detect if the text is asking to recall a fact.
        
        Returns:
            The key to recall, or None if not a recall request
        """
        text_lower = text.lower()
        
        for pattern_info in self.recall_patterns:
            pattern = pattern_info["pattern"]
            key = pattern_info["key"]
            
            if re.search(pattern, text_lower, re.IGNORECASE):
                return key
        
        # Check for generic "what do you remember about me"
        if re.search(r"what\s+do\s+you\s+remember\s+about\s+me", text_lower, re.IGNORECASE):
            return "__ALL__"
        
        return None
    
    def detect_command_intent(self, text: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Detect if the text is a system command.
        
        Returns:
            Tuple of (command, params) or (None, None)
        """
        text_lower = text.lower()
        
        # App launch commands
        app_patterns = [
            r"open\s+(\w+)",
            r"launch\s+(\w+)",
            r"start\s+(\w+)",
            r"run\s+(\w+)",
        ]
        
        for pattern in app_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                app_name = match.group(1)
                return ("launch_app", {"app": app_name})
        
        return (None, None)
    
    def process(self, text: str) -> NLPResult:
        """
        Full NLP processing pipeline.
        
        Steps:
        1. Normalize text
        2. Detect intent
        3. Extract entities
        4. Extract facts
        """
        original_text = text
        normalized = self.normalize_text(text)
        
        # Detect recall intent
        recall_key = self.detect_recall_intent(normalized)
        if recall_key:
            if recall_key == "__ALL__":
                return NLPResult(
                    intent="recall_all_facts",
                    facts=[],
                    entities={},
                    command=None,
                    confidence=1.0,
                    original_text=original_text
                )
            else:
                return NLPResult(
                    intent="recall_fact",
                    facts=[],
                    entities={"key": recall_key},
                    command=None,
                    confidence=1.0,
                    original_text=original_text
                )
        
        # Extract multiple facts
        facts = self.extract_multiple_facts(normalized)
        if facts:
            return NLPResult(
                intent="remember_facts",
                facts=facts,
                entities={},
                command=None,
                confidence=0.95,
                original_text=original_text
            )
        
        # Detect command intent
        command, params = self.detect_command_intent(normalized)
        if command:
            return NLPResult(
                intent=command,
                facts=[],
                entities=params or {},
                command=command,
                confidence=0.9,
                original_text=original_text
            )
        
        # Default: return as-is for further processing
        return NLPResult(
            intent="unknown",
            facts=[],
            entities={},
            command=None,
            confidence=0.5,
            original_text=original_text
        )