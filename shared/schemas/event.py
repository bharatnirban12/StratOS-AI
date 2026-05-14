from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4
from datetime import datetime

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_ASSIGNED = "TASK_ASSIGNED"
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_COMPLETED = "AGENT_COMPLETED"
    AGENT_FAILED = "AGENT_FAILED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    EVALUATION_DONE = "EVALUATION_DONE"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType

    simulation_id: str
    task_id: Optional[str]  = None
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None

    source: str    # service name (orchestrator, agent, evaluator, etc.)
    payload: Dict[str, Any] = Field(default_factory = dict)

    timestamp:datetime = Field(default_factory=datetime.utcnow)

    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "simulation_id": self.simulation_id,
            "task_id": self.task_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "source": self.source,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version
        }

    def to_json(self) -> str:
        return self.model_dump_json()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Optional["Event"]:

        try:

            if not data:
                return None

            if isinstance(
                data.get("event_type"),
                str
            ):

                data["event_type"] = EventType(
                    data["event_type"]
                )

            return Event(
                id=data.get("id", str(uuid4())),

                event_type=data["event_type"],

                simulation_id=data.get(
                    "simulation_id",
                    "unknown"
                ),

                task_id=data.get("task_id"),

                trace_id=data.get(
                    "trace_id",
                    str(uuid4())
                ),

                parent_id=data.get("parent_id"),

                source=data.get(
                    "source",
                    "unknown"
                ),

                payload=data.get(
                    "payload",
                    {}
                ),

                version=data.get(
                    "version",
                    "1.0"
                )
            )

        except Exception:
            return None      
