"""
moa/workflows/close_workflow.py
Close Workflow - Closes running applications
"""

from .base_workflow import BaseWorkflow
import subprocess
import psutil
import logging

logger = logging.getLogger("jarvis.close_workflow")


class CloseWorkflow(BaseWorkflow):
    """Workflow for closing applications."""
    
    # Map common app names to process names
    PROCESS_MAP = {
        "notepad": "notepad.exe",
        "calculator": "calculator.exe",
        "calc": "calculator.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "outlook": "outlook.exe",
        "vscode": "code.exe",
        "visual studio code": "code.exe",
        "code": "code.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "spotify": "spotify.exe",
        "vlc": "vlc.exe",
        "discord": "discord.exe",
        "slack": "slack.exe",
        "steam": "steam.exe",
    }
    
    async def run(self, **kwargs) -> dict:
        """Close an application."""
        app = kwargs.get("app", "").strip()
        force = kwargs.get("force", False)
        
        if not app:
            return {
                "success": False,
                "answer": "What would you like me to close?",
                "error": "No app specified"
            }
        
        logger.info(f"Closing: {app}")
        
        # Get the process name
        process_name = self.PROCESS_MAP.get(app.lower(), app)
        if not process_name.endswith('.exe'):
            process_name += '.exe'
        
        try:
            closed = []
            
            # Find and close processes
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name']
                    if proc_name and proc_name.lower() == process_name.lower():
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        closed.append(proc.info['pid'])
                        logger.info(f"Closed {proc_name} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if closed:
                return {
                    "success": True,
                    "answer": f"✅ Closed {app} ({len(closed)} instance(s))",
                    "action": "close_app",
                    "closed_app": app,
                    "pids": closed,
                    "force": force
                }
            else:
                return {
                    "success": False,
                    "answer": f"❌ Could not find {app} running. It may already be closed.",
                    "action": "close_app",
                    "closed_app": app,
                    "pids": []
                }
                
        except Exception as e:
            logger.error(f"Error closing {app}: {e}")
            return {
                "success": False,
                "answer": f"❌ Could not close {app}. Error: {str(e)}",
                "action": "close_app",
                "closed_app": app,
                "error": str(e)
            }