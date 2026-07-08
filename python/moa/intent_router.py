"""
moa/intent_router.py
Intent Router - Decides what to do BEFORE LLM
With auto-correction, fuzzy matching, and proper priority routing
"""

import re
from typing import Tuple, Optional, Dict, Any, List
from dataclasses import dataclass
from rapidfuzz import fuzz

@dataclass
class Intent:
    """Represents a routed intent."""
    capability: str
    params: Dict[str, Any]
    confidence: float = 1.0
    requires_llm: bool = False


class IntentRouter:
    """
    Routes user input to the correct capability.
    
    RULE: LLM is NEVER the first choice.
    LLM is ONLY used when NO OTHER intent matches.
    
    ROUTING PRIORITY:
    1. Wake word cleanup
    2. Memory commands
    3. System commands
    4. Application close
    5. Application launch
    6. FileSystem commands (NEW - PRIORITY)
    7. Desktop commands
    8. Time/Date
    9. Weather/Location
    10. List Apps
    11. Agent Check
    12. Search/RAG
    13. LLM (fallback)
    """
    
    def __init__(self):
        # =================================================
        # WAKE WORDS - NORMALIZE TRANSCRIPTION VARIATIONS
        # =================================================
        self.wake_words = [
            "jarvis", "jairbys", "clarvis", "azaris", "jarvice",
            "garvis", "jervis", "garves", "darwish", "jarvish",
            "jarivs", "jarvus"
        ]
        
        # =================================================
        # GREETINGS - Should NOT be routed as app launches
        # =================================================
        self.greetings = [
            "hello", "hi", "hey", "good morning", "good afternoon",
            "good evening", "good night", "greetings", "howdy",
            "what's up", "sup", "yo", "hey there", "hi there"
        ]
        
        # =================================================
        # APP NAMES - Comprehensive for fuzzy matching
        # =================================================
        self.app_names = [
            # System apps - Windows built-in
            "notepad", "calculator", "calc", "paint", "mspaint",
            "cmd", "command prompt", "powershell", "explorer", "file explorer",
            "task manager", "taskmgr", "control panel", "settings",
            "store", "microsoft store", "regedit", "registry editor",
            "device manager", "disk management", "services", "event viewer",
            "snipping tool", "camera", "clock", "alarms", "alarm clock",
            "calendar", "calender", "photos", "mail", "maps", "weather",
            "voice recorder", "sound recorder", "media player", "windows media player",
            "movies", "tv", "clipchamp", "xbox", "game bar",
            
            # Browsers
            "chrome", "google chrome", "firefox", "edge", "microsoft edge",
            "opera", "brave", "vivaldi", "browser",
            
            # Web apps (open in browser)
            "chatgpt", "chat gpt", "gpt", "claude", "copilot", "gemini",
            "youtube", "google", "gmail", "github", "stackoverflow",
            "reddit", "twitter", "x", "linkedin", "facebook", "instagram",
            "amazon", "flipkart", "netflix", "prime video", "hotstar",
            
            # Office
            "word", "microsoft word", "excel", "microsoft excel",
            "powerpoint", "power point", "outlook", "microsoft outlook",
            "onenote", "access", "publisher",
            
            # Development
            "vscode", "visual studio code", "code", "visual studio",
            "pycharm", "intellij", "sublime text", "sublime", "notepad++",
            "notepad plus plus", "git", "git bash", "github desktop",
            
            # Media
            "spotify", "vlc", "vlc media player", "winamp", "itunes",
            "audacity",
            
            # Communication
            "discord", "slack", "teams", "microsoft teams", "zoom",
            "skype", "telegram", "whatsapp", "signal",
            
            # Games
            "steam", "epic games", "epic", "minecraft", "roblox",
            
            # Utility
            "7zip", "winrar", "winzip", "ccleaner", "malwarebytes",
            
            # Adobe
            "photoshop", "adobe photoshop", "illustrator", "adobe illustrator",
            "premiere", "adobe premiere", "after effects", "adobe after effects",
            "reader", "adobe reader", "acrobat", "adobe acrobat",
        ]
        
        # =================================================
        # APP ALIASES
        # =================================================
        self.app_aliases = {
            # System
            "calculator": "calc", "calc": "calc", "notepad": "notepad",
            "paint": "mspaint", "mspaint": "mspaint", "cmd": "cmd",
            "command prompt": "cmd", "powershell": "powershell",
            "explorer": "explorer", "file explorer": "explorer",
            "task manager": "taskmgr", "taskmgr": "taskmgr",
            "control panel": "control.exe", "settings": "ms-settings:",
            "store": "ms-windows-store:", "microsoft store": "ms-windows-store:",
            "regedit": "regedit.exe", "registry editor": "regedit.exe",
            "device manager": "devmgmt.msc", "disk management": "diskmgmt.msc",
            "services": "services.msc", "event viewer": "eventvwr.msc",
            "snipping tool": "SnippingTool.exe",
            
            # UWP Protocols
            "camera": "windows.camera:", "clock": "ms-clock:",
            "alarms": "ms-clock:", "alarm clock": "ms-clock:",
            "calendar": "outlookcal:", "calender": "outlookcal:",
            "photos": "ms-photos:", "mail": "outlookmail:",
            "maps": "bingmaps:", "weather": "ms-weather:",
            "music": "ms-music:", "movies": "ms-video:",
            "tv": "ms-video:", "clipchamp": "ms-clipchamp:",
            "voice recorder": "ms-voice-recorder:", "sound recorder": "ms-voice-recorder:",
            
            # Browsers
            "chrome": "chrome", "google chrome": "chrome",
            "firefox": "firefox", "edge": "msedge",
            "microsoft edge": "msedge", "browser": "chrome",
            
            # Web Apps
            "chatgpt": "https://chat.openai.com", "chat gpt": "https://chat.openai.com",
            "gpt": "https://chat.openai.com", "claude": "https://claude.ai",
            "copilot": "https://copilot.microsoft.com", "gemini": "https://gemini.google.com",
            "youtube": "https://youtube.com", "google": "https://google.com",
            "gmail": "https://gmail.com", "github": "https://github.com",
            "stackoverflow": "https://stackoverflow.com", "reddit": "https://reddit.com",
            "twitter": "https://twitter.com", "x": "https://x.com",
            "linkedin": "https://linkedin.com", "facebook": "https://facebook.com",
            "instagram": "https://instagram.com", "amazon": "https://amazon.com",
            "flipkart": "https://flipkart.com", "netflix": "https://netflix.com",
            "prime video": "https://primevideo.com", "hotstar": "https://hotstar.com",
            
            # Office
            "word": "winword", "microsoft word": "winword",
            "excel": "excel", "microsoft excel": "excel",
            "powerpoint": "powerpnt", "power point": "powerpnt",
            "outlook": "outlook", "microsoft outlook": "outlook",
            "onenote": "onenote", "access": "msaccess", "publisher": "mspub",
            
            # Development
            "vscode": "code", "visual studio code": "code", "code": "code",
            "visual studio": "devenv", "pycharm": "pycharm64",
            "intellij": "idea64", "sublime text": "sublime_text",
            "sublime": "sublime_text", "notepad++": "notepad++",
            "notepad plus plus": "notepad++", "git": "git",
            "git bash": "git-bash", "github desktop": "GitHubDesktop",
            
            # Media
            "spotify": "spotify", "vlc": "vlc", "vlc media player": "vlc",
            "winamp": "winamp", "itunes": "iTunes", "audacity": "audacity",
            
            # Communication
            "discord": "discord", "slack": "slack", "teams": "teams",
            "microsoft teams": "teams", "zoom": "zoom", "skype": "skype",
            "telegram": "telegram", "whatsapp": "whatsapp", "signal": "signal",
            
            # Games
            "steam": "steam", "epic games": "EpicGamesLauncher",
            "epic": "EpicGamesLauncher", "minecraft": "Minecraft",
            "roblox": "RobloxPlayerLauncher",
            
            # Utility
            "7zip": "7zFM", "winrar": "WinRAR", "winzip": "WINZIP32",
            "ccleaner": "CCleaner64", "malwarebytes": "MBAMService",
            
            # Adobe
            "photoshop": "Photoshop", "adobe photoshop": "Photoshop",
            "illustrator": "Illustrator", "adobe illustrator": "Illustrator",
            "premiere": "Premiere", "adobe premiere": "Premiere",
            "after effects": "AfterFX", "adobe after effects": "AfterFX",
            "reader": "Acrobat", "adobe reader": "Acrobat",
            "acrobat": "Acrobat", "adobe acrobat": "Acrobat",
        }
        
        # =================================================
        # UWP PROCESS MAPPING - For closing UWP apps
        # =================================================
        self.uwp_process_mapping = {
            "clock": "Clock.exe",
            "alarms": "Alarms.exe",
            "alarm clock": "Alarms.exe",
            "calendar": "Calendar.exe",
            "calender": "Calendar.exe",
            "camera": "Camera.exe",
            "photos": "Photos.exe",
            "mail": "Mail.exe",
            "maps": "Maps.exe",
            "weather": "Weather.exe",
            "voice recorder": "VoiceRecorder.exe",
            "sound recorder": "VoiceRecorder.exe",
            "movies": "Movies.exe",
            "clipchamp": "Clipchamp.exe",
        }
        
        # =================================================
        # UWP PROTOCOL MAPPING - For launching UWP apps
        # =================================================
        self.uwp_protocol_mapping = {
            "camera": "windows.camera:",
            "clock": "ms-clock:",
            "alarms": "ms-clock:",
            "alarm clock": "ms-clock:",
            "photos": "ms-photos:",
            "gallery": "ms-photos:",
            "mail": "outlookmail:",
            "calendar": "outlookcal:",
            "calender": "outlookcal:",
            "maps": "bingmaps:",
            "weather": "ms-weather:",
            "music": "ms-music:",
            "movies": "ms-video:",
            "tv": "ms-video:",
            "clipchamp": "ms-clipchamp:",
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
            "voice recorder": "ms-voice-recorder:",
            "sound recorder": "ms-voice-recorder:",
        }
        
        # =================================================
        # SUPERVISOR COMMANDS
        # =================================================
        self.supervisor_commands = {
            "agents progress": "progress_report",
            "agent progress": "progress_report",
            "progress report": "progress_report",
            "system status": "progress_report",
            "system health": "check_all",
            "check all agents": "check_all",
            "check agents": "check_all",
            "show alerts": "get_alerts",
            "alerts": "get_alerts",
            "idle agents": "get_idle_agents",
            "unhealthy agents": "get_unhealthy_agents",
            "busiest agent": "get_busiest_agent",
            "least used agent": "get_least_used_agent",
            "report each agent": "progress_report_full",
            "full report": "progress_report_full",
            "detailed status": "progress_report_full",
            "agents list": "progress_report_full",
            "all agents list": "progress_report_full",
            "where all agents": "progress_report_full",
            "list all agents": "progress_report_full",
        }
        
        # =================================================
        # AUTO-CORRECTIONS
        # =================================================
        self.corrections = {
            "tim": "time", "tiem": "time", "tme": "time",
            "todat": "today", "todaty": "today", "tody": "today",
            "dat": "date", "dae": "date",
            "calender": "calendar", "calandar": "calendar",
            "wather": "weather", "wheather": "weather", "weater": "weather",
            "forcast": "forecast",
            "chrom": "chrome", "chorme": "chrome", "chome": "chrome",
            "notpad": "notepad", "nootpad": "notepad",
            "calculater": "calculator", "calclator": "calculator",
            "excl": "excel", "powerpnt": "powerpoint", "outlok": "outlook",
            "chartgpt": "chatgpt", "chart gpt": "chatgpt",
            "microsoft store": "store", "ms store": "store",
            "file explorer": "explorer", "my computer": "explorer",
            "this pc": "explorer",
            "opne": "open", "opoen": "open",
            "clsoe": "close", "closse": "close",
            "luanch": "launch", "lunch": "launch",
            "seach": "search", "searc": "search", "serach": "search",
            "findd": "find", "fnd": "find",
            "strt": "start", "str": "start",
            "exsit": "exit", "exti": "exit", "quitt": "quit",
            "stap": "stop", "stpp": "stop", "stp": "stop",
            "youtub": "youtube", "yutube": "youtube",
            "gogle": "google", "googel": "google",
            "gmial": "gmail", "gitub": "github", "githhub": "github",
            "reditt": "reddit", "twiter": "twitter", "twittr": "twitter",
            "facebok": "facebook", "facebbok": "facebook",
            "amzon": "amazon", "amazzon": "amazon",
            "flipcart": "flipkart", "netflx": "netflix",
        }
        
        # =================================================
        # FILESYSTEM PATTERNS - PRIORITY 6 (NEW)
        # =================================================
        self.filesystem_patterns = {
            "list_drives": [
                r"list drives", r"show drives", r"available drives",
                r"what drives", r"drives available", r"all drives"
            ],
            "get_drive_info": [
                r"info (?:about|for) drive ([A-Za-z]:)",
                r"drive info ([A-Za-z]:)",
                r"details? about drive ([A-Za-z]:)",
                r"check drive ([A-Za-z]:)",
                r"drive ([A-Za-z]:) details?"
            ],
            "create_file": [
                r"create file ([A-Za-z]:[^\\]*\\.+?)(?:\s+with content\s+(.+))?$",
                r"create a file ([A-Za-z]:[^\\]*\\.+?)(?:\s+with\s+(.+))?$",
                r"make file ([A-Za-z]:[^\\]*\\.+?)(?:\s+with\s+(.+))?$",
                r"create file (.+?)(?:\s+with content\s+(.+))?$",
                r"create a file (.+?)(?:\s+with\s+(.+))?$",
                # Drive-specific patterns
                r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
                r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+on\s+([A-Za-z])\s*drive",
                r"create\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z]):",
                r"make\s+(?:a\s+)?file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
                r"new\s+file\s+([a-zA-Z0-9_\-.]+)\s+in\s+([A-Za-z])\s*drive",
            ],
            "open_file": [
                r"open file ([A-Za-z]:[^\\]*\\.+)",
                r"open ([A-Za-z]:[^\\]*\\.+)",
                r"open file (.+)",
            ],
            "read_file": [
                r"read file ([A-Za-z]:[^\\]*\\.+)",
                r"show file ([A-Za-z]:[^\\]*\\.+)",
                r"display file ([A-Za-z]:[^\\]*\\.+)",
                r"read file (.+)",
            ],
            "write_file": [
                r"write file ([A-Za-z]:[^\\]*\\.+?) with (.+)",
                r"write to file ([A-Za-z]:[^\\]*\\.+?) with (.+)",
                r"write file (.+?) with (.+)",
            ],
            "append_file": [
                r"append file ([A-Za-z]:[^\\]*\\.+?) with (.+)",
                r"append to file ([A-Za-z]:[^\\]*\\.+?) with (.+)",
                r"add to file ([A-Za-z]:[^\\]*\\.+?) with (.+)",
                r"append file (.+?) with (.+)",
            ],
            "delete_file": [
                r"delete file ([A-Za-z]:[^\\]*\\.+)",
                r"remove file ([A-Za-z]:[^\\]*\\.+)",
                r"delete file (.+)",
            ],
            "create_folder": [
                r"create folder ([A-Za-z]:[^\\]*\\.+)",
                r"make folder ([A-Za-z]:[^\\]*\\.+)",
                r"create directory ([A-Za-z]:[^\\]*\\.+)",
                r"create folder (.+)",
                r"make folder (.+)",
            ],
            "delete_folder": [
                r"delete folder ([A-Za-z]:[^\\]*\\.+)",
                r"remove folder ([A-Za-z]:[^\\]*\\.+)",
                r"delete directory ([A-Za-z]:[^\\]*\\.+)",
                r"delete folder (.+)",
            ],
            "copy_file": [
                r"copy file ([A-Za-z]:[^\\]*\\.+?) to ([A-Za-z]:[^\\]*\\.+)",
                r"copy ([A-Za-z]:[^\\]*\\.+?) to ([A-Za-z]:[^\\]*\\.+)",
                r"copy file (.+?) to (.+)",
            ],
            "move_file": [
                r"move file ([A-Za-z]:[^\\]*\\.+?) to ([A-Za-z]:[^\\]*\\.+)",
                r"move ([A-Za-z]:[^\\]*\\.+?) to ([A-Za-z]:[^\\]*\\.+)",
                r"move file (.+?) to (.+)",
            ],
            "search_files": [
                r"search files (.+?) in ([A-Za-z]:[^\\]*\\.+)",
                r"find files (.+?) in ([A-Za-z]:[^\\]*\\.+)",
                r"search for (.+?) in ([A-Za-z]:[^\\]*\\.+)",
                r"search files (.+?) in (.+)",
            ],
            "list_directory": [
                r"list directory ([A-Za-z]:[^\\]*\\.+)",
                r"list files in ([A-Za-z]:[^\\]*\\.+)",
                r"show files in ([A-Za-z]:[^\\]*\\.+)",
                r"list directory (.+)",
                r"list files in (.+)",
            ],
            "get_file_info": [
                r"info about file ([A-Za-z]:[^\\]*\\.+)",
                r"file info ([A-Za-z]:[^\\]*\\.+)",
                r"info about file (.+)",
            ],
            "create_and_open": [
                r"create and open ([A-Za-z]:[^\\]*\\.+?)(?:\s+with content\s+(.+))?$",
                r"create and open file ([A-Za-z]:[^\\]*\\.+?)(?:\s+with\s+(.+))?$",
                r"create and open (.+?)(?:\s+with\s+(.+))?$",
            ],
        }
        
        # =================================================
        # DESKTOP PATTERNS - PRIORITY 7
        # =================================================
        self.desktop_patterns = {
            "file_info": [r"info about file (.+)", r"file info (.+)"],
            "list_directory": [r"list directory (.+)", r"show files in (.+)", r"list files in (.+)", r"list (.+) files", r"show (.+) directory"],
            "search_files": [r"search for (.+) in (.+)", r"find (.+) in (.+)", r"search (.+) in (.+)", r"find files (.+) in (.+)"],
            "create_file": [r"create file (.+)", r"make file (.+)", r"create a file (.+)", r"make a file (.+)", r"create (.+) file", r"new file (.+)"],
            "read_file": [r"read file (.+)"], "delete_file": [r"delete file (.+)"],
            "copy_file": [r"copy (.+) to (.+)"], "move_file": [r"move (.+) to (.+)"], "rename_file": [r"rename (.+) to (.+)"],
            "list_processes": [r"list processes", r"show processes", r"running apps", r"running processes", r"process list"],
            "kill_process": [r"kill process (\d+)"],
            "kill_process_by_name": [r"kill (.+) process", r"kill (.+)", r"stop (.+)", r"terminate (.+)", r"close (.+) app"],
            "start_process": [r"start (.+)", r"run (.+)"],
            "list_windows": [r"list windows", r"show windows", r"open windows", r"active windows"],
            "focus_window": [r"focus (.+) window", r"switch to (.+)", r"go to (.+) window", r"bring (.+) to front"],
            "minimize_window": [r"minimize (.+)", r"minimize (.+) window"],
            "maximize_window": [r"maximize (.+)", r"maximize (.+) window"],
            "close_window": [r"close (.+) window", r"close (.+)"],
            "resize_window": [r"resize (.+) to (\d+) (\d+)"],
            "move_window": [r"move (.+) to (\d+) (\d+)"],
            "get_volume": [
                r"^volume$",
                r"what is (the )?volume",
                r"get (the )?volume",
                r"current volume",
                r"check volume",
                r"tell me (the )?volume",
            ],
            "set_volume": [
                r"set volume to (\d+)",
                r"volume (\d+)",
                r"set volume (\d+)",
                r"increase volume to (\d+)",
                r"turn volume to (\d+)",
            ],
            "set_brightness": [r"set brightness to (\d+)", r"brightness (\d+)", r"set brightness (\d+)"],
            "get_brightness": [r"get brightness", r"what is brightness", r"current brightness"],
            "set_wallpaper": [r"set wallpaper (.+)"],
            "system_info": [r"system info", r"computer info", r"pc info", r"show system info", r"system status", r"system stats"],
            "get_ip_info": [r"ip address", r"what is my ip", r"get ip"],
            "screenshot": [r"screenshot", r"take screenshot", r"capture screen", r"screen capture", r"take a screenshot"],
            "type_text": [r"type (.+)"], "hotkey": [r"hotkey (.+)"],
            "mouse_click": [r"click at (\d+) (\d+)"], "mouse_move": [r"move mouse to (\d+) (\d+)"],
            "find_app": [r"find app (.+)", r"locate app (.+)", r"where is (.+)"],
            "list_services": [r"list services", r"show services"],
            "start_service": [r"start service (.+)"], "stop_service": [r"stop service (.+)"],
            "registry_read": [r"read registry (.+)"], "registry_write": [r"write registry (.+) to (.+)"],
            "scan_junk": [r"scan junk", r"junk scan", r"find junk", r"search junk", r"scan system junk", r"find system junk", r"junk files", r"find temp files", r"scan temp files"],
            "clean_system": [r"clean system", r"system clean", r"clean junk", r"junk clean", r"remove junk", r"clean temp", r"delete temp files", r"clear temp", r"clean system junk", r"clean my system", r"remove temporary files", r"clear junk files"],
            "empty_recycle_bin": [r"empty recycle bin", r"clear recycle bin", r"empty trash", r"clear trash", r"empty recycle", r"clear recycle", r"empty recycling bin"],
            "delete_pattern": [r"delete (.+) in (.+)", r"remove (.+) from (.+)", r"delete all (.+) files in (.+)", r"delete (\*\.\w+) in (.+)"],
            "delete_large": [r"delete large files in (.+)", r"remove large files from (.+)", r"clean large files", r"delete files larger than (\d+)mb in (.+)", r"delete files larger than (\d+)mb", r"remove files larger than (\d+)mb"],
        }
    
    # =================================================
    # HELPER METHODS
    # =================================================
    
    def _clean_context_aware_input(self, text: str) -> str:
        """
        🔧 FIX: If context-aware AI injected history, extract the actual question.
        Prevents the router from matching regex against the injected history.
        """
        if not text:
            return text
        
        # Check if this is a context-injected prompt
        if "Current question:" in text:
            # Extract the actual question
            match = re.search(r'Current question:\s*(.*?)\s*(?:Based on the conversation|Provide a logical|Previous conversation|$)', text, re.IGNORECASE | re.DOTALL)
            if match:
                clean_text = match.group(1).strip()
                if clean_text:
                    # Remove any remaining prompt artifacts
                    clean_text = re.sub(r'\s*(?:Based on the conversation|Previous conversation|Provide a logical).*$', '', clean_text, re.IGNORECASE)
                    clean_text = clean_text.strip()
                    if clean_text:
                        return clean_text
        
        return text
    
    def _fuzzy_match_app(self, spoken: str, threshold: int = 75) -> Optional[str]:
        """Fuzzy match spoken app name against known app names."""
        spoken = spoken.lower().strip()
        
        # Direct match
        if spoken in self.app_names:
            return spoken
        
        # Partial match
        for app in self.app_names:
            if spoken in app or app in spoken:
                return app
        
        # Fuzzy match
        best_match = None
        best_score = 0
        for app in self.app_names:
            score = fuzz.ratio(spoken, app)
            if score > best_score:
                best_score = score
                best_match = app
        
        if best_match and best_score >= threshold:
            return best_match
        
        return None
    
    def _normalize_wake_word(self, text: str) -> str:
        """Normalize wake word variations to 'jarvis'."""
        text_lower = text.lower()
        for wake in self.wake_words:
            if wake in text_lower:
                text = re.sub(r'\b' + re.escape(wake) + r'\b', "Jarvis", text, flags=re.IGNORECASE)
        return text
    
    def _auto_correct(self, text: str) -> str:
        """Apply auto-corrections to text."""
        # Phrase corrections
        phrase_corrections = {
            "chart gpt": "chatgpt",
            "microsoft store": "store",
            "file explorer": "explorer",
            "visual studio code": "vscode",
            "vs code": "vscode",
            "power point": "powerpoint",
            "google chrome": "chrome",
            "microsoft edge": "edge",
            "command prompt": "cmd",
            "calender": "calendar",
            "calandar": "calendar",
        }
        
        text_lower = text.lower()
        for wrong, correct in phrase_corrections.items():
            if wrong in text_lower:
                text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text, flags=re.IGNORECASE)
        
        # Word corrections
        words = text.split()
        corrected_words = []
        for word in words:
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word.lower() in self.corrections:
                corrected_words.append(self.corrections[clean_word.lower()])
            else:
                corrected_words.append(word)
        
        return " ".join(corrected_words)
    
    def _check_memory_patterns(self, text: str) -> Optional[Dict]:
        """Check if text matches memory patterns."""
        text_lower = text.lower()
        
        # =================================================
        # PRIORITY 1: REMEMBER (WRITE)
        # 🔧 FIX: Use [^.!?]+ to prevent capturing injected context
        # =================================================
        remember_patterns = [
            (r"remember my name is ([^.!?]+)", "user.name"),
            (r"remember that my name is ([^.!?]+)", "user.name"),
            (r"my name is ([^.!?]+)", "user.name"),
            (r"call me ([^.!?]+)", "user.name"),
            (r"save my name as ([^.!?]+)", "user.name"),
            (r"i am called ([^.!?]+)", "user.name"),
            (r"i am ([^.!?]+)", "user.name"),
            (r"remember i am ([^.!?]+)", "user.name"),
            (r"remember my mother's name is ([^.!?]+)", "user.mother"),
            (r"my mother's name is ([^.!?]+)", "user.mother"),
            (r"remember my father's name is ([^.!?]+)", "user.father"),
            (r"my father's name is ([^.!?]+)", "user.father"),
            (r"remember my birthday is ([^.!?]+)", "user.birthday"),
            (r"my birthday is ([^.!?]+)", "user.birthday"),
            (r"remember i live in ([^.!?]+)", "user.location"),
            (r"i live in ([^.!?]+)", "user.location"),
            (r"my location is ([^.!?]+)", "user.location"),
            (r"remember my favorite color is ([^.!?]+)", "user.favorite_color"),
            (r"my favorite color is ([^.!?]+)", "user.favorite_color"),
            (r"remember my pet is ([^.!?]+)", "user.pet"),
            (r"my pet is ([^.!?]+)", "user.pet"),
            (r"remember my occupation is ([^.!?]+)", "user.occupation"),
            (r"my occupation is ([^.!?]+)", "user.occupation"),
        ]
        
        for pattern, key in remember_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean any remaining prompt artifacts
                value = re.sub(r'\s*(?:Based on the conversation|Previous conversation|Provide a logical).*$', '', value, re.IGNORECASE)
                value = value.strip()
                if value and len(value) < 200:  # Sanity check - prevent giant captures
                    print(f"🧠 [ROUTER] Remember → {key}: {value}")
                    return {"capability": "remember_fact", "params": {"key": key, "value": value}}
        
        # =================================================
        # PRIORITY 2: RECALL (READ)
        # =================================================
        recall_patterns = [
            (r"what is my name", "user.name"),
            (r"what's my name", "user.name"),
            (r"who am i", "user.name"),
            (r"what do you know about me", "user.name"),
            (r"what do you remember about me", "user.name"),
            (r"what is my mother's name", "user.mother"),
            (r"my mother's name", "user.mother"),
            (r"what is my father's name", "user.father"),
            (r"my father's name", "user.father"),
            (r"when is my birthday", "user.birthday"),
            (r"my birthday", "user.birthday"),
            (r"where do i live", "user.location"),
            (r"my location", "user.location"),
            (r"what is my favorite color", "user.favorite_color"),
            (r"my favorite color", "user.favorite_color"),
            (r"do you know me", "user.name"),
            (r"remember me", "user.name"),
        ]
        
        for pattern, key in recall_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                print(f"🧠 [ROUTER] Recall → {key}")
                return {"capability": "recall_fact", "params": {"key": key}}
        
        # =================================================
        # PRIORITY 3: CLEAR MEMORY
        # =================================================
        clear_patterns = [
            r"clear memory",
            r"forget my name",
            r"reset memory",
            r"clear my name",
            r"delete my name",
            r"erase memory",
            r"forget me",
            r"clear all memory",
            r"clear everything",
            r"forget everything",
        ]
        for pattern in clear_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {"capability": "clear_memory", "params": {}}
        
        return None
    
    def _parse_app_control(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse app control commands."""
        text_lower = text.lower()
        
        # Check greetings first - don't route as app
        for greeting in self.greetings:
            if greeting in text_lower:
                return None
        
        # Clean text
        text_lower = re.sub(r'^(jarvis|hey jarvis|hey)\s+', '', text_lower)
        text_lower = re.sub(r'\s+jarvis$', '', text_lower)
        
        if text_lower.strip() in self.greetings:
            return None
        
        # Check verbs
        close_verbs = ["close", "kill", "stop", "exit", "terminate", "shut down", "shutdown"]
        launch_verbs = ["open", "launch", "start", "run"]
        
        is_launch = any(verb in text_lower for verb in launch_verbs)
        is_close = any(verb in text_lower for verb in close_verbs)
        
        if not is_launch and not is_close:
            return None
        
        # Check UWP protocols
        for uwp_name, protocol in self.uwp_protocol_mapping.items():
            if uwp_name in text_lower:
                for verb in launch_verbs:
                    if verb in text_lower:
                        return ("launch", protocol)
                return ("launch", protocol)
        
        # Find app name
        app_name = None
        for app in self.app_names:
            if app in text_lower:
                app_name = app
                break
        
        if not app_name and (is_launch or is_close):
            words = text_lower.split()
            for word in words:
                if len(word) > 2:
                    matched = self._fuzzy_match_app(word)
                    if matched:
                        app_name = matched
                        break
            
            if not app_name:
                matched = self._fuzzy_match_app(text_lower)
                if matched:
                    app_name = matched
        
        if not app_name:
            return None
        
        if is_close:
            # Check if it's a UWP app that needs special process name
            if app_name in self.uwp_process_mapping:
                return ("close", self.uwp_process_mapping[app_name])
            return ("close", app_name)
        
        if is_launch:
            return ("launch", app_name)
        
        return None
    
    def _parse_filesystem(self, text: str) -> Optional[Tuple[str, Dict]]:
        """Parse filesystem commands with drive support."""
        for action, patterns in self.filesystem_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    params = {}
                    groups = match.groups()
                    
                    if action in ["create_file", "create_and_open"]:
                        # Handle optional content
                        if len(groups) == 2:
                            # Check if this is a drive-specific pattern (filename, drive)
                            if re.match(r'^[a-zA-Z0-9_\-.]+$', groups[0].strip()):
                                # Drive-specific pattern: filename + drive
                                filename = groups[0].strip()
                                drive = groups[1].strip().upper()
                                # Remove "drive" suffix if present
                                drive = re.sub(r'\s*drive\s*$', '', drive)
                                # If drive is just a letter, format it
                                if len(drive) == 1:
                                    params["path"] = f"{drive}:\\{filename}"
                                else:
                                    params["path"] = f"{drive}\\{filename}"
                                params["content"] = ""
                            else:
                                params["path"] = groups[0].strip()
                                params["content"] = groups[1].strip() if groups[1] else ""
                        elif len(groups) == 1:
                            # For create_and_open with just path
                            params["path"] = groups[0].strip()
                            params["content"] = ""
                        else:
                            params["path"] = groups[0].strip() if groups else ""
                        
                        # Clean up path
                        if "path" in params:
                            # Remove trailing punctuation
                            params["path"] = re.sub(r'[.,;:]+$', '', params["path"])
                            # Preserve drive letter format
                            if re.match(r'^[A-Za-z]:', params["path"]):
                                # Keep as is
                                pass
                            elif not re.match(r'^[A-Za-z]:', params["path"]) and not params["path"].startswith(('/', '\\')):
                                # Relative path, keep as is
                                pass
                    
                    elif action in ["open_file", "read_file", "delete_file", "create_folder", "delete_folder", "get_file_info"]:
                        params["path"] = groups[0].strip() if groups else ""
                        # Clean up path
                        if "path" in params:
                            params["path"] = re.sub(r'[.,;:]+$', '', params["path"])
                    
                    elif action in ["write_file", "append_file"]:
                        if len(groups) >= 2:
                            params["path"] = groups[0].strip()
                            params["content"] = " ".join(groups[1:]).strip()
                    
                    elif action in ["copy_file", "move_file"]:
                        if len(groups) >= 2:
                            params["source"] = groups[0].strip()
                            params["destination"] = " ".join(groups[1:]).strip()
                            # Clean up
                            for key in ["source", "destination"]:
                                if key in params:
                                    params[key] = re.sub(r'[.,;:]+$', '', params[key])
                    
                    elif action in ["search_files"]:
                        if len(groups) >= 2:
                            params["pattern"] = groups[0].strip()
                            params["path"] = groups[1].strip()
                            # Clean up
                            params["path"] = re.sub(r'[.,;:]+$', '', params["path"])
                    
                    elif action in ["list_directory"]:
                        params["path"] = groups[0].strip() if groups else "."
                        params["path"] = re.sub(r'[.,;:]+$', '', params["path"])
                    
                    elif action in ["get_drive_info"]:
                        params["path"] = groups[0].strip() if groups else ""
                        # Ensure proper drive format
                        if params["path"] and not params["path"].endswith((':', '/', '\\')):
                            params["path"] = params["path"] + ":/"
                    
                    elif action in ["list_drives"]:
                        params = {}
                    
                    print(f"💾 [ROUTER] Filesystem action → {action} with {params}")
                    return (action, params)
        return None
    
    def _parse_desktop(self, text: str) -> Optional[Tuple[str, Dict]]:
        """Parse desktop commands."""
        # Check if it's a filesystem command first (priority)
        # If text contains drive letter (e.g., C: or D:), it's likely filesystem
        if re.search(r'[A-Za-z]:', text):
            # Try filesystem first
            fs_result = self._parse_filesystem(text)
            if fs_result:
                return fs_result
        
        # Try desktop patterns
        for action, patterns in self.desktop_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    params = {}
                    groups = match.groups()
                    
                    if action in ["copy_file", "move_file"] and len(groups) == 2:
                        params = {"src": groups[0], "dest": groups[1]}
                    elif action == "create_file_with_path" and len(groups) == 2:
                        filename = groups[0]
                        path = groups[1].rstrip('\\/')
                        params = {"path": path + '\\' + filename}
                    elif action in ["resize_window"] and len(groups) == 3:
                        params = {"title": groups[0], "width": int(groups[1]), "height": int(groups[2])}
                    elif action in ["move_window"] and len(groups) == 3:
                        params = {"title": groups[0], "x": int(groups[1]), "y": int(groups[2])}
                    elif action in ["set_volume", "set_brightness"]:
                        params = {"level": int(groups[0])}
                    elif action == "kill_process" and groups:
                        params = {"pid": int(groups[0])}
                    elif action == "kill_process_by_name" and groups:
                        params = {"name": groups[0]}
                    elif action in ["focus_window", "minimize_window", "maximize_window", "close_window"] and groups:
                        params = {"title": groups[0]}
                    elif action == "type_text" and groups:
                        params = {"text": groups[0]}
                    elif action == "hotkey" and groups:
                        params = {"keys": groups[0].split('+')}
                    elif action == "search_files" and len(groups) == 2:
                        params = {"pattern": groups[0], "root": groups[1]}
                    elif action == "find_app" and groups:
                        params = {"app_name": groups[0]}
                    elif action in ["file_info", "read_file", "delete_file", "create_file"] and groups:
                        params = {"path": groups[0]}
                    elif action in ["list_directory"] and groups:
                        params = {"path": groups[0]}
                    elif action == "rename_file" and len(groups) == 2:
                        params = {"old": groups[0], "new": groups[1]}
                    elif action == "registry_read" and groups:
                        params = {"key_path": groups[0]}
                    elif action == "registry_write" and len(groups) == 2:
                        params = {"key_path": groups[0], "value": groups[1]}
                    elif action in ["start_service", "stop_service"] and groups:
                        params = {"service_name": groups[0]}
                    elif action == "mouse_click" and len(groups) == 2:
                        params = {"x": int(groups[0]), "y": int(groups[1])}
                    elif action == "mouse_move" and len(groups) == 2:
                        params = {"x": int(groups[0]), "y": int(groups[1])}
                    elif action == "get_volume" and not groups:
                        params = {}
                    elif action == "get_brightness" and not groups:
                        params = {}
                    elif action == "delete_pattern" and len(groups) == 2:
                        params = {"pattern": groups[0], "root_path": groups[1], "confirm": True, "safe_mode": True}
                    elif action == "delete_large":
                        if len(groups) == 2:
                            params = {"root_path": groups[1], "min_size_mb": int(groups[0])}
                        elif len(groups) == 1:
                            try:
                                min_size = int(groups[0])
                                params = {"root_path": "C:\\", "min_size_mb": min_size}
                            except ValueError:
                                params = {"root_path": groups[0], "min_size_mb": 100}
                        else:
                            params = {"root_path": "C:\\", "min_size_mb": 100}
                    elif action in ["scan_junk", "clean_system", "empty_recycle_bin"]:
                        if action == "clean_system":
                            safe = 'safe' in text or 'safely' in text
                            dry = 'dry run' in text or 'preview' in text or 'show' in text
                            params = {"safe_mode": safe, "dry_run": dry}
                        else:
                            params = {}
                    else:
                        if groups:
                            if len(groups) == 1:
                                params = {"value": groups[0]}
                            else:
                                params = dict(enumerate(groups))
                    
                    return (action, params)
        return None
    
    def _is_question(self, text: str) -> bool:
        """Check if text is a question."""
        question_words = ["who", "what", "where", "when", "why", "how", "which", "whom", "whose"]
        return any(text.startswith(w + " ") for w in question_words) or "?" in text
    
    def _is_time_query(self, text: str) -> bool:
        """Check if text is asking for time."""
        patterns = [
            r"what time is it", r"what's the time", r"time now", r"current time",
            r"tell me the time", r"what is the time", r"time\s*$", r"time\s+now", r"now time"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _is_date_query(self, text: str) -> bool:
        """Check if text is asking for date."""
        patterns = [
            r"what is today's date", r"what's today's date", r"today's date",
            r"current date", r"what day is it", r"what date is it", r"today date", r"date\s*$"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _is_weather_query(self, text: str) -> bool:
        """Check if text is asking for weather."""
        patterns = [
            r"^weather$", r"weather today", r"today's weather", r"forecast",
            r"temperature", r"rain today", r"is it raining", r"weather update",
            r"weather updates", r"what's the weather"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _is_location_query(self, text: str) -> bool:
        """Check if text is asking for location."""
        patterns = [
            r"where am i", r"where are we", r"my location", r"current location",
            r"what's my location", r"find my location", r"where i am", r"location\s*$"
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)
    
    def _parse_agent_check(self, text: str) -> Optional[str]:
        """Parse agent check commands."""
        patterns = [
            r"check\s+(\w+)\s+agent",
            r"status\s+of\s+(\w+)\s+agent",
            r"how\s+is\s+(\w+)\s+agent",
            r"show\s+(\w+)\s+agent",
            r"agent\s+(\w+)\s+status",
            r"what\s+about\s+(\w+)\s+agent",
            r"(\w+)\s+agent\s+health",
            r"how's\s+(\w+)\s+agent",
        ]
        
        if "security status" in text or "security agent" in text:
            return "security"
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                agent = match.group(1).lower()
                if agent in ["all", "every", "each", "any"]:
                    return None
                return agent
        return None
    
    def _parse_search(self, text: str) -> Optional[str]:
        """Parse search queries with comprehensive patterns."""
        text_lower = text.lower()
        
        # Skip memory queries
        memory_keywords = [
            "my name", "my mother", "my father", "my favorite color",
            "where i live", "i live", "i am from", "my birthday",
            "my pet", "my occupation", "remember about me", "know about me",
            "what do you remember", "what do you know", "who am i",
            "your name", "my name is", "remember my name", "tell me my name",
            "do you know my name", "what is my", "what's my",
            "mother's name", "father's name",
        ]
        for keyword in memory_keywords:
            if keyword in text_lower:
                return None
        
        # =================================================
        # FORCE SEARCH: Exam/Results/News/Current Events
        # =================================================
        force_search_keywords = [
            # Results / Exams
            "results", "released", "declared", "out", "announced",
            "published", "issued", "notification", "admit card",
            "hall ticket", "rank card", "marksheet", "certificate",
            "exam", "eamcet", "ap eamcet", "ts eamcet", "jee", "neet", 
            "gate", "cat", "gre", "gmat", "sat", "act", "toefl", "ielts",
            "upse", "ias", "ips", "ifos", "ssc", "bank", "railway",
            "defence", "army", "navy", "airforce", "police",
            "constable", "sub inspector", "deputy", "collector",
            "district magistrate", "clerk", "stenographer",
            "assistant", "manager", "executive", "probationary",
            "training", "selection", "commission", "board",
            "authority", "counseling", "counselling",
            "provisional", "syllabus", "pattern", "cutoff", "cut off",
            "merit", "waiting", "reservation", "quota", "category",
            "caste", "income", "verification", "document",
            "apm set", "ap set", "ts set", "set results",
            
            # News / Current Affairs
            "news", "trending", "headlines", "latest", "breaking",
            "current", "today", "tomorrow", "yesterday",
            "election", "budget", "scheme", "launch", "announcement",
            
            # Weather
            "weather", "temperature", "rain", "forecast",
            
            # Sports
            "score", "match", "game", "tournament", "championship",
            "ipl", "world cup", "cricket", "football",
            
            # Health
            "covid", "corona", "pandemic", "vaccine", "cases",
            
            # Business
            "price", "cost", "rate", "stock", "market", "share",
            "gdp", "economy", "inflation",
            
            # General Knowledge
            "who is", "what is", "where is", "when is", "why is", "how is",
            "tell me about", "information about", "facts about",
            "history of", "meaning of", "definition of",
        ]
        
        if any(keyword in text_lower for keyword in force_search_keywords):
            return text
        
        # Explicit search patterns
        explicit_patterns = [
            r"search for (.+)", r"search (.+)", r"find (.+)",
            r"google (.+)", r"look up (.+)", r"browse (.+)"
        ]
        for pattern in explicit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Question patterns
        question_patterns = [
            (r"who is (.+)", "who is"), (r"who are (.+)", "who are"),
            (r"who was (.+)", "who was"), (r"what is (.+)", "what is"),
            (r"what are (.+)", "what are"), (r"what was (.+)", "what was"),
            (r"where is (.+)", "where is"), (r"where are (.+)", "where are"),
            (r"when is (.+)", "when is"), (r"when was (.+)", "when was"),
            (r"why is (.+)", "why is"), (r"how is (.+)", "how is"),
            (r"how are (.+)", "how are"), (r"how does (.+)", "how does"),
            (r"how do (.+)", "how do"), (r"tell me about (.+)", "tell me about"),
            (r"are (.+) results? (released|declared|out)", "are"),
            (r"is (.+) results? (released|declared|out)", "is"),
            (r"(.+) results? (released|declared|out)", "results"),
            (r"when will (.+) results? be (released|declared)", "when"),
            (r"(.+) exam results?", "exam results"),
            (r"(.+) results?", "results"),
        ]
        for pattern, prefix in question_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                query = match.group(1).strip() if match.groups() else text
                skip_phrases = [
                    "my name", "my mother", "my father", "my location",
                    "my city", "my favorite", "i live", "i am from",
                    "system", "agent", "agents", "status", "health"
                ]
                if any(x in query.lower() for x in skip_phrases):
                    return None
                if len(query.strip()) < 2:
                    return None
                return text
        
        return None
    
    def _parse_memory(self, text: str) -> Optional[Dict]:
        """Parse memory commands."""
        text_lower = text.lower()
        
        # Memory recall patterns
        recall_patterns = [
            (r"tell me what is my name", "user.name"),
            (r"tell me my name", "user.name"),
            (r"tell me what is my mother", "user.mother"),
            (r"tell me my mother", "user.mother"),
            (r"tell me what is my father", "user.father"),
            (r"tell me my father", "user.father"),
            (r"can you tell me my name", "user.name"),
            (r"could you tell me my name", "user.name"),
            (r".*what is my name", "user.name"),
            (r".*what is my mother", "user.mother"),
            (r".*what is my father", "user.father"),
            (r".*tell me.*my name", "user.name"),
            (r".*tell me.*my mother", "user.mother"),
            (r".*tell me.*my father", "user.father"),
            (r"what.*my name", "user.name"),
            (r"what.*mother.*name", "user.mother"),
            (r"what.*father.*name", "user.father"),
        ]
        for pattern, key in recall_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {"capability": "recall_fact", "params": {"key": key}}
        
        # Memory remember patterns
        remember_patterns = [
            (r"my name is ([^.!?]+)", "user.name"),
            (r"my mother's name is ([^.!?]+)", "user.mother"),
            (r"my mother name is ([^.!?]+)", "user.mother"),
            (r"my father's name is ([^.!?]+)", "user.father"),
            (r"my favorite color is ([^.!?]+)", "user.favorite_color"),
            (r"i live in ([^.!?]+)", "user.city"),
            (r"i am from ([^.!?]+)", "user.city"),
            (r"i like ([^.!?]+)", "user.likes"),
            (r"my birthday is ([^.!?]+)", "user.birthday"),
            (r"my pet name is ([^.!?]+)", "user.pet"),
            (r"my occupation is ([^.!?]+)", "user.occupation"),
            (r"call me ([^.!?]+)", "user.name"),
            (r"remember my name is ([^.!?]+)", "user.name"),
            (r"remember that my name is ([^.!?]+)", "user.name"),
            (r"save my name as ([^.!?]+)", "user.name"),
            (r"remember that i am ([^.!?]+)", "user.name"),
            (r"i am called ([^.!?]+)", "user.name"),
            (r"i am ([^.!?]+)", "user.name"),
            (r"remember i am ([^.!?]+)", "user.name"),
        ]
        for pattern, key in remember_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r'[.,!?;:]+$', '', value)
                if value and len(value) > 1:
                    return {"capability": "remember_fact", "params": {"key": key, "value": value}}
        
        # Clear memory patterns
        clear_patterns = [
            r"clear memory", r"forget my name", r"reset memory",
            r"clear my name", r"delete my name", r"erase memory",
            r"forget me", r"clear all memory", r"clear everything",
            r"forget everything"
        ]
        for pattern in clear_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return {"capability": "clear_memory", "params": {}}
        
        return None
    
    # =================================================
    # MAIN ROUTE METHOD
    # =================================================
    
    def route(self, text: str) -> Intent:
        """
        Route text to the correct capability.
        
        ROUTING PRIORITY:
        1. Wake word cleanup
        2. Memory commands
        3. System commands
        4. Application close
        5. Application launch
        6. Filesystem commands (NEW - PRIORITY)
        7. Desktop commands
        8. Time/Date
        9. Weather/Location
        10. List Apps
        11. Agent Check
        12. Search/RAG
        13. LLM (fallback)
        """
        if not text or not text.strip():
            return Intent("think", {"query": "Hello"}, confidence=0.5, requires_llm=True)
        
        # =================================================
        # STEP 0: Clean context-aware injection
        # 🔧 FIX: This prevents router from matching against injected history
        # =================================================
        text = self._clean_context_aware_input(text)
        
        # Step 1: Normalize wake words
        text = self._normalize_wake_word(text)
        
        # Step 2: Clean "ok jarvis", "hey jarvis", or just "jarvis" from beginning/end
        text = re.sub(r'^(ok\s+)?(jarvis|hey jarvis|hey)\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+jarvis$', '', text, flags=re.IGNORECASE)
        
        # Step 3: Auto-correct
        corrected = self._auto_correct(text)
        if corrected != text:
            print(f"🔧 [ROUTER] Auto-correct: '{text}' → '{corrected}'")
        text = corrected.lower().strip()
        
        # =================================================
        # STEP 4: Check System Actions (NO LLM)
        # =================================================
        
        # =================================================
        # 4a: MEMORY COMMANDS - PRIORITY 2
        # =================================================
        memory_result = self._check_memory_patterns(text)
        if memory_result:
            print(f"🧠 [ROUTER] Memory → {memory_result}")
            return Intent(
                memory_result["capability"],
                memory_result["params"],
                confidence=1.0,
                requires_llm=False
            )
        
        memory_result = self._parse_memory(text)
        if memory_result:
            print(f"🧠 [ROUTER] Memory → {memory_result}")
            return Intent(
                memory_result["capability"],
                memory_result["params"],
                confidence=1.0,
                requires_llm=False
            )
        
        # =================================================
        # 4b: SYSTEM COMMANDS - PRIORITY 3
        # =================================================
        for phrase, capability in self.supervisor_commands.items():
            if phrase in text:
                print(f"🔧 [ROUTER] Supervisor command → {capability}")
                return Intent(capability, {}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4c: APP CONTROL - PRIORITY 4 & 5 (Close > Launch)
        # =================================================
        app_control = self._parse_app_control(text)
        if app_control:
            action, app_name = app_control
            if action == "close":
                print(f"🛑 [ROUTER] Close app → {app_name}")
                return Intent("close_app", {"app": app_name}, confidence=1.0, requires_llm=False)
            else:
                # Check if it's a UWP app with special URI
                if app_name in self.uwp_protocol_mapping:
                    protocol = self.uwp_protocol_mapping[app_name]
                    print(f"🚀 [ROUTER] Launch UWP app → {app_name} ({protocol})")
                    return Intent("launch_app", {"app": protocol}, confidence=1.0, requires_llm=False)
                
                app_alias = self.app_aliases.get(app_name, app_name)
                print(f"🚀 [ROUTER] Launch app → {app_alias}")
                return Intent("launch_app", {"app": app_alias}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4d: FILESYSTEM COMMANDS - PRIORITY 6 (NEW)
        # =================================================
        fs_result = self._parse_filesystem(text)
        if fs_result:
            action, params = fs_result
            print(f"💾 [ROUTER] Filesystem action → {action}")
            return Intent("filesystem", {"action": action, "params": params}, confidence=0.95, requires_llm=False)
        
        # =================================================
        # 4e: DESKTOP COMMANDS - PRIORITY 7
        # =================================================
        desktop_result = self._parse_desktop(text)
        if desktop_result:
            action, params = desktop_result
            print(f"🖥️ [ROUTER] Desktop action → {action}")
            return Intent("desktop", {"action": action, "params": params}, confidence=0.95, requires_llm=False)
        
        # =================================================
        # 4f: TIME/DATE - PRIORITY 8
        # =================================================
        if self._is_time_query(text):
            print("🕒 [ROUTER] Time query → time_agent")
            return Intent("get_time", {}, confidence=1.0, requires_llm=False)
        
        if self._is_date_query(text):
            print("📅 [ROUTER] Date query → date_agent")
            return Intent("get_date", {}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4g: WEATHER/LOCATION - PRIORITY 9
        # =================================================
        if self._is_weather_query(text) and not self._is_question(text):
            print("🌤️ [ROUTER] Weather query → weather_agent")
            return Intent("weather", {}, confidence=1.0, requires_llm=False)
        
        if self._is_location_query(text):
            print("📍 [ROUTER] Location query → location_agent")
            return Intent("my_location", {}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4h: LIST APPS - PRIORITY 10
        # =================================================
        if re.search(r"list apps|installed apps|what apps|show apps|all apps|available apps", text, re.IGNORECASE):
            print("📋 [ROUTER] List apps")
            return Intent("list_apps", {}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4i: AGENT CHECK - PRIORITY 11
        # =================================================
        agent_check = self._parse_agent_check(text)
        if agent_check:
            print(f"🔍 [ROUTER] Agent check → {agent_check}")
            return Intent("check_agent", {"agent_name": agent_check}, confidence=1.0, requires_llm=False)
        
        # =================================================
        # 4j: SEARCH/RAG - PRIORITY 12
        # =================================================
        search_query = self._parse_search(text)
        if search_query:
            print(f"🔍 [ROUTER] Search → {search_query}")
            return Intent("search", {"query": search_query}, confidence=0.9, requires_llm=False)
        
        # =================================================
        # STEP 5: LLM Fallback - PRIORITY 13
        # =================================================
        print(f"💭 [ROUTER] No system action found → LLM")
        return Intent("think", {"query": text}, confidence=0.5, requires_llm=True)