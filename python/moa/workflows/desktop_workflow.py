"""
moa/workflows/desktop_workflow.py
Desktop Workflow - Full desktop control
"""

from .base_workflow import BaseWorkflow
from moa.desktop_controller import DesktopController
import logging

logger = logging.getLogger("jarvis.desktop_workflow")


class DesktopWorkflow(BaseWorkflow):
    """Workflow for full desktop control."""

    def __init__(self, orchestrator):
        super().__init__(orchestrator)
        self.controller = DesktopController()
    
    async def run(self, **kwargs) -> dict:
        """Execute desktop command."""
        action = kwargs.get("action", "")
        params = kwargs.get("params", {})
        
        logger.info(f"DesktopWorkflow: {action} -> {params}")
        
        # =================================================
        # FIX: Handle get_brightness separately
        # =================================================
        if action == "get_brightness":
            try:
                result = self.controller.get_brightness()
                if result and result.get("success"):
                    return {"success": True, "answer": f"💡 Brightness: {result.get('brightness')}%", **result}
                else:
                    error_msg = result.get("error", "Failed to get brightness") if result else "No result returned"
                    return {"success": False, "error": error_msg, "answer": f"❌ {error_msg}"}
            except Exception as e:
                return {"success": False, "error": str(e), "answer": f"❌ Error: {str(e)}"}
        
        # =================================================
        # Map actions to controller methods
        # =================================================
        action_map = {
            # File operations
            "file_info": self.controller.file_info,
            "list_directory": self.controller.list_directory,
            "search_files": self.controller.search_files,
            "create_file": self.controller.create_file,
            "read_file": self.controller.read_file,
            "delete_file": self.controller.delete_file,
            "copy_file": self.controller.copy_file,
            "move_file": self.controller.move_file,
            "rename_file": self.controller.rename_file,
            
            # Process operations
            "list_processes": self.controller.list_processes,
            "kill_process": self.controller.kill_process,
            "kill_process_by_name": self.controller.kill_process_by_name,
            "start_process": self.controller.start_process,
            "get_process_info": self.controller.get_process_info,
            
            # Window operations
            "list_windows": self.controller.list_windows,
            "focus_window": self.controller.focus_window,
            "minimize_window": self.controller.minimize_window,
            "maximize_window": self.controller.maximize_window,
            "close_window": self.controller.close_window,
            "resize_window": self.controller.resize_window,
            "move_window": self.controller.move_window,
            
            # System settings
            "set_volume": self.controller.set_volume,
            "get_volume": self.controller.get_volume,
            "set_brightness": self.controller.set_brightness,
            "set_power_plan": self.controller.set_power_plan,
            "set_wallpaper": self.controller.set_wallpaper,
            
            # Clipboard
            "get_clipboard": self.controller.get_clipboard,
            "set_clipboard": self.controller.set_clipboard,
            "clear_clipboard": self.controller.clear_clipboard,
            
            # Screen capture
            "screenshot": self.controller.screenshot,
            "screen_size": self.controller.screen_size,
            "get_mouse_position": self.controller.get_mouse_position,
            
            # System info
            "system_info": self.controller.system_info,
            
            # Registry
            "registry_read": self.controller.registry_read,
            "registry_write": self.controller.registry_write,
            "registry_delete": self.controller.registry_delete,
            
            # Automation
            "type_text": self.controller.type_text,
            "press_key": self.controller.press_key,
            "hotkey": self.controller.hotkey,
            "mouse_click": self.controller.mouse_click,
            "mouse_move": self.controller.mouse_move,
            "mouse_scroll": self.controller.mouse_scroll,
            "mouse_drag": self.controller.mouse_drag,
            
            # Services
            "list_services": self.controller.list_services,
            "start_service": self.controller.start_service,
            "stop_service": self.controller.stop_service,
            
            # Network
            "get_ip_info": self.controller.get_ip_info,
            "ping_host": self.controller.ping_host,
            
            # App finding
            "find_app": self.controller.find_app,
            
            # =================================================
            # SYSTEM CLEANER
            # =================================================
            "scan_junk": self.controller.scan_junk_files,
            "clean_system": self.controller.clean_system_junk,
            "empty_recycle_bin": self.controller.empty_recycle_bin,
            "delete_pattern": self.controller.delete_files_by_pattern,
            "delete_large": self.controller.delete_large_files,
        }
        
        if action in action_map:
            try:
                result = action_map[action](**params)
                
                # =================================================
                # DEFENSIVE CHECKS - FIX FOR "Error: None"
                # =================================================
                if result is None:
                    logger.error(f"{action} returned None")
                    return {
                        "success": False,
                        "error": f"{action} returned None",
                        "answer": f"❌ {action} returned no result"
                    }
                
                if not isinstance(result, dict):
                    logger.error(f"{action} returned {type(result)}")
                    return {
                        "success": False,
                        "error": f"Invalid return type: {type(result).__name__}",
                        "answer": "❌ Controller returned an invalid result"
                    }
                
                # Check for success
                if result.get("success"):
                    answer = self._format_success(action, result)
                    return {"success": True, "answer": answer, **result}
                else:
                    # Handle error properly - ensure error is a string
                    error_msg = result.get("error", "Operation failed")
                    if error_msg is None:
                        error_msg = "Unknown error (error field was None)"
                    return {
                        "success": False, 
                        "error": error_msg, 
                        "answer": f"❌ {error_msg}"
                    }
            except Exception as e:
                logger.error(f"Desktop action error: {e}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": str(e), "answer": f"❌ Error: {str(e)}"}
        else:
            return {"success": False, "error": f"Unknown desktop action: {action}", 
                    "answer": f"❌ Unknown desktop action: {action}"}
    
    def _format_success(self, action: str, result: dict) -> str:
        """Format success result for display."""
        formats = {
            "list_directory": f"📁 {result.get('count', 0)} items found",
            "search_files": f"🔍 Found {result.get('count', 0)} files",
            "create_file": f"✅ Created: {result.get('path', '')}",
            "delete_file": f"🗑️ Deleted: {result.get('path', '')}",
            "copy_file": f"📋 Copied to: {result.get('dest', '')}",
            "move_file": f"📦 Moved to: {result.get('dest', '')}",
            "rename_file": f"✏️ Renamed to: {result.get('new', '')}",
            "list_processes": f"🔄 {result.get('count', 0)} processes running",
            "kill_process": f"🛑 Killed process {result.get('pid', '')}",
            "kill_process_by_name": f"🛑 Killed {result.get('count', 0)} processes",
            "start_process": f"▶️ Started: {result.get('command', '')}",
            "list_windows": f"🪟 {result.get('count', 0)} windows found",
            "focus_window": f"🔲 Focused: {result.get('window', '')}",
            "set_volume": f"🔊 Volume set to {result.get('volume', '')}%",
            "get_volume": f"🔊 Volume: {result.get('volume', '')}%",
            "set_brightness": f"💡 Brightness set to {result.get('brightness', '')}%",
            "get_brightness": f"💡 Brightness: {result.get('brightness', '')}%",
            "screenshot": f"📸 Screenshot saved: {result.get('filename', '')}",
            "system_info": "📊 System information retrieved",
            "set_wallpaper": f"🖼️ Wallpaper set: {result.get('wallpaper', '')}",
            "registry_read": f"📋 Registry: {result.get('value_name', '')} = {result.get('data', '')}",
            "type_text": f"⌨️ Typed: {result.get('text', '')[:50]}...",
            "hotkey": f"⌨️ Hotkey: {'+'.join(result.get('keys', []))}",
            "find_app": f"✅ Found app: {result.get('app', '')}",
            "get_ip_info": f"🌐 IP: {result.get('local_ip', '')} (Public: {result.get('public_ip', '')})",
            
            # System Cleaner
            "scan_junk": f"📊 Found {result.get('total_files', 0)} junk files ({result.get('total_size_mb', 0):.2f} MB)",
            "clean_system": f"🧹 {result.get('message', 'System cleaned!')}",
            "empty_recycle_bin": f"🗑️ {result.get('message', 'Recycle Bin emptied!')}",
            "delete_pattern": f"🗑️ {result.get('message', 'Files deleted!')}",
            "delete_large": f"📊 {result.get('message', 'Large files processed!')}",
        }
        return formats.get(action, f"✅ {action} completed successfully")