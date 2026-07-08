"""
moa/auto_corrector.py
Auto-Correction Module - Fixes typos before intent detection
"""

import re
from typing import Dict, List, Optional


class AutoCorrector:
    """
    Auto-corrects common typos and speech recognition errors.
    
    Features:
    - Common word corrections
    - Phonetic corrections
    - Context-aware corrections
    - Partial word matching
    """
    
    def __init__(self):
        # Common corrections - MORE CAREFUL WITH "name"
        self.corrections = {
            # App names
            "opne": "open",
            "opoen": "open",
            "oppen": "open",
            "calcualtor": "calculator",
            "calculater": "calculator",
            "notpad": "notepad",
            "notepadd": "notepad",
            "nootpad": "notepad",
            "chorme": "chrome",
            "chrom": "chrome",
            "chome": "chrome",
            "vscode": "visual studio code",
            "vs code": "visual studio code",
            "firefos": "firefox",
            "friefox": "firefox",
            
            # Weather
            "wheater": "weather",
            "weater": "weather",
            "wethere": "weather",
            "forecat": "forecast",
            "forcast": "forecast",
            "forcaste": "forecast",
            "temp": "temperature",
            "temprature": "temperature",
            "tempreture": "temperature",
            
            # Time
            "timee": "time",
            "tiem": "time",
            "tme": "time",
            
            # Location
            "locaton": "location",
            "loction": "location",
            "locaion": "location",
            "where am i": "where am i",
            
            # Memory - FIXED: Don't over-correct "name"
            # Only correct exact typos, not "name" itself
            "nmae": "name",      # typo
            "anme": "name",      # typo
            "amne": "name",      # typo
            "nam": "name",       # partial
            "mather": "mother",
            "moter": "mother",
            "mothr": "mother",
            "fahter": "father",
            "fater": "father",
            "fathr": "father",
            
            # System
            "staus": "status",
            "statis": "status",
            "statut": "status",
            "sytem": "system",
            "systm": "system",
            
            # Common typos
            "waht": "what",
            "whta": "what",
            "wht": "what",
            "wat": "what",
            "wuat": "what",
            "isnt": "isn't",
            "arent": "aren't",
            "dont": "don't",
            "didnt": "didn't",
            "wont": "won't",
            "shouldnt": "shouldn't",
            "wouldnt": "wouldn't",
            "couldnt": "couldn't",
            "coudl": "could",
            "shoudl": "should",
            "woudl": "would",
            "becuase": "because",
            "becase": "because",
            "becaus": "because",
            
            # Voice recognition typos
            "wise": "voice",
            "exsit": "exit",
            "exict": "exit",
            "exti": "exit",
            "quitt": "quit",
            "stap": "stop",
            "stpp": "stop",
            "stoop": "stop",
            "cancle": "cancel",
            "cancell": "cancel",
            
            # Multi-word
            "chat gpt": "chatgpt",
            "chatgpt": "chatgpt",
            "micro soft": "microsoft",
            "microsft": "microsoft",
            "microsof": "microsoft",
            "microsoft store": "microsoft store",
            
            # Agent names
            "securty": "security",
            "seciruty": "security",
            "secrutiy": "security",
            "memmory": "memory",
            "memroy": "memory",
            "memry": "memory",
            "browser": "browser",
            "brower": "browser",
            "broswer": "browser",
            "browsr": "browser",
            "supervisor": "supervisor",
            "supervisr": "supervisor",
            "supervsor": "supervisor",
            "superisor": "supervisor",
        }
        
        # Word patterns for partial matching - BE MORE CAREFUL
        self.patterns = [
            # Only correct obvious typos
            (r'\b(\w{2})me\b', r'\1 name'),  # "anme" -> "name"
            (r'\b(\w{2})ther\b', r'\1ther'),  # "mther" -> "mother"
            (r'\b(\w{2})ter\b', r'\1ther'),   # "fater" -> "father"
        ]
        
        # Map common "agent" name typos
        self.agent_corrections = {
            "sec": "security",
            "secu": "security",
            "secur": "security",
            "mem": "memory",
            "memor": "memory",
            "super": "supervisor",
            "superv": "supervisor",
            "brow": "browser",
            "brows": "browser",
            "voice": "voice",
            "vision": "vision",
            "llm": "llm",
        }
    
    def correct(self, text: str) -> str:
        """
        Auto-correct a text string.
        
        Args:
            text: The text to correct
            
        Returns:
            The corrected text
        """
        if not text:
            return text
        
        original = text
        corrected = text.lower().strip()
        
        # Split into words
        words = corrected.split()
        corrected_words = []
        
        i = 0
        while i < len(words):
            word = words[i]
            
            # Check for multi-word corrections
            multi_corrected = False
            if i + 1 < len(words):
                multi_word = f"{word} {words[i+1]}"
                if multi_word in self.corrections:
                    corrected_words.append(self.corrections[multi_word])
                    i += 2
                    multi_corrected = True
            
            if not multi_corrected:
                # Check if word needs correction
                if word in self.corrections:
                    corrected_words.append(self.corrections[word])
                else:
                    # Check for partial matches
                    found = False
                    for pattern, replacement in self.patterns:
                        match = re.search(pattern, word)
                        if match:
                            corrected_words.append(re.sub(pattern, replacement, word))
                            found = True
                            break
                    
                    if not found:
                        # Check agent name corrections
                        if word in self.agent_corrections:
                            corrected_words.append(self.agent_corrections[word])
                        else:
                            # Try to find partial match in corrections
                            # BUT BE CAREFUL - don't over-correct
                            found = False
                            for wrong, right in self.corrections.items():
                                if len(wrong) >= 3 and wrong in word and word != "name":
                                    # Only replace if it's a clear typo
                                    if len(word) - len(wrong) <= 2:  # Only if it's a close match
                                        corrected_words.append(word.replace(wrong, right))
                                        found = True
                                        break
                            
                            if not found:
                                corrected_words.append(word)
            
            i += 1
        
        result = " ".join(corrected_words)
        
        # Fix common phrase issues
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()
        
        if result != original:
            print(f"🔧 Auto-correct: '{original}' -> '{result}'")
        
        return result
    
    def correct_command(self, text: str) -> str:
        """
        Specialized correction for command phrases.
        
        Handles:
        - "what about security" -> "check security"
        - "how is security" -> "check security"
        - "tell me about security" -> "check security"
        """
        text = text.lower().strip()
        
        # Agent status phrases
        if "what about" in text:
            agent = text.split("what about")[-1].strip()
            return f"check {agent}"
        
        if "how is" in text and "agent" in text:
            agent = text.split("how is")[-1].strip()
            if "agent" in agent:
                agent = agent.replace("agent", "").strip()
            return f"check {agent} agent"
        
        if "tell me about" in text and "agent" in text:
            agent = text.split("tell me about")[-1].strip()
            if "agent" in agent:
                agent = agent.replace("agent", "").strip()
            return f"check {agent} agent"
        
        # Time/date phrases
        if "time now" in text or "current time" in text:
            return "what time is it"
        
        if "today date" in text or "current date" in text:
            return "what is today's date"
        
        # Weather phrases
        if "weather today" in text or "today weather" in text:
            return "weather"
        
        if "temperature today" in text:
            return "weather"
        
        # Memory recall - DON'T over-correct
        if "what is my name" in text or "what's my name" in text:
            return "what is my name"
        
        if "what is my mother name" in text:
            return "what is my mother name"
        
        return text