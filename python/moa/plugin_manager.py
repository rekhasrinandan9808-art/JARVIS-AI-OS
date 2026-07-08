"""
moa/plugin_manager.py
Plugin System - Dynamic loading of capabilities
"""

import os
import sys
import importlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("jarvis.plugin_manager")


@dataclass
class Plugin:
    """Plugin metadata."""
    name: str
    version: str
    author: str
    description: str
    module: str
    enabled: bool = True


class PluginManager:
    """
    Dynamic plugin system for JARVIS.
    
    Plugins are Python modules in the 'plugins' directory.
    Each plugin must have:
    - A class named 'Plugin' with a 'run' method
    - A 'info' dictionary with metadata
    """
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_dir = Path(__file__).parent.parent / "plugins"
        self.plugin_dir.mkdir(exist_ok=True)
        self._loaded = False
    
    def discover(self):
        """Discover all plugins in the plugins directory."""
        if self._loaded:
            return
        
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                self._load_plugin(item.name)
            elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                self._load_plugin(item.stem)
        
        self._loaded = True
        logger.info(f"🔌 Discovered {len(self.plugins)} plugins")
    
    def _load_plugin(self, name: str):
        """Load a plugin by name."""
        try:
            # Add plugins directory to path
            sys.path.insert(0, str(self.plugin_dir))
            
            # Import module
            module = importlib.import_module(name)
            
            # Get plugin info
            if hasattr(module, 'info'):
                info = module.info
                plugin = Plugin(
                    name=info.get('name', name),
                    version=info.get('version', '1.0.0'),
                    author=info.get('author', 'Unknown'),
                    description=info.get('description', ''),
                    module=name
                )
                self.plugins[name] = plugin
                logger.info(f"✅ Loaded plugin: {plugin.name} v{plugin.version}")
            else:
                logger.warning(f"⚠️ Plugin {name} missing 'info' dict")
            
        except Exception as e:
            logger.error(f"❌ Failed to load plugin {name}: {e}")
    
    def enable(self, name: str):
        """Enable a plugin."""
        if name in self.plugins:
            self.plugins[name].enabled = True
            logger.info(f"✅ Enabled plugin: {name}")
    
    def disable(self, name: str):
        """Disable a plugin."""
        if name in self.plugins:
            self.plugins[name].enabled = False
            logger.info(f"🛑 Disabled plugin: {name}")
    
    def execute(self, name: str, params: Dict = None) -> Any:
        """Execute a plugin."""
        if name not in self.plugins:
            return {"success": False, "error": f"Plugin not found: {name}"}
        
        plugin = self.plugins[name]
        if not plugin.enabled:
            return {"success": False, "error": f"Plugin disabled: {name}"}
        
        try:
            module = importlib.import_module(plugin.module)
            if hasattr(module, 'run'):
                result = module.run(params or {})
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": "Plugin has no 'run' function"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_plugins(self) -> List[Dict]:
        """Get all plugins."""
        return [{
            "name": p.name,
            "version": p.version,
            "author": p.author,
            "description": p.description,
            "enabled": p.enabled
        } for p in self.plugins.values()]