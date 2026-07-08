"""
runtime/service_registry/registry.py
Distinct from agents/registry.py (which holds the 39 AI agents). This
registry tracks OS-level services -- the REST API, the scheduler,
the health monitor -- and their connection info, so other parts of
the system can discover them (e.g. "where is the REST API listening").
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ServiceInfo:
    name: str
    kind: str  # "http", "grpc", "background_loop", etc.
    host: Optional[str] = None
    port: Optional[int] = None
    registered_at: float = field(default_factory=time.time)
    metadata: Dict[str, str] = field(default_factory=dict)


class ServiceRegistry:
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}

    def register(self, info: ServiceInfo) -> None:
        self._services[info.name] = info

    def deregister(self, name: str) -> None:
        self._services.pop(name, None)

    def get(self, name: str) -> Optional[ServiceInfo]:
        return self._services.get(name)

    def list_all(self) -> List[ServiceInfo]:
        return list(self._services.values())

    def find_by_kind(self, kind: str) -> List[ServiceInfo]:
        return [s for s in self._services.values() if s.kind == kind]
