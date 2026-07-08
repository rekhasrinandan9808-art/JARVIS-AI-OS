from moa.synonyms import *


class IntentDetector:

    def detect(self, text: str):

        t = text.lower().strip()

        # Search
        for word in SEARCH:
            if t.startswith(word):
                return "search"

        # Research
        for word in RESEARCH:
            if t.startswith(word):
                return "research"

        # Syntax
        for word in SYNTAX:
            if t.startswith(word):
                return "syntax"

        # Coding
        for word in CODING:
            if t.startswith(word):
                return "coding"

        # Translate
        for word in TRANSLATE:
            if t.startswith(word):
                return "translate"

        # Weather
        for word in WEATHER:
            if word in t:
                return "weather"

        # Location
        for word in LOCATION:
            if word in t:
                return "location"

        return None