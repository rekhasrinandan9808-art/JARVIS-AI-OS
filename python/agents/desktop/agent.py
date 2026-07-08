"""
agents/desktop/agent.py
Desktop Agent - Full desktop control with admin privileges
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability
from moa.desktop_controller import DesktopController
import logging

logger = logging.getLogger("jarvis.desktop_agent")


class DesktopAgent(BaseAgent):
    name = "desktop"
    description = "Full desktop control with admin privileges"
    agent_id = 42
    
    def __init__(self):
        super().__init__()
        self.controller = DesktopController()
    
    def capabilities(self) -> List[AgentCapability]:
        return [
            # File operations
            AgentCapability("file_info", "Get file information", {"path": "str"}),
            AgentCapability("list_directory", "List directory contents", {"path": "str"}),
            AgentCapability("search_files", "Search for files", {"root": "str", "pattern": "str"}),
            AgentCapability("create_file", "Create a file", {"path": "str", "content": "str"}),
            AgentCapability("read_file", "Read a file", {"path": "str"}),
            AgentCapability("delete_file", "Delete a file", {"path": "str"}),
            AgentCapability("copy_file", "Copy a file", {"src": "str", "dest": "str"}),
            AgentCapability("move_file", "Move a file", {"src": "str", "dest": "str"}),
            AgentCapability("rename_file", "Rename a file", {"old": "str", "new": "str"}),
            
            # Process operations
            AgentCapability("list_processes", "List running processes", {}),
            AgentCapability("kill_process", "Kill a process by PID", {"pid": "int"}),
            AgentCapability("kill_process_by_name", "Kill processes by name", {"name": "str"}),
            AgentCapability("start_process", "Start a process", {"command": "str"}),
            
            # Window operations
            AgentCapability("list_windows", "List all windows", {}),
            AgentCapability("focus_window", "Focus a window", {"title": "str"}),
            AgentCapability("minimize_window", "Minimize a window", {"title": "str"}),
            AgentCapability("maximize_window", "Maximize a window", {"title": "str"}),
            AgentCapability("close_window", "Close a window", {"title": "str"}),
            
            # System settings
            AgentCapability("set_volume", "Set system volume", {"level": "int"}),
            AgentCapability("get_volume", "Get system volume", {}),
            AgentCapability("set_brightness", "Set screen brightness", {"level": "int"}),
            AgentCapability("set_wallpaper", "Set desktop wallpaper", {"image_path": "str"}),
            
            # System info
            AgentCapability("system_info", "Get system information", {}),
            AgentCapability("get_ip_info", "Get IP information", {}),
            
            # Registry
            AgentCapability("registry_read", "Read registry value", {"key_path": "str", "value_name": "str"}),
            AgentCapability("registry_write", "Write registry value", {"key_path": "str", "value_name": "str", "data": "any"}),
            
            # Automation
            AgentCapability("screenshot", "Take a screenshot", {}),
            AgentCapability("type_text", "Type text", {"text": "str"}),
            AgentCapability("hotkey", "Press hotkey", {"keys": "list"}),
            AgentCapability("mouse_click", "Click mouse", {}),
            AgentCapability("mouse_move", "Move mouse", {"x": "int", "y": "int"}),
            
            # App management
            AgentCapability("find_app", "Find an application", {"app_name": "str"}),
        ]
    
    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute desktop action."""
        logger.info(f"DesktopAgent: {action} with params: {params}")
        
        # Map actions to controller methods
        action_map = {
            "file_info": self.controller.file_info,
            "list_directory": self.controller.list_directory,
            "search_files": self.controller.search_files,
            "create_file": self.controller.create_file,
            "read_file": self.controller.read_file,
            "delete_file": self.controller.delete_file,
            "copy_file": self.controller.copy_file,
            "move_file": self.controller.move_file,
            "rename_file": self.controller.rename_file,
            "list_processes": self.controller.list_processes,
            "kill_process": self.controller.kill_process,
            "kill_process_by_name": self.controller.kill_process_by_name,
            "start_process": self.controller.start_process,
            "list_windows": self.controller.list_windows,
            "focus_window": self.controller.focus_window,
            "minimize_window": self.controller.minimize_window,
            "maximize_window": self.controller.maximize_window,
            "close_window": self.controller.close_window,
            "set_volume": self.controller.set_volume,
            "get_volume": self.controller.get_volume,
            "set_brightness": self.controller.set_brightness,
            "set_wallpaper": self.controller.set_wallpaper,
            "system_info": self.controller.system_info,
            "get_ip_info": self.controller.get_ip_info,
            "registry_read": self.controller.registry_read,
            "registry_write": self.controller.registry_write,
            "screenshot": self.controller.screenshot,
            "type_text": self.controller.type_text,
            "hotkey": self.controller.hotkey,
            "mouse_click": self.controller.mouse_click,
            "mouse_move": self.controller.mouse_move,
            "find_app": self.controller.find_app,
        }
        
        if action in action_map:
            try:
                result = action_map[action](**params)
                return result
            except Exception as e:
                logger.error(f"Desktop action error: {e}")
                return {"success": False, "error": str(e)}
        else:
            return {"success": False, "error": f"Unknown action: {action}"}