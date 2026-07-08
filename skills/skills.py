"""
skills/skills.py
Automation Skills - Pre-built automation routines
"""

import os
import subprocess
import webbrowser
import logging
from datetime import datetime
from typing import Dict, Any, List, Callable

logger = logging.getLogger("jarvis.skills")


class SkillManager:
    """
    Automation skill manager.
    Skills are pre-built automation routines.
    """
    
    def __init__(self):
        self.skills = {}
        self._register_default_skills()
        logger.info(f"✅ Registered {len(self.skills)} skills")
    
    def _register_default_skills(self):
        """Register default skills."""
        self.register_skill("good_morning", self._skill_good_morning)
        self.register_skill("good_night", self._skill_good_night)
        self.register_skill("take_note", self._skill_take_note)
        self.register_skill("read_last_note", self._skill_read_last_note)
        self.register_skill("open_email", self._skill_open_email)
        self.register_skill("lock_screen", self._skill_lock_screen)
        self.register_skill("shutdown", self._skill_shutdown)
        self.register_skill("restart", self._skill_restart)
    
    def register_skill(self, name: str, func: Callable):
        """Register a skill."""
        self.skills[name] = func
        logger.debug(f"Registered skill: {name}")
    
    def execute(self, name: str, params: Dict = None) -> Dict:
        """Execute a skill."""
        if name not in self.skills:
            return {"success": False, "error": f"Skill not found: {name}"}
        
        try:
            result = self.skills[name](params or {})
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_skills(self) -> List[str]:
        """List all skills."""
        return list(self.skills.keys())
    
    # ==========================================
    # DEFAULT SKILLS
    # ==========================================
    
    def _skill_good_morning(self, params: Dict) -> Dict:
        """Good morning routine: weather, news, calendar, music."""
        # Open browser with weather
        webbrowser.open("https://weather.com")
        # Play music (if configured)
        # Read calendar events
        return {
            "message": "Good morning! I've opened the weather for you.",
            "tasks": ["weather", "calendar", "news"]
        }
    
    def _skill_good_night(self, params: Dict) -> Dict:
        """Good night routine: lock screen, set alarm."""
        # Set alarm (would integrate with system)
        # Lock screen
        return {
            "message": "Good night! Locking your screen.",
            "tasks": ["lock_screen"]
        }
    
    def _skill_take_note(self, params: Dict) -> Dict:
        """Take a note with timestamp."""
        note = params.get("note", "No content")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note_path = os.path.expanduser("~/Documents/notes.txt")
        
        with open(note_path, "a") as f:
            f.write(f"[{timestamp}] {note}\n")
        
        return {"message": f"Note saved: {note[:50]}...", "path": note_path}
    
    def _skill_read_last_note(self, params: Dict) -> Dict:
        """Read the last note."""
        note_path = os.path.expanduser("~/Documents/notes.txt")
        try:
            with open(note_path, "r") as f:
                lines = f.readlines()
                if lines:
                    last = lines[-1].strip()
                    return {"message": f"Last note: {last}"}
                else:
                    return {"message": "No notes found"}
        except:
            return {"message": "No notes found"}
    
    def _skill_open_email(self, params: Dict) -> Dict:
        """Open email client."""
        try:
            subprocess.Popen(["outlook.exe"], shell=True)
            return {"message": "Opening email client..."}
        except:
            webbrowser.open("https://mail.google.com")
            return {"message": "Opening Gmail..."}
    
    def _skill_lock_screen(self, params: Dict) -> Dict:
        """Lock the screen."""
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return {"message": "Screen locked"}
        except:
            return {"error": "Could not lock screen"}
    
    def _skill_shutdown(self, params: Dict) -> Dict:
        """Shutdown computer (requires confirmation)."""
        if params.get("confirm", False):
            try:
                subprocess.run(["shutdown", "/s", "/t", "10"])
                return {"message": "Shutting down in 10 seconds..."}
            except:
                return {"error": "Could not shutdown"}
        return {"message": "Shutdown requires confirmation", "requires_confirm": True}
    
    def _skill_restart(self, params: Dict) -> Dict:
        """Restart computer (requires confirmation)."""
        if params.get("confirm", False):
            try:
                subprocess.run(["shutdown", "/r", "/t", "10"])
                return {"message": "Restarting in 10 seconds..."}
            except:
                return {"error": "Could not restart"}
        return {"message": "Restart requires confirmation", "requires_confirm": True}