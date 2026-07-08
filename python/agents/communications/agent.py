"""
communications/agent.py
Agent #23: CommunicationsAgent -- contacts registry and message dispatch interface
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


class CommunicationsAgent(BaseAgent):
    name = "communications"
    description = (
        "Manages a contacts registry and drafts outgoing messages. Actual send (SMS/email/IM) "
        "requires wiring real credentials -- Twilio for SMS, SMTP for email, bot tokens for IM."
    )
    agent_id = 23

    def __init__(self):
        super().__init__()
        self._contacts: Dict[str, Dict[str, str]] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("add_contact", "Add a contact", {"contact_id": "str", "name": "str", "email": "str", "phone": "str"}),
            AgentCapability("list_contacts", "List all contacts", {}),
            AgentCapability("draft_message", "Draft a message for a contact (does not send)", {"contact_id": "str", "body": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "add_contact":
            self._contacts[params["contact_id"]] = {
                "name": params.get("name", ""), "email": params.get("email", ""), "phone": params.get("phone", ""),
            }
            return {"added": params["contact_id"]}
        if action == "list_contacts":
            return self._contacts
        if action == "draft_message":
            contact = self._contacts.get(params["contact_id"])
            if not contact:
                raise ValueError("Unknown contact: " + params["contact_id"])
            return {"to": contact, "body": params["body"], "status": "drafted -- wire SMTP/Twilio to actually send"}
