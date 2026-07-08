"""
moa/text_normalizer.py
Text Normalizer - Fixes math symbols, abbreviations, etc. for speech
"""

import re
from typing import Optional, Dict, List, Tuple, Union


class TextNormalizer:
    """
    Normalizes text for speech and display.
    """
    
    def __init__(self):
        # Math symbol replacements
        self.math_replacements = {
            "²": " squared",
            "³": " cubed",
            "¹": " to the first",
            "½": " half",
            "¼": " quarter",
            "¾": " three quarters",
            "∞": " infinity",
            "π": " pi",
            "√": " square root of",
            "∑": " sum of",
            "∫": " integral of",
            "±": " plus or minus",
            "≠": " not equal to",
            "≈": " approximately equal to",
            "≤": " less than or equal to",
            "≥": " greater than or equal to",
        }
        
        # Pattern replacements
        self.patterns = [
            # E=mc² -> E equals M C squared
            (r"E\s*=\s*mc\s*[\^]?\s*2", "E equals M C squared"),
            (r"E\s*=\s*mc²", "E equals M C squared"),
            (r"mc²", "M C squared"),
            (r"mc\^2", "M C squared"),
            
            # Other physics formulas
            (r"F\s*=\s*ma", "F equals M A"),
            (r"F\s*=\s*m\s*[\^]?\s*2", "F equals M squared"),
            (r"a\s*=\s*F/m", "A equals F over M"),
            
            # Math expressions with power
            (r"(\d+)\s*[\^]\s*(\d+)", r"\1 to the power of \2"),
            (r"(\d+)\s*²", r"\1 squared"),
            (r"(\d+)\s*³", r"\1 cubed"),
            
            # Fractions
            (r"(\d+)/(\d+)", r"\1 over \2"),
            
            # Abbreviations
            (r"i\.e\.", "that is"),
            (r"e\.g\.", "for example"),
            (r"et\s*al\.", "and others"),
            (r"etc\.", "etcetera"),
            (r"vs\.", "versus"),
            (r"Dr\.", "Doctor"),
            (r"Mr\.", "Mister"),
            (r"Mrs\.", "Misses"),
            (r"Ms\.", "Miss"),
            (r"Prof\.", "Professor"),
            (r"St\.", "Saint"),
            (r"Ave\.", "Avenue"),
            (r"Rd\.", "Road"),
            (r"Blvd\.", "Boulevard"),
            
            # URLs and paths (simplify)
            (r"https?://[^\s]+", "a web link"),
            (r"www\.[^\s]+", "a website"),
            (r"[A-Za-z]:\\[^\s]+", "a file path"),
        ]
    
    def normalize_math(self, text: str) -> str:
        """
        Normalize math symbols and formulas for speech.
        """
        if not text:
            return text
        
        result = text
        
        # Apply math replacements
        for symbol, replacement in self.math_replacements.items():
            result = result.replace(symbol, replacement)
        
        # Apply patterns
        for pattern, replacement in self.patterns:
            try:
                result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            except Exception as e:
                # If pattern fails, continue
                continue
        
        return result
    
    def normalize(self, text: str) -> str:
        """
        Full text normalization for speech.
        """
        if not text:
            return text
        
        result = text
        result = self.normalize_math(result)
        
        # Fix common issues
        result = re.sub(r'\s+', ' ', result)  # Multiple spaces
        result = result.strip()
        
        return result


# Global instance
normalizer = TextNormalizer()