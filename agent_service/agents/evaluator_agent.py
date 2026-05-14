from typing import Dict, Any
import json
from agent_service.agents.base_agent import BaseAgent


class EvaluatorAgent(BaseAgent):

    def __init__(self):
        super().__init__("evaluator")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType, DecisionVerdict, Decision
        simulation_id = input_data.get("simulation_id")
        full_context = input_data.get("input")
        
        # 1. PRE-ANALYSIS: Data Quality Check
        # Robustly extract from orchestrator state.results where keys are 'agent:capability'
        finance_data = next((v for k, v in full_context.items() if "finance" in k or "financial_projection" in k), {})
        ceo_data = next((v for k, v in full_context.items() if "ceo" in k or "strategic_vision" in k or "business_blueprinting" in k), {})
        
        # Robust context extraction
        if isinstance(finance_data, dict) and "structured_output" in finance_data:
            finance_data = finance_data["structured_output"]
        
        assumptions = finance_data.get("assumptions", {})
        mc_results = finance_data.get("risk_profile", {})
        sim_results = finance_data.get("simulation", {})
        
        # Detect missing/zero values that cause bias
        missing_critical_data = [k for k, v in assumptions.items() if v == 0 and k in ["price_per_month", "target_users_year1"]]
        
        messages = [
            {
                "role": "system",
                "content": """You are a Strategic Advisor and Investment Committee Lead.
                Provide a BALANCED evaluation based on the multi-agent simulation results.
                
                You must return a JSON object that adheres to the DecisionVerdict schema.
                REQUIRED FIELDS:
                - decision: One of [APPROVE, REJECT, CONDITIONAL_APPROVE, INSUFFICIENT_DATA]
                - confidence: 0.0 to 1.0
                - reasoning: Detailed explanation
                - risk_factors: List of strings
                - scores: Map of {market, finance, technical, execution} to 0-10 floats
                
                SCORING RULES:
                - DO NOT use percentages or ROI (e.g. 400) as scores.
                - ALL scores MUST be between 0.0 and 10.0.
                - Use the 'finance_rating' provided in the context for the finance score.
                
                DECISION RULES:
                - INSUFFICIENT_DATA: If price=0 or users=0 in finance assumptions.
                - CONDITIONAL_APPROVE: If economics are tight but strategy is solid.
                - REJECT: Only for fundamental business model failure.
                """
            },
            {
                "role": "user",
                "content": f"""
                Review this simulation context:
                - CEO Strategic Vision: {ceo_data.get('narrative', 'None provided')}
                - Business Assumptions: {json.dumps(assumptions)}
                - Financial Projections: {json.dumps(sim_results)}
                - Recommended Finance Score (0-10): {sim_results.get('finance_rating', 'N/A')}
                - Monte Carlo Risk Profile: {json.dumps(mc_results)}
                
                Provide your final strategic evaluation.
                """
            }
        ]

        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema=DecisionVerdict.model_json_schema(),
            api_key=input_data.get("personal_api_key")
        )
        
        if response_data is None:

            response_data = {

                "decision": "CONDITIONAL_APPROVE",

                "confidence": 0.5,

                "reasoning":
                    "Fallback evaluation generated.",

                "risk_factors": [
                    "Limited market validation"
                ],

                "scores": {
                    "market": 6.0,
                    "finance": 5.0,
                    "technical": 7.0,
                    "execution": 5.0
                }
            }

        try:
            # Enforce calibration logic for missing data
            if missing_critical_data or response_data.get("decision") == "INSUFFICIENT_DATA":
                response_data["decision"] = "INSUFFICIENT_DATA"
                response_data["confidence"] = min(response_data.get("confidence", 0.0), 0.3)
            
            # Validate against DecisionVerdict
            verdict = DecisionVerdict(**response_data)
            
            result = AgentResult(
                agent_id=AgentType.EVALUATOR,
                narrative=verdict.reasoning,
                structured_output=verdict.model_dump()
            )
            
            self.store_memory(
                simulation_id=simulation_id,
                content=result.model_dump_json(),
                structured_data=result.model_dump()
            )
            return result.model_dump()
        
        except Exception as e:
            from loguru import logger
            logger.error(f"Evaluator Contract validation failed: {e}")
            raise