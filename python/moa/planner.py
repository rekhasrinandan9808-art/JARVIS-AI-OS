"""
moa/planner.py
Planner -- converts natural language commands into capability + params
Uses Intent Router for intelligent routing with conversational support
"""

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple

from moa.auto_corrector import AutoCorrector
from moa.intent_router import IntentRouter, Intent


@dataclass
class Plan:
    capability: str
    params: dict


class Planner:

    def __init__(self):
        self.corrector = AutoCorrector()
        self.router = IntentRouter()
        
        # =================================================
        # COMMAND DETECTION PATTERNS
        # =================================================
        self.command_indicators = [
            "open", "close", "kill", "start", "stop", "run",
            "create", "delete", "list", "set", "get", "check",
            "launch", "exit", "quit", "help", "status",
            "report", "show", "find", "search", "copy", "move",
            "rename", "delete", "remove", "clear", "empty"
        ]
        
        self.command_patterns = {
            "launch": [r"open\s+", r"launch\s+", r"start\s+", r"run\s+"],
            "close": [r"close\s+", r"kill\s+", r"stop\s+", r"exit\s+"],
            "system": [r"system\s+status", r"check\s+agents", r"agents\s+progress"],
            "desktop": [r"create\s+file", r"delete\s+file", r"list\s+files", r"set\s+volume"],
            "memory": [r"my\s+name\s+is", r"what\s+is\s+my\s+name", r"remember\s+"],
        }
        
        # =================================================
        # DIRECT PATTERNS (fallback if router fails)
        # =================================================
        
        # System commands - route to supervisor
        self.system_patterns = [
            (r"agents? progress", "progress_report"),
            (r"progress of agents?", "progress_report"),
            (r"agent progress", "progress_report"),
            (r"check agents?", "check_all"),
            (r"system health", "check_all"),
            (r"system status", "check_all"),
            (r"health of agents?", "check_all"),
            (r"how are the agents?", "check_all"),
            (r"agent status", "progress_report"),
            (r"show agent status", "progress_report"),
            (r"all agents?", "progress_report_full"),
        ]
        
        # Time patterns
        self.time_patterns = [
            r"what time is it",
            r"what's the time",
            r"time now",
            r"current time",
            r"tell me the time",
            r"what is the time",
        ]
        
        # Date patterns
        self.date_patterns = [
            r"what is today's date",
            r"what's today's date",
            r"today's date",
            r"current date",
            r"what day is it",
            r"what date is it",
            r"today date",
        ]
        
        # Weather patterns
        self.weather_patterns = [
            r"weather",
            r"weather today",
            r"today's weather",
            r"forecast",
            r"temperature",
            r"rain today",
            r"is it raining",
            r"weather update",
            r"weather updates",
            r"what's the weather",
            r"weather forecast",
        ]
        
        # Location patterns
        self.location_patterns = [
            r"where am i",
            r"where are we",
            r"my location",
            r"current location",
            r"what's my location",
            r"find my location",
            r"where i am",
        ]
        
        # Close app patterns - FIXED with better cleaning
        self.close_patterns = [
            r"close\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"kill\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"stop\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"exit\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
        ]
        
        # Launch app patterns - FIXED
        self.launch_patterns = [
            r"open\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"launch\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"start\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
            r"run\s+([a-zA-Z0-9\s]+?)(?:\s*$)",
        ]
        
        # Agent check patterns
        self.agent_check_patterns = [
            r"check\s+(\w+)\s+agent",
            r"status\s+of\s+(\w+)\s+agent",
            r"how\s+is\s+(\w+)\s+agent",
            r"show\s+(\w+)\s+agent",
            r"agent\s+(\w+)\s+status",
            r"tell\s+me\s+about\s+(\w+)\s+agent",
            r"what\s+about\s+(\w+)\s+agent",
            r"(\w+)\s+agent\s+health",
            r"how's\s+(\w+)\s+agent",
            r"what's\s+(\w+)\s+agent\s+status",
        ]
        
        # Memory recall patterns
        self.memory_recall_patterns = [
            r"what is my name",
            r"what's my name",
            r"what is my mother's name",
            r"what is my mother name",
            r"what's my mother's name",
            r"what is my father's name",
            r"what is my favorite color",
            r"where do i live",
            r"where am i from",
            r"what do i like",
            r"when is my birthday",
            r"what is my pet name",
            r"what is my occupation",
            r"what do you remember about me",
            r"what do you know about me",
            r"tell me my name",
            r"do you know my name",
        ]
        
        # Memory remember patterns
        self.memory_remember_patterns = [
            r"my name is (.+)",
            r"my mother's name is (.+)",
            r"my mother name is (.+)",
            r"my father's name is (.+)",
            r"my favorite color is (.+)",
            r"i live in (.+)",
            r"i am from (.+)",
            r"i like (.+)",
            r"my birthday is (.+)",
            r"my pet name is (.+)",
            r"my occupation is (.+)",
            r"remember my name is (.+)",
            r"save my name as (.+)",
            r"call me (.+)",
        ]
        
        # Search patterns
        self.search_patterns = [
            r"search for (.+)",
            r"search (.+)",
            r"find (.+)",
            r"google (.+)",
            r"look up (.+)",
            r"browse (.+)",
        ]

    def plan(self, command: str) -> Plan:
        """
        Plan a command using:
        1. Auto-correction
        2. Intent routing (returns Intent object)
        3. Command detection (is it a command or conversation?)
        4. Direct pattern matching (fallback)
        """
        if not command or not command.strip():
            return Plan("think", {"query": "Hello"})
        
        # Step 0: Clean the command - remove "ok jarvis", "hey jarvis", etc.
        command = re.sub(r'^(ok\s+)?(jarvis|hey jarvis|hey)\s+', '', command, flags=re.IGNORECASE)
        command = command.strip()
        
        # Step 1: Auto-correct
        corrected = self.corrector.correct(command)
        corrected = self.corrector.correct_command(corrected)
        
        # Step 2: Try Intent Router first - FIXED: router returns ONE object
        try:
            intent = self.router.route(corrected)
            
            # Intent is an object with attributes
            if intent and hasattr(intent, 'capability') and intent.capability:
                print(f"🎯 Intent routed: {intent.capability} -> {intent.params}")
                return Plan(intent.capability, intent.params)
        except Exception as e:
            print(f"⚠️ Intent router error: {e}")
        
        # Step 3: Check if it's a command or conversation
        text = corrected.lower().strip()
        is_command = self._is_command(text)
        
        # If it's a command, route to appropriate capability
        if is_command:
            print(f"⚡ Command detected")
            return self._route_command(text)
        
        # Step 4: Fallback to direct pattern matching for commands
        # =================================================
        # 4a: System Commands
        # =================================================
        for pattern, cap in self.system_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🔧 System command: {cap}")
                return Plan(cap, {})
        
        # =================================================
        # 4b: Time
        # =================================================
        for pattern in self.time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🕒 Time query")
                return Plan("get_time", {})
        
        # =================================================
        # 4c: Date
        # =================================================
        for pattern in self.date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"📅 Date query")
                return Plan("get_date", {})
        
        # =================================================
        # 4d: Weather
        # =================================================
        for pattern in self.weather_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🌤️ Weather query")
                return Plan("weather", {})
        
        # =================================================
        # 4e: Location
        # =================================================
        for pattern in self.location_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"📍 Location query")
                return Plan("my_location", {})
        
        # =================================================
        # 4f: Memory Recall
        # =================================================
        for pattern in self.memory_recall_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🧠 Memory recall")
                if "mother" in pattern:
                    return Plan("recall_fact", {"key": "user.mother"})
                elif "father" in pattern:
                    return Plan("recall_fact", {"key": "user.father"})
                elif "color" in pattern:
                    return Plan("recall_fact", {"key": "user.favorite_color"})
                elif "live" in pattern or "from" in pattern:
                    return Plan("recall_fact", {"key": "user.city"})
                elif "like" in pattern:
                    return Plan("recall_fact", {"key": "user.likes"})
                elif "birthday" in pattern:
                    return Plan("recall_fact", {"key": "user.birthday"})
                elif "pet" in pattern:
                    return Plan("recall_fact", {"key": "user.pet"})
                elif "occupation" in pattern:
                    return Plan("recall_fact", {"key": "user.occupation"})
                elif "remember about me" in pattern or "know about me" in pattern:
                    return Plan("get_all_memory", {})
                else:
                    return Plan("recall_fact", {"key": "user.name"})
        
        # =================================================
        # 4g: Memory Remember
        # =================================================
        for pattern in self.memory_remember_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                print(f"🧠 Memory remember: {value}")
                if "mother" in pattern:
                    key = "user.mother"
                elif "father" in pattern:
                    key = "user.father"
                elif "color" in pattern:
                    key = "user.favorite_color"
                elif "live" in pattern or "from" in pattern:
                    key = "user.city"
                elif "like" in pattern:
                    key = "user.likes"
                elif "birthday" in pattern:
                    key = "user.birthday"
                elif "pet" in pattern:
                    key = "user.pet"
                elif "occupation" in pattern:
                    key = "user.occupation"
                else:
                    key = "user.name"
                return Plan("remember_fact", {"key": key, "value": value})
        
        # =================================================
        # 4h: Close App - FIXED with better cleaning
        # =================================================
        for pattern in self.close_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip() if match.groups() else ""
                # If no match from group, try to extract manually
                if not app_name:
                    for cmd in ["close ", "kill ", "stop ", "exit "]:
                        if text.startswith(cmd):
                            app_name = text[len(cmd):].strip()
                            break
                
                # Clean "jarvis" from app name
                app_name = re.sub(r'\s+jarvis$', '', app_name, flags=re.IGNORECASE)
                app_name = re.sub(r'^jarvis\s+', '', app_name, flags=re.IGNORECASE)
                app_name = app_name.strip()
                
                skip_words = ["voice", "mode", "all", "agents", "system", "settings", "browser", "the", "a", "an"]
                if app_name and app_name.lower() not in skip_words:
                    print(f"🛑 Closing app: {app_name}")
                    return Plan("close_app", {"app": app_name})
        
        # =================================================
        # 4i: Launch App - FIXED with better cleaning
        # =================================================
        for pattern in self.launch_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip() if match.groups() else ""
                # If no match from group, try to extract manually
                if not app_name:
                    for cmd in ["open ", "launch ", "start ", "run "]:
                        if text.startswith(cmd):
                            app_name = text[len(cmd):].strip()
                            break
                
                # Clean "jarvis" from app name
                app_name = re.sub(r'\s+jarvis$', '', app_name, flags=re.IGNORECASE)
                app_name = re.sub(r'^jarvis\s+', '', app_name, flags=re.IGNORECASE)
                app_name = app_name.strip()
                
                skip_words = ["voice", "mode", "all", "agents", "system", "settings", "browser", "the", "a", "an"]
                if app_name and app_name.lower() not in skip_words:
                    print(f"🚀 Launching app: {app_name}")
                    return Plan("launch_app", {"app": app_name})
        
        # =================================================
        # 4j: Agent Check
        # =================================================
        if "security status" in text or "security agent" in text:
            return Plan("check_agent", {"agent_name": "security"})
        
        for pattern in self.agent_check_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agent_name = match.group(1).lower()
                if agent_name in ["all", "every", "each", "any"]:
                    return Plan("check_all", {})
                print(f"🔍 Checking agent: {agent_name}")
                return Plan("check_agent", {"agent_name": agent_name})
        
        # =================================================
        # 4k: Clear Memory
        # =================================================
        clear_patterns = [
            r"clear memory",
            r"forget my name",
            r"reset memory",
            r"clear my name",
            r"delete my name",
            r"erase memory",
            r"clear user",
            r"forget me",
            r"clear all memory",
            r"forget everything",
        ]
        for pattern in clear_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🧹 Clearing memory")
                return Plan("clear_memory", {})
        
        if "clear" in text and "memory" in text:
            print(f"🧹 Clearing memory")
            return Plan("clear_memory", {})
        
        # =================================================
        # 4l: Search
        # =================================================
        for pattern in self.search_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                print(f"🔍 Searching: {query}")
                return Plan("search", {"query": query})
        
        # =================================================
        # 4m: Code Commands
        # =================================================
        if text.startswith("write code ") or text.startswith("code "):
            code = text[10:].strip() if text.startswith("write code ") else text[5:].strip()
            return Plan("write", {"code": code, "language": "python"})
        
        if text.startswith("run code "):
            code = text[9:].strip()
            return Plan("run", {"code": code, "language": "python"})
        
        # =================================================
        # 4n: List Apps
        # =================================================
        if re.search(r"list apps|installed apps|what apps|show apps|all apps|available apps", text, re.IGNORECASE):
            print(f"📋 Listing apps")
            return Plan("list_apps", {})
        
        # =================================================
        # 4o: Think (LLM) - LAST RESORT - CONVERSATIONAL
        # =================================================
        print(f"💭 Conversational query → LLM")
        return Plan("think", {"query": command})
    
    def _is_command(self, text: str) -> bool:
        """
        Check if text is a command vs conversation.
        
        A command is an explicit instruction to perform an action.
        Conversation is general chat, questions, or natural language.
        """
        # Check against command patterns
        for category, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        
        # Check for explicit command indicators
        words = text.split()
        if words and words[0].lower() in self.command_indicators:
            return True
        
        # Check for command-like phrases
        command_phrases = [
            "my name is",
            "what is my name",
            "set volume",
            "system status",
            "agents progress",
            "check all",
            "report each",
            "list apps",
            "installed apps",
        ]
        for phrase in command_phrases:
            if phrase in text:
                return True
        
        return False
    
    def _route_command(self, text: str) -> Plan:
        """
        Route command to appropriate capability.
        This is used when _is_command returns True.
        """
        # Time
        for pattern in self.time_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Plan("get_time", {})
        
        # Date
        for pattern in self.date_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Plan("get_date", {})
        
        # Weather
        for pattern in self.weather_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Plan("weather", {})
        
        # Location
        for pattern in self.location_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Plan("my_location", {})
        
        # Launch - with cleaning
        for pattern in self.launch_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                app = match.group(1).strip() if match.groups() else text.replace('open ', '').replace('launch ', '').strip()
                # Clean "jarvis" from app name
                app = re.sub(r'\s+jarvis$', '', app, flags=re.IGNORECASE)
                app = re.sub(r'^jarvis\s+', '', app, flags=re.IGNORECASE)
                app = app.strip()
                if app:
                    return Plan("launch_app", {"app": app})
        
        # Close - with cleaning
        for pattern in self.close_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                app = match.group(1).strip() if match.groups() else text.replace('close ', '').replace('kill ', '').strip()
                # Clean "jarvis" from app name
                app = re.sub(r'\s+jarvis$', '', app, flags=re.IGNORECASE)
                app = re.sub(r'^jarvis\s+', '', app, flags=re.IGNORECASE)
                app = app.strip()
                if app:
                    return Plan("close_app", {"app": app})
        
        # Agent check
        for pattern in self.agent_check_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agent = match.group(1).lower()
                return Plan("check_agent", {"agent_name": agent})
        
        # System commands
        for pattern, cap in self.system_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return Plan(cap, {})
        
        # Memory recall
        for pattern in self.memory_recall_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                if "mother" in pattern:
                    return Plan("recall_fact", {"key": "user.mother"})
                elif "father" in pattern:
                    return Plan("recall_fact", {"key": "user.father"})
                elif "color" in pattern:
                    return Plan("recall_fact", {"key": "user.favorite_color"})
                elif "live" in pattern or "from" in pattern:
                    return Plan("recall_fact", {"key": "user.city"})
                elif "like" in pattern:
                    return Plan("recall_fact", {"key": "user.likes"})
                elif "birthday" in pattern:
                    return Plan("recall_fact", {"key": "user.birthday"})
                elif "pet" in pattern:
                    return Plan("recall_fact", {"key": "user.pet"})
                elif "occupation" in pattern:
                    return Plan("recall_fact", {"key": "user.occupation"})
                else:
                    return Plan("recall_fact", {"key": "user.name"})
        
        # Memory remember
        for pattern in self.memory_remember_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if "mother" in pattern:
                    key = "user.mother"
                elif "father" in pattern:
                    key = "user.father"
                elif "color" in pattern:
                    key = "user.favorite_color"
                elif "live" in pattern or "from" in pattern:
                    key = "user.city"
                elif "like" in pattern:
                    key = "user.likes"
                elif "birthday" in pattern:
                    key = "user.birthday"
                elif "pet" in pattern:
                    key = "user.pet"
                elif "occupation" in pattern:
                    key = "user.occupation"
                else:
                    key = "user.name"
                return Plan("remember_fact", {"key": key, "value": value})
        
        # Search
        for pattern in self.search_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip()
                return Plan("search", {"query": query})
        
        # List Apps
        if re.search(r"list apps|installed apps|what apps|show apps|all apps|available apps", text, re.IGNORECASE):
            return Plan("list_apps", {})
        
        # Default to LLM
        return Plan("think", {"query": text})