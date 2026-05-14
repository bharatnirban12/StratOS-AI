import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent


class MLAgent(BaseAgent):

    def __init__(self):
        super().__init__("ml")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType
        simulation_id = input_data.get("simulation_id")
        goal = input_data.get("goal", "")
        constraints = input_data.get("constraints", {})
        full_context = input_data.get("input", {})

        # Robustly find previous agent data
        ceo_data = next(
            (v for k, v in full_context.items()
             if "ceo" in k or "strategic_vision" in k or "architect" in k),
            {}
        )
        if isinstance(ceo_data, dict) and "structured_output" in ceo_data:
            ceo_data = ceo_data["structured_output"]
        
        messages = [
            {
                "role": "system",
                "content": f"""You are a Senior ML/Infrastructure Engineer designing the technical architecture for:

BUSINESS IDEA: {goal}

Design a complete system architecture, tech stack, scaling strategy, infrastructure cost estimate,
and technical risks SPECIFIC to building this exact product.
Do NOT give generic architecture advice. Every recommendation must directly relate to: {goal}"""
            },
            {
                "role": "user",
                "content": f"""Design the technical architecture for this business:

Business Goal: {goal}
Budget: ${constraints.get('budget', 'Unknown')}
Timeline: {constraints.get('timeline', 'Unknown')}
Business Model: {ceo_data.get('business_model', 'Unknown')}
Vision: {ceo_data.get('strategic_vision', 'N/A')[:500]}

Provide system architecture, recommended tech stack, scaling strategy, 
estimated monthly infrastructure cost, and technical risks — ALL specific to this business."""
            }
        ]

        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",
                "properties": {
                    "system_architecture": {"type": "string"},
                    "recommended_stack": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "scaling_strategy": {"type": "string"},
                    "estimated_monthly_infra_cost": {"type": "number"},
                    "technical_risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "system_architecture",
                    "recommended_stack"
                ]
            },
            
            api_key=input_data.get("personal_api_key"),
            capability="technical_architecture"
        )

        if response_data is None:

            response_data = {

                "system_architecture":
                    "Fallback ML architecture",

                "recommended_stack": [
                    "FastAPI",
                    "Redis",
                    "Postgres"
                ],

                "scaling_strategy":
                    "Horizontal scaling",

                "estimated_monthly_infra_cost":
                    2000,

                "technical_risks": [
                    "LLM latency"
                ]
            }
        
        try:
            result = AgentResult(
                agent_id=AgentType.ML,
                narrative=response_data.get("system_architecture", "Techical architecture completed."),
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
                f"ML Agent Failed: {e}"
            )
            raise