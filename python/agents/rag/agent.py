"""
rag/agent.py
Agent #2: RAGAgent -- retrieval-augmented generation over stored documents
"""

from __future__ import annotations
from typing import Any, Dict, List
from ..base_agent import BaseAgent, AgentCapability


import difflib


class RAGAgent(BaseAgent):
    name = "rag"
    description = "Indexes text documents and retrieves the most relevant passages for a query."
    agent_id = 2

    def __init__(self):
        super().__init__()
        self._docs: Dict[str, str] = {}

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability("add_document", "Add a document to the index", {"doc_id": "str", "text": "str"}),
            AgentCapability("query", "Retrieve top-k relevant documents", {"query": "str", "k": "int"}),
            AgentCapability("remove_document", "Remove a document from the index", {"doc_id": "str"}),
        ]

    async def _run(self, action: str, params: Dict[str, Any]) -> Any:
        if action == "add_document":
            self._docs[params["doc_id"]] = params["text"]
            return {"indexed": params["doc_id"]}
        if action == "remove_document":
            self._docs.pop(params["doc_id"], None)
            return {"removed": params["doc_id"]}
        if action == "query":
            query = params["query"]
            k = params.get("k", 3)
            scored = []
            for doc_id, text in self._docs.items():
                ratio = difflib.SequenceMatcher(None, query.lower(), text.lower()).ratio()
                scored.append((ratio, doc_id, text[:280]))
            scored.sort(reverse=True)
            return [
                {"doc_id": d, "score": round(s, 3), "snippet": t}
                for s, d, t in scored[:k]
            ]
