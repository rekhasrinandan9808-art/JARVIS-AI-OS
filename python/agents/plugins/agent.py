"""
plugins/agent.py
Agent #15: PluginsAgent -- dynamic plugin loader
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import importlib.util
import os


class PluginsAgent(BaseAgent):
    name = "plugins"
    description = (
        "Loads third-party Python plugins from a directory. Each plugin must expose "
        "a top-level `run(params: dict) -> Any` function."
    )
    agent_id = 15

    def __init__(self, plugin_dir: str = "/tmp/jarvis_plugins"):
        super().__init__()
        self.plugin_dir = plugin_dir
        os.makedirs(self.plugin_dir, exist_ok=True)
        self._loaded: Dict[str, Any] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("list_plugins", "List available plugin files", {}),
            AgentCapability("load_plugin", "Load a plugin module by filename", {"filename": "str"}),
            AgentCapability("run_plugin", "Run a loaded plugin's run() function", {"filename": "str", "params": "dict"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "list_plugins":
            return [f for f in os.listdir(self.plugin_dir) if f.endswith(".py")]
        if action == "load_plugin":
            filename = params["filename"]
            path = os.path.join(self.plugin_dir, filename)
            spec = importlib.util.spec_from_file_location(filename[:-3], path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._loaded[filename] = module
            return {"loaded": filename, "has_run": hasattr(module, "run")}
        if action == "run_plugin":
            filename = params["filename"]
            if filename not in self._loaded:
                raise ValueError("Plugin '" + filename + "' not loaded -- call load_plugin first")
            return self._loaded[filename].run(params.get("params", {}))
