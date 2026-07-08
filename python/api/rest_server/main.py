"""
api/rest_server/main.py
REST + WebSocket surface over the orchestrator. Protected by an API key --
generate one with `python -m api.rest_server.gen_key`, then either set
JARVIS_API_KEY as an env var before starting the server, or pass one on
first run (it'll generate and print one for you).

Run with:
    uvicorn main:app --reload --port 8000

Every request except / and /health must include:
    Authorization: Bearer <your-api-key>
"""

from __future__ import annotations
import logging
import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI, HTTPException, WebSocket, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from moa.orchestrator import Orchestrator  # noqa: E402
from api.websocket.bridge import websocket_endpoint, register_event_forwarding  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jarvis.rest_server")

app = FastAPI(title="JARVIS AI OS", version="0.2.0")

# Loosen for local dev; tighten to your actual hologram/desktop origins before shipping.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()
register_event_forwarding(orchestrator)  # every agent event now streams to connected hologram clients


# ---- API key auth --------------------------------------------------------------
# Reads from JARVIS_API_KEY env var. If unset, a fresh key is generated on
# startup and printed ONCE to the console -- copy it now, it isn't stored
# anywhere (same "can't be recovered" property as security.generate_api_key).
API_KEY = os.environ.get("JARVIS_API_KEY")
if not API_KEY:
    import secrets
    API_KEY = "jarvis_" + secrets.token_urlsafe(32)
    print("=" * 70)
    print("No JARVIS_API_KEY set -- generated a new one for this session:")
    print(f"  {API_KEY}")
    print("Set JARVIS_API_KEY as an environment variable to keep this stable")
    print("across restarts, otherwise a new one is generated every time.")
    print("=" * 70)


async def require_api_key(authorization: Optional[str] = Header(None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Authorization header. Use: Authorization: Bearer <key>")
    provided = authorization.removeprefix("Bearer ").strip()
    import hmac
    if not hmac.compare_digest(provided, API_KEY):
        raise HTTPException(403, "Invalid API key")


@app.websocket("/ws")
async def ws_route(websocket: WebSocket, key: Optional[str] = None):
    """
    Point your hologram/js/websocket.js at ws://<host>:8000/ws?key=<your-api-key>
    (WebSockets can't send custom headers from a browser, so the key goes
    in the query string here instead of an Authorization header.)
    """
    import hmac
    if not key or not hmac.compare_digest(key, API_KEY):
        await websocket.close(code=4401)  # custom close code = auth failure
        return
    await websocket_endpoint(websocket, orchestrator)


class ExecuteRequest(BaseModel):
    agent: str
    action: str
    params: Optional[Dict[str, Any]] = None


@app.get("/agents", dependencies=[Depends(require_api_key)])
def list_agents():
    return orchestrator.list_agents()


@app.get("/health")
def health():
    # Deliberately unauthenticated -- lets your watchdog/monitoring check
    # liveness without needing the key, same pattern as most production APIs.
    return orchestrator.health()


@app.get("/agents/{agent_name}", dependencies=[Depends(require_api_key)])
def describe_agent(agent_name: str):
    agent = orchestrator.registry.get(agent_name)
    if agent is None:
        raise HTTPException(404, f"No agent named '{agent_name}'")
    return agent.describe()


@app.post("/execute", dependencies=[Depends(require_api_key)])
async def execute(req: ExecuteRequest):
    result = await orchestrator.run(req.agent, req.action, req.params)
    return result.to_dict()


@app.get("/")
def root():
    # Deliberately unauthenticated -- a basic "is this even running" check.
    return {
        "status": "JARVIS AI OS core running",
        "agent_count": len(orchestrator.list_agents()),
        "endpoints": ["/agents", "/agents/{name}", "/execute (POST)", "/health"],
        "auth": "Bearer token required on /agents, /execute, and /ws (as ?key=)",
    }
