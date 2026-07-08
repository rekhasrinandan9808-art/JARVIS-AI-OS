from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class TaskStatus(Enum):
    CREATED = "created"
    PLANNING = "planning"
    ROUTED = "routed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    goal: str

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=datetime.utcnow)

    status: TaskStatus = TaskStatus.CREATED

    assigned_agent: str | None = None

    result: Any = None

    metadata: dict = field(default_factory=dict)