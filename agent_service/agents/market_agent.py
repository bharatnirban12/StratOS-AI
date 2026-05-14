import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent


class MarketAgent(BaseAgent):

    def __init__(self):
        super().__init__("market")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType
        simulation_id = input_data.get("simulation_id")
        goal = input_data.get("goal", "")
        full_context = input_data.get("input", {})

        # Robustly find CEO/architect data with fuzzy key matching
        ceo_data = next(
            (v for k, v in full_context.items()
             if "ceo" in k or "architect" in k or "business_blueprinting" in k or "strategic_vision" in k),
            {}
        )
        # Extract structured output if nested
        if isinstance(ceo_data, dict) and "structured_output" in ceo_data:
            ceo_data = ceo_data["structured_output"]

        business_model = ceo_data.get("business_model", "Unknown")
        target_market = ceo_data.get("target_market", "")
        
        messages = [
            {
                "role": "system",
                "content": f"""You are the Principal Market Analyst for the following business:

BUSINESS IDEA: {goal}

Your job is to provide a SPECIFIC market analysis for THIS exact business idea.
Do NOT provide generic market analysis. Every data point must relate to: {goal}
Focus on the actual industry, actual competitors, and actual market size for this specific product."""
            },
            {
                "role": "user",
                "content": f"""Analyze the market opportunity for this specific business:

Business Goal: {goal}
Business Model: {business_model}
Target Market: {target_market}
CEO Strategy Context: {json.dumps(ceo_data, default=str)[:2000]}

Provide TAM/SAM/SOM, real competitors in this space, target customers, market risks, 
and a go-to-market strategy. ALL analysis must be specific to the business described above."""
            }
        ]
        
        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",
                "properties": {
                    "tam": {"type": "string"},
                    "sam": {"type": "string"},
                    "som": {"type": "string"},
                    "target_customers": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "competitors": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "market_risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "go_to_market_strategy": {
                        "type": "string"
                    },
                    "market_summary": {
                        "type": "string"
                    }
                },
                "required": [
                    "tam",
                    "sam",
                    "som",
                    "market_summary"
                ]
            },           
            
            api_key=input_data.get("personal_api_key")
        )

        if response_data is None:

            response_data = {

                "tam": "1B USD",

                "sam": "100M USD",

                "som": "10M USD",

                "target_customers": [
                    "SMBs"
                ],

                "competitors": [
                    "Legacy competitors"
                ],

                "market_risks": [
                    "Competition",
                    "Adoption friction"
                ],

                "go_to_market_strategy":
                    "Organic growth and partnerships",

                "market_summary":
                    "Fallback market analysis generated."
            }

        try:
            result = AgentResult(
                agent_id=AgentType.MARKET,
                narrative=response_data.get("market_summary", "Market analysis completed."),
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
                f"Market Agent Failed: {e}"
            )
            raise