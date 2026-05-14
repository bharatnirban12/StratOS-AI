from pydantic import BaseModel, Field, validator
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime

class AgentType(str, Enum):
    ARCHITECT = "architect"
    CEO = "ceo"
    MARKET = "market"
    PRODUCT = "product"
    ML = "ml"
    FINANCE = "finance"
    EXECUTION = "execution"
    EVALUATOR = "evaluator"
    SPECIALIST = "specialist"

class Decision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    CONDITIONAL_APPROVE = "CONDITIONAL_APPROVE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

# --- CORE BUSINESS CONTRACTS ---

class BusinessAssumptions(BaseModel):
    """The central source of truth for simulation inputs."""
    pricing_model: str = Field(..., description="Subscription, Usage, etc.")
    price_per_month: Optional[float] = None
    target_users_year1: int = Field(..., gt=0)
    marketing_budget: float = Field(..., ge=0)
    monthly_churn: Optional[float] = None
    conversion_rate: Optional[float] = None
    cpc_estimate: Optional[float] = None
    team_size: int = Field(..., gt=0)
    avg_salary_annual: float = Field(default=120000.0)
    api_cost_per_user: Optional[float] = None
    infrastructure_complexity: float = Field(default=1.0, ge=1.0, le=5.0)
    
    # --- Realistic Additions ---
    sales_cycle_months: int = Field(default=3, ge=0)
    gross_margin_target: float = Field(default=0.8, ge=0.1, le=0.95)
    cac_target: float = Field(default=500.0, ge=0)
    onboarding_delay_months: int = Field(default=1, ge=0)

# --- AGENT INTERFACE CONTRACTS ---
class ValidationResult(BaseModel):
    is_valid: bool
    missing_fields: List[str] = []
    data_quality_score: float = Field(default=1.0, ge=0, le=1)
    diagnostics: str = ""

class AgentResult(BaseModel):
    """Unified output structure for ALL agents."""
    agent_id: Union[AgentType, str]
    narrative: str = Field(..., description="Detailed strategic reasoning for UX")
    structured_output: Dict[str, Any] = Field(default_factory=dict, description="Machine-readable parameters")
    metrics: Dict[str, float] = Field(default_factory=dict)
    validation: Optional[ValidationResult] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# --- SIMULATION & EVALUATION CONTRACTS ---

class MonthlySnapshot(BaseModel):
    month: int
    users: int
    mrr: float
    cash: float
    burn: float

class RiskProfile(BaseModel):
    p10_cash: float
    p50_cash: float
    p90_cash: float
    bankruptcy_rate: float
    variance_coefficient: float = 0.0

class DecisionVerdict(BaseModel):
    decision: Decision
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    risk_factors: List[str]
    required_changes: List[str] = []
    scores: Dict[str, float] = Field(..., description="market, finance, technical, execution")

class SimulationReport(BaseModel):
    """Final aggregate payload for UI consumption."""
    simulation_id: str
    verdict: DecisionVerdict
    assumptions: BusinessAssumptions
    history: List[MonthlySnapshot]
    risk: RiskProfile
    agent_narratives: Dict[str, str]
    results: Dict[str, AgentResult] = {}
    status: str = "completed"
