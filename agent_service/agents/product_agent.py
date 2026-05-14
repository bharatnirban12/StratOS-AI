import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent


class ProductAgent(BaseAgent):

    def __init__(self):
        super().__init__("product")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType
        simulation_id = input_data.get("simulation_id")
        goal = input_data.get("goal", "")
        full_context = input_data.get("input", {})

        # Robustly find previous agent data
        ceo_data = next(
            (v for k, v in full_context.items()
             if "ceo" in k or "strategic_vision" in k or "architect" in k),
            {}
        )
        if isinstance(ceo_data, dict) and "structured_output" in ceo_data:
            ceo_data = ceo_data["structured_output"]

        market_data = next(
            (v for k, v in full_context.items()
             if "market" in k),
            {}
        )
        if isinstance(market_data, dict) and "structured_output" in market_data:
            market_data = market_data["structured_output"]
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a Principal Product Manager designing the product strategy for:

BUSINESS IDEA: {goal}

Design a product roadmap, MVP scope, pricing tiers, and growth strategy SPECIFIC to this business.
Do NOT give generic product advice. Every recommendation must directly relate to: {goal}"""
            },
            {
                "role": "user",
                "content": f"""Create the product strategy for this business:

Business Goal: {goal}
Business Model: {ceo_data.get('business_model', 'Unknown')}
Target Market: {market_data.get('target_customers', 'Unknown')}
Market Summary: {market_data.get('market_summary', 'N/A')[:500]}
CEO Vision: {ceo_data.get('strategic_vision', 'N/A')[:500]}

Provide product roadmap, pricing tiers, retention strategy, onboarding strategy, 
go-to-market funnel, growth loops, and competitive differentiators — ALL specific to this business."""
            }
        ]

        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                        "type": "object",

                        "properties": {

                            "product_summary": {
                                "type": "string"
                            },

                            "product_roadmap": {
                                "type": "array",
                                "items": {"type": "string"}
                            },

                            "pricing_tiers": {
                                "type": "array",
                                "items": {"type": "string"}
                            },

                            "retention_strategy": {
                                "type": "string"
                            },

                            "onboarding_strategy": {
                                "type": "string"
                            },

                            "go_to_market_funnel": {
                                "type": "string"
                            },

                            "growth_loops": {
                                "type": "array",
                                "items": {"type": "string"}
                            },

                            "competitive_differentiators": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },

                        "required": [
                            "product_summary",
                            "product_roadmap",
                            "pricing_tiers"
                        ]
                    },            
                    
            api_key=input_data.get("personal_api_key")
        )

        
        if response_data is None:

            response_data = {

                "product_summary":
                    "Fallback product strategy generated.",

                "product_roadmap": [
                    "MVP",
                    "Beta",
                    "Scale"
                ],

                "pricing_tiers": [
                    "Starter",
                    "Pro"
                ],

                "retention_strategy":
                    "Email engagement",

                "onboarding_strategy":
                    "Guided onboarding",

                "go_to_market_funnel":
                    "SEO and partnerships",

                "growth_loops": [
                    "Referral system"
                ],

                "competitive_differentiators": [
                    "AI automation"
                ]
            }
        
        try:
            result = AgentResult(
                agent_id=AgentType.PRODUCT,
                narrative=response_data.get("product_summary", "Product roadmap completed."),
                structured_output= response_data
            )
            self.store_memory(
                simulation_id=simulation_id,
                content=result.model_dump_json(),
                structured_data=result.model_dump()
            )
            
            return result.model_dump()
        
        except Exception as e:
            from loguru import logger

            logger.exception(
                f"Product Agent Failed: {e}"
            )
            raise