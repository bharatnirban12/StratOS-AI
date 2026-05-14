import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent
from agent_service.registry.personas import get_persona
from shared.contracts.simulation import AgentResult, AgentType

class UniversalAgentRuntime(BaseAgent):
    """
    A generic agent executor that hydrates a persona from the registry.
    This replaces hardcoded agent classes.
    """
    def __init__(self, persona_id: str):
        blueprint = get_persona(persona_id)
        if not blueprint:
            raise ValueError(f"Persona {persona_id} not found in registry.")
        
        super().__init__(persona_id)
        self.blueprint = blueprint

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        goal = input_data.get("goal")
        context = input_data.get("input", {})
        
        # Hydrate the template
        system_content = self.blueprint.system_prompt_template.format(
            goal=goal,
            focus=", ".join(self.blueprint.expected_outputs)
        )
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"Current Context: {json.dumps(context)}"}
        ]

        # Determine the primary capability for model routing
        capability = self.blueprint.capabilities[0] if self.blueprint.capabilities else None
        
        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",
                "properties": {
                    "narrative": {"type": "string"},
                    "structured_output": {"type": "object"},
                    "metrics": {"type": "object"}
                }
            },
            api_key=input_data.get("personal_api_key"),
            capability=capability
        )

        # Map to AgentResult
        result = AgentResult(
            agent_id=self.name,
            narrative=response_data.get("narrative", f"{self.blueprint.role} analysis complete."),
            structured_output=response_data.get("structured_output", {}),
            metrics=response_data.get("metrics", {})
        )

        # Store in vector memory
        self.store_memory(input_data.get("simulation_id"), result.model_dump_json())

        return result.model_dump()
