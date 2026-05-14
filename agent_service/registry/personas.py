from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AgentBlueprint(BaseModel):
    id: str
    role: str
    description: str
    system_prompt_template: str
    required_inputs: List[str]
    expected_outputs: List[str]
    capabilities: List[str] = []

# Registry of common specialist personas
# Mapped to the specific strengths of the Gemma 4 / Nemotron family
PERSONA_REGISTRY = {
    "market_researcher": AgentBlueprint(
        id="market_researcher",
        role="Market Analyst",
        description="Expert in industry trends and competitor analysis.",
        system_prompt_template="You are a Market Analyst. Research the market landscape for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["competitor_matrix", "tam_sam_som", "market_trends"],
        capabilities=["market_analysis"]
    ),
    "finance_architect": AgentBlueprint(
        id="finance_architect",
        role="Finance Architect",
        description="Expert in mathematical modeling and financial projections.",
        system_prompt_template="""You are a Finance Architect. Build a detailed P&L projection for: {goal}.
        IMPORTANT: You MUST provide a 'structured_output' dictionary containing these exact keys for our simulation engine:
        - price_per_month (float)
        - estimated_users_year1 (int)
        - marketing_budget (float total per month)
        - monthly_churn (float e.g. 0.05)
        - team_size (int)
        - api_cost_per_user (float)
        """,
        required_inputs=["goal"],
        expected_outputs=["price_per_month", "estimated_users_year1", "marketing_budget", "monthly_churn", "team_size", "api_cost_per_user"],
        capabilities=["financial_projection"]
    ),
    "risk_analyst": AgentBlueprint(
        id="risk_analyst",
        role="Risk & Compliance Officer",
        description="Specialist in regulatory risk, IP, and licensing.",
        system_prompt_template="You are a Risk Officer. Identify regulatory hurdles and IP risks for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["risk_score", "licensing_requirements"],
        capabilities=["risk_assessment"]
    ),
    "growth_hacker": AgentBlueprint(
        id="growth_hacker",
        role="Growth Engineer",
        description="Expert in digital acquisition and scaling strategy.",
        system_prompt_template="You are a Growth Engineer. Build a digital acquisition strategy for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["keyword_strategy", "cpc_estimates"],
        capabilities=["growth_strategy"]
    ),
    "ops_specialist": AgentBlueprint(
        id="ops_specialist",
        role="Operations Director",
        description="Specialist in organizational scaling and operations.",
        system_prompt_template="You are an Operations Director. Plan the physical/digital operations for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["staffing_plan", "operational_costs"],
        capabilities=["operations_planning"]
    ),
    "supply_chain_expert": AgentBlueprint(
        id="supply_chain_expert",
        role="Supply Chain Architect",
        description="Specialist in procurement and inventory management.",
        system_prompt_template="You are a Supply Chain Architect. Design the inventory strategy for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["inventory_turnover", "cogs_structure"],
        capabilities=["supply_chain_design"]
    ),
    "tech_lead": AgentBlueprint(
        id="tech_lead",
        role="Technical Architect",
        description="Specialist in software architecture and technical feasibility.",
        system_prompt_template="You are a Technical Architect. Design the system architecture for: {goal}.",
        required_inputs=["goal"],
        expected_outputs=["stack_recommendation", "infrastructure_costs"],
        capabilities=["technical_architecture"]
    )
}

def get_persona(persona_id: str) -> Optional[AgentBlueprint]:
    return PERSONA_REGISTRY.get(persona_id)
