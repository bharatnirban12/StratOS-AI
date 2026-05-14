from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime

# --- GOVERNANCE & VERSIONING ---

class Industry(str, Enum):
    SAAS = "saas"
    RETAIL = "retail"
    LOGISTICS = "logistics"
    MANUFACTURING = "manufacturing"
    MARKETPLACE = "marketplace"
    SERVICES = "services"
    HEALTHCARE = "healthcare"
    TECHNOLOGY = "technology"
    OPERATIONS = "operations"
    OTHER = "other"

class BlueprintVersion(BaseModel):
    major: int = 1
    minor: int = 0
    patch: int = 0
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

class Capability(str, Enum):
    MARKET_ANALYSIS = "market_analysis"
    FINANCIAL_PROJECTION = "financial_projection"
    OPERATIONS_PLANNING = "operations_planning"
    SUPPLY_CHAIN_DESIGN = "supply_chain_design"
    TECHNICAL_ARCHITECTURE = "technical_architecture"
    RISK_ASSESSMENT = "risk_assessment"
    GROWTH_STRATEGY = "growth_strategy"
    BUSINESS_BLUEPRINTING = "business_blueprinting"
    STRATEGIC_VISION = "strategic_vision"

class BlueprintMetadata(BaseModel):
    id: str
    version: str
    author: str = "system"
    created_at: datetime = Field(default_factory=datetime.now)
    capabilities: List[Capability]
    domain_tags: List[str]
    max_tokens: int = 4000
    estimated_cost_usd: float = 0.01

# --- MULTI-DOMAIN INTELLIGENCE ---

class DomainConfidence(BaseModel):
    domain: str
    confidence: float = Field(..., ge=0, le=1)

class MultiDomainBlueprint(BaseModel):
    """Output of the Probabilistic Architect."""
        
    domains: List[DomainConfidence] = Field(default_factory=list)

    primary_domain: str = "unknown"

    business_model: str = "unknown"

    required_capabilities: List[Capability] = Field(
        default_factory=list
    )

    reasoning: str = "No reasoning provided."

    @validator("domains")
    def validate_confidence_sum(cls, v):

        total = sum(d.confidence for d in v)

        if total > 1.0 + 0.01:
            raise ValueError(
                "Domain confidences exceed 1.0"
            )

        return v
    
    def map_capability_to_agent(self, capability: Union[Capability, str]) -> str:
        """Centralized mapping of business capabilities to agent IDs."""
        mapping = {
            Capability.BUSINESS_BLUEPRINTING: "architect",
            Capability.MARKET_ANALYSIS: "market",
            Capability.FINANCIAL_PROJECTION: "finance",
            Capability.OPERATIONS_PLANNING: "execution",
            Capability.SUPPLY_CHAIN_DESIGN: "execution",
            Capability.TECHNICAL_ARCHITECTURE: "ml",
            Capability.RISK_ASSESSMENT: "evaluator",
            Capability.GROWTH_STRATEGY: "product",
            Capability.STRATEGIC_VISION: "ceo"
        }
        # Handle both Enum and String
        try:
            cap_enum = (
                capability
                if isinstance(capability, Capability)
                else Capability(capability)
            )

        except Exception:
            return "evaluator"
        return mapping.get(cap_enum, "evaluator")

    @property
    def weighted_specialists(self) -> List[str]:
        return list({
            self.map_capability_to_agent(c)
            for c in self.required_capabilities
        })

# --- TYPED CAPABILITY CONTRACTS ---

class CapabilityContract(BaseModel):
    """Base for all specialist outputs."""
    agent_id: str
    capability: Capability
    confidence: float
    data: Dict[str, Any]
    validation_status: str = "pending"


class UniversalSimulationState(BaseModel):

    simulation_id: str

    month: int = 0

    metrics: Dict[str, Any] = Field(default_factory=dict)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    status: str = "running"