"""
api/websocket/bridge.py
Real-time bridge between the orchestrator and your existing hologram
project (hologram/js/jarvisConnector.js + websocket.js). Two things
flow over this socket:

1. Client -> server: {"type": "execute", "agent": "...", "action": "...", "params": {...}}
   Server replies:    {"type": "result", "request_id": ..., ...AgentResult}

2. Server -> client (unprompted): every event published on the orchestrator's
   EventRouter is pushed to all connected clients, e.g.
   {"type": "event", "topic": "agent.task.completed", "payload": {...}}
   Your hologram.js can subscribe to these to trigger visual reactions
   (e.g. pulse the energy core whenever agent.task.completed fires).

Wire this into your existing hologram/js/websocket.js by pointing it at
ws://<host>:8000/ws and handling messages of type "result" and "event".
"""

from __future__ import annotations
import json
import logging
from typing import Any, Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("jarvis.websocket_bridge")


class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)
        logger.info("Hologram client connected (%d total)", len(self.active))

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)
        logger.info("Hologram client disconnected (%d total)", len(self.active))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def register_event_forwarding(orchestrator) -> None:
    """Call once at startup: forwards every orchestrator event to all connected hologram clients."""

    async def forward(event) -> None:
        await manager.broadcast({
            "type": "event",
            "topic": event.topic,
            "source": event.source,
            "payload": event.payload,
            "timestamp": event.timestamp,
        })

    orchestrator.events.subscribe("*", forward)


async def websocket_endpoint(ws: WebSocket, orchestrator) -> None:
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "error": "invalid JSON"})
                continue

            if msg.get("type") != "execute":
                await ws.send_json({"type": "error", "error": f"unknown message type '{msg.get('type')}'"})
                continue

            result = await orchestrator.run(
                msg.get("agent", ""), msg.get("action", ""), msg.get("params", {})
            )
            await ws.send_json({
                "type": "result",
                "request_id": msg.get("request_id"),
                **result.to_dict(),
            })
    except WebSocketDisconnect:
        manager.disconnect(ws)
