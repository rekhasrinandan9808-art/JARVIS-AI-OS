"""
robotics/agent.py
Agent #13: RoboticsAgent -- hardware actuator/sensor interface
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class RoboticsAgent(BaseAgent):
    name = "robotics"
    description = (
        "Interface for robotics hardware (motors, servos, sensors). "
        "This is hardware-agnostic scaffolding -- plug in your board's SDK "
        "(e.g. RPi.GPIO, pyserial, ROS2 client) inside _run()."
    )
    agent_id = 13

    def __init__(self):
        super().__init__()
        self._simulated_state: Dict[str, Any] = {"motors": {}, "sensors": {}}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("set_motor", "Set a motor's speed/position (simulated until hardware wired in)", {"motor_id": "str", "value": "float"}),
            AgentCapability("read_sensor", "Read a sensor value (simulated until hardware wired in)", {"sensor_id": "str"}),
            AgentCapability("get_state", "Get full simulated hardware state", {}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "set_motor":
            self._simulated_state["motors"][params["motor_id"]] = params["value"]
            return {"motor_id": params["motor_id"], "value": params["value"], "note": "simulated -- wire real hardware driver here"}
        if action == "read_sensor":
            return self._simulated_state["sensors"].get(params["sensor_id"], 0.0)
        if action == "get_state":
            return self._simulated_state
