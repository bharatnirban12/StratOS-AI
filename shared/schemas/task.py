from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentType(str, Enum):
    ARCHITECT = "architect"
    CEO = "ceo"
    MARKET = "market"
    PRODUCT = "product"
    ML = "ml"
    FINANCE = "finance"
    EXECUTION = "execution"
    EVALUATOR = "evaluator"


class Task(BaseModel):
    id: str = Field(default_factory = lambda: str(uuid4()))
    simulation_id: str

    agent: AgentType
    status: TaskStatus = TaskStatus.CREATED

    goal: str

    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)

    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    retries: int = 0
    max_retries : int = 3


    def mark_in_progress(self):
        self.status = TaskStatus.IN_PROGRESS

    def mark_success(self, result: Dict[str, Any]):
        self.status = TaskStatus.SUCCESS
        self.result = result

    def mark_failed(self, error: str):
        self.status = TaskStatus.FAILED
        self.error = error

    def should_retry(self) -> bool:

        self.retries += 1

        return self.retries <= self.max_retries