"""
iot/agent.py
Agent #14: IoTAgent -- smart-home / IoT device registry and control
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class IoTAgent(BaseAgent):
    name = "iot"
    description = (
        "Registry of IoT/smart-home devices and a control interface. "
        "Wire the send() method to your MQTT broker or vendor API (Zigbee2MQTT, Home Assistant, etc)."
    )
    agent_id = 14

    def __init__(self):
        super().__init__()
        self._devices: Dict[str, Dict[str, Any]] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("register_device", "Register a device", {"device_id": "str", "type": "str"}),
            AgentCapability("set_state", "Set a device's state (simulated until broker wired in)", {"device_id": "str", "state": "dict"}),
            AgentCapability("get_state", "Get a device's last known state", {"device_id": "str"}),
            AgentCapability("list_devices", "List registered devices", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "register_device":
            self._devices[params["device_id"]] = {"type": params["type"], "state": {}}
            return {"registered": params["device_id"]}
        if action == "set_state":
            dev = self._devices.setdefault(params["device_id"], {"type": "unknown", "state": {}})
            dev["state"].update(params["state"])
            return dev["state"]
        if action == "get_state":
            return self._devices.get(params["device_id"], {}).get("state", {})
        if action == "list_devices":
            return list(self._devices.keys())
