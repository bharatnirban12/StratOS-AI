import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent


class ExecutionAgent(BaseAgent):

    def __init__(self):
        super().__init__("execution")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType
        simulation_id = input_data.get("simulation_id")
        goal = input_data.get("goal", "")
        constraints = input_data.get("constraints", {})
        full_context = input_data.get("input", {})

        # Robustly find previous agent data
        architect_data = next(
            (v for k, v in full_context.items()
             if "architect" in k or "business_blueprinting" in k),
            {}
        )
        if isinstance(architect_data, dict) and "structured_output" in architect_data:
            architect_data = architect_data["structured_output"]

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
                "content": f"""You are a Business Execution Specialist creating an operational roadmap for:

BUSINESS IDEA: {goal}

Provide a detailed, phased execution plan with milestones, hiring plan, operational phases,
risks, and dependencies SPECIFIC to building and launching this exact business.
Do NOT give generic execution advice. Every recommendation must directly relate to: {goal}"""
            },
            {
                "role": "user",
                "content": f"""Create the execution roadmap for this business:

Business Goal: {goal}
Budget: ${constraints.get('budget', 'Unknown')}
Timeline: {constraints.get('timeline', 'Unknown')}
Business Model: {architect_data.get('business_model', 'Unknown')}
Primary Domain: {architect_data.get('primary_domain', 'Unknown')}
Market Summary: {market_data.get('market_summary', 'N/A')[:500]}

Provide execution summary, milestones, operational phases, hiring plan,
execution risks, timeline strategy, and dependencies — ALL specific to this business."""
            }
         ]


        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",

                "properties": {

                    "execution_summary": {
                        "type": "string"
                    },

                    "milestones": {
                        "type": "array",
                        "items": {"type": "string"}
                    },

                    "operational_phases": {
                        "type": "array",
                        "items": {"type": "string"}
                    },

                    "hiring_plan": {
                        "type": "array",
                        "items": {"type": "string"}
                    },

                    "execution_risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },

                    "timeline_strategy": {
                        "type": "string"
                    },

                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },

                "required": [
                    "execution_summary",
                    "milestones",
                    "operational_phases"
                ]
            },
            
            api_key=input_data.get("personal_api_key")
        )
        
         # Normalize list response
        if response_data is None:

            response_data = {
                "execution_summary": "Fallback execution strategy.",
                "milestones": ["Planning", "Launch"],
                "operational_phases": ["Development", "Growth"],
                "hiring_plan": ["Engineer"],
                "execution_risks": ["Budget constraints"],
                "timeline_strategy": "Agile rollout",
                "dependencies": ["Funding"]
            }

        try:
            result = AgentResult(
                agent_id=AgentType.EXECUTION,
                narrative=response_data.get("execution_summary", "Execution roadmap completed."),
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
                f"Execution Agent Failed: {e}"
            )
            raise