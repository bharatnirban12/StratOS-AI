from pydantic import BaseModel, Field
from typing import Optional, Dict

class SimulationRequest(BaseModel):
    goal: str = Field(..., min_length=5)
    constraints: Optional[Dict] = Field(default_factory=dict)
