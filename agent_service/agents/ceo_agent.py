from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent


class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("ceo")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType, BusinessAssumptions
        simulation_id = input_data.get("simulation_id")
        goal = input_data.get("goal")
        budget = input_data.get("budget", 50000)
        
        messages = [
            {
                "role": "system",
                "content": f"""You are the Principal CEO and Strategic Architect. 
                Design a business strategy for: {goal}
                
                Economic Constraints:
                - TOTAL BUDGET: ${budget}
                - TIMELINE: 12 months
                
                Return ONLY the JSON fields defined below.
                The 'structured_output' MUST contain the business assumptions for the simulation engine.
                """
            },
            {
                "role": "user",
                "content": f"""
                Provide your strategic narrative and structured parameters for this business.
                
                REQUIRED PARAMETERS in 'structured_output':
                - pricing_model (string)
                - price_per_month (float)
                - target_users_year1 (int)
                - marketing_budget (float)
                - monthly_churn (float)
                - conversion_rate (float)
                - cpc_estimate (float)
                - team_size (int)
                - avg_salary_annual (float)
                - api_cost_per_user (float)
                - infrastructure_complexity (float)
                """
            }
        ]

        # Use the NEW structured generation with schema guidance
        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",

                "properties": {

                    "strategic_vision": {
                        "type": "string"
                    },

                    "business_model": {
                        "type": "string"
                    },

                    "core_value_proposition": {
                        "type": "string"
                    },

                    "target_market": {
                        "type": "string"
                    },

                    "revenue_strategy": {
                        "type": "string"
                    },

                    "key_risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },

                    "competitive_advantage": {
                        "type": "string"
                    },
                
                    "initial_business_assumptions": {
                        "type": "object"
                    }
                },

                "required": [
                    "strategic_vision",
                    "business_model",
                    "core_value_proposition"
                ]
            },
            
            api_key=input_data.get("personal_api_key")
        )

        if response_data is None:

            response_data = {

                "domains": [
                    {
                        "domain": "technology",
                        "confidence": 0.9
                    }
                ],

                "primary_domain": "technology",

                "business_model": "saas",

                "required_capabilities": [
                    "market_analysis",
                    "financial_projection",
                    "growth_strategy",
                    "risk_assessment"
                ],

                "reasoning":
                    "Fallback blueprint generated."
            }
        # Ensure we have a valid AgentResult object
        try:
            result = AgentResult(
                agent_id=AgentType.CEO,
                narrative=response_data.get("strategic_vision", "Strategic vision generated."),
                structured_output=response_data
            )
            
            # Store in memory for future reference
            self.store_memory(
                simulation_id=simulation_id,
                content=result.model_dump_json(),
                structured_data=result.model_dump()
            )            
            return result.model_dump()
        
        except Exception as e:
            from loguru import logger
            logger.error(f"CEO Contract validation failed: {e}")
            # Minimal fallback that satisfies the contract
            return AgentResult(
                agent_id=AgentType.CEO,
                narrative="CEO strategy generation failed.",
                structured_output={
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "recoverable": True,
                    "missing_fields": [
                        "price_per_month",
                        "target_users_year1",
                        "marketing_budget"
                    ]
                }
            ).model_dump()