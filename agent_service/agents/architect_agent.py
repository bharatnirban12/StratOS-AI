import json
from typing import Dict, Any
from agent_service.agents.base_agent import BaseAgent
from shared.contracts.domain import MultiDomainBlueprint, Industry, Capability
from shared.contracts.simulation import AgentResult, AgentType          
from shared.runtime.compiler import WorkflowCompiler
from shared.runtime.governance import RuntimeGovernance

class BusinessArchitectAgent(BaseAgent):
    """
    Harden Architect Agent with Multi-Label Domain Classification
    and integrated Governance/Compilation checks.
    """
    def __init__(self):
        super().__init__("architect")
        self.compiler = WorkflowCompiler()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        idea = input_data.get("goal")
        
        system_prompt = f"""
        You are a FAANG Principal Business Architect.

        Your job is to transform startup ideas into a
        production-grade execution blueprint for a
        multi-agent business intelligence platform.

        Analyze:
        - industry classification
        - business model
        - operational complexity
        - technical requirements
        - financial needs
        - execution risk
        - scalability constraints

        ALLOWED INDUSTRIES:
        {[i.value for i in Industry]}

        ALLOWED CAPABILITIES:
        {[c.value for c in Capability]}

        REQUIRED OUTPUT RULES:
        - Return ONLY valid JSON
        - DO NOT return markdown
        - DO NOT explain outside JSON
        - Include realistic capabilities
        - Minimize unnecessary workflows
        - Optimize for execution efficiency

        REQUIRED SCHEMA KEYS:
        - domains
        - primary_domain
        - business_model
        - required_capabilities
        - reasoning

        Keep reasoning concise and execution-focused.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze Idea: {idea}"}
        ]

        # 1. Generate Raw Blueprint
        raw_blueprint_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema={
                "type": "object",
                "properties": {

                    "primary_domain": {
                        "type": "string"
                    },

                    "business_model": {
                        "type": "string"
                    },

                    "required_capabilities": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },

                    "domains": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string"
                                },
                                "confidence": {
                                    "type": "number"
                                }
                            },
                            "required": [
                                "domain",
                                "confidence"
                            ]
                        }
                    },
                
                    "reasoning": {
                        "type": "string"
                    }
                },

                "required": [
                    "domains",
                    "primary_domain",
                    "business_model",
                    "required_capabilities",
                    "reasoning"
                ]
            },
            api_key=input_data.get("personal_api_key"),
            capability="business_blueprinting"
        )
        
        # ------------------------------------------------
        # HARD FAILSAFE
        # ------------------------------------------------

        if raw_blueprint_data is None:

            raw_blueprint_data = {}

        elif not isinstance(raw_blueprint_data, dict):

            raw_blueprint_data = {
                "domains": [],
                "primary_domain": "technology",
                "business_model": "unknown",
                "required_capabilities": [],
                "reasoning": str(raw_blueprint_data)
            }
        
        try:

            # -----------------------------
            # Normalize domains
            # -----------------------------


            domains_data = raw_blueprint_data.get("domains")

            if not domains_data:

                raw_blueprint_data["domains"] = []

            else:

                normalized_domains = []

                for item in domains_data:

                    # Model returned string
                    if isinstance(item, str):

                        normalized_domains.append({
                            "domain": item,
                            "confidence": 0.85
                        })

                    # Model returned null
                    elif item is None:

                        continue

                    # Already object
                    else:

                        normalized_domains.append(item)

                raw_blueprint_data["domains"] = (
                    normalized_domains
                )
                
                total_confidence = sum(
                    item.get("confidence", 0)
                    for item in normalized_domains
                )

                if total_confidence > 1.0:

                    normalized_domains = [

                        {
                            **item,

                            "confidence":
                                round(
                                    item.get(
                                        "confidence",
                                        0
                                    ) / total_confidence,
                                    2
                                )
                        }

                        for item in normalized_domains
                    ]

                raw_blueprint_data["domains"] = (
                    normalized_domains
                )

            # -----------------------------
            # Normalize reasoning
            # -----------------------------

            if isinstance(
                raw_blueprint_data.get("reasoning"),
                dict
            ):

                raw_blueprint_data["reasoning"] = str(
                    raw_blueprint_data["reasoning"]
                )

            # Safe defaults for missing fields

            raw_blueprint_data.setdefault(
                "domains",
                []
            )

            raw_blueprint_data.setdefault(
                "required_capabilities",
                []
            )
            
            if not raw_blueprint_data[
                "required_capabilities"
            ]:

                raw_blueprint_data[
                    "required_capabilities"
                ] = [
                    "market_analysis",
                    "financial_projection",
                    "operations_planning",
                    "technical_architecture",
                    "growth_strategy",
                    "risk_assessment",
                    "strategic_vision"
                ]

            raw_blueprint_data.setdefault(
                "reasoning",
                "No reasoning provided."
            )

            raw_blueprint_data.setdefault(
                "business_model",
                "Unknown"
            )

            raw_blueprint_data.setdefault(
                "primary_domain",
                "technology"
            )

            # -----------------------------
            # Normalize capabilities
            # -----------------------------
            
            raw_blueprint_data[
                "required_capabilities"
            ] = [

                Capability(cap)

                if isinstance(cap, str)

                else cap

                for cap in raw_blueprint_data[
                    "required_capabilities"
                ]
            ]

            # -----------------------------
            # Enforce Foundation Capabilities
            # -----------------------------
            # Guarantee CEO (Strategic Vision) and Finance (Financial Projection)
            # always run so Evaluator has sufficient data to generate a verdict.
            core_caps = [Capability.STRATEGIC_VISION, Capability.FINANCIAL_PROJECTION]
            for cap in core_caps:
                if cap not in raw_blueprint_data["required_capabilities"]:
                    raw_blueprint_data["required_capabilities"].append(cap)

            blueprint = MultiDomainBlueprint(
                **raw_blueprint_data
            )

        except Exception as e:
            from loguru import logger
            logger.error(f"Blueprint validation failed: {e}")
            raise ValueError(f"Blueprint validation failed: {e}")


        # 2. Apply Runtime Governance (Budgeting/Pruning)
        governance_result = RuntimeGovernance.validate_blueprint(blueprint)
        if not governance_result["is_allowed"]:
            from loguru import logger
            logger.warning(f"Governance violation: {governance_result['issues']}. Pruning...")
            blueprint = RuntimeGovernance.prune_workflow(blueprint)

        # 3. Compile Execution Plan (Cycle Detection / DAG Generation)
        try:
            execution_plan = self.compiler.compile(blueprint)
            
            # Enrich response with the validated execution plan
            response = blueprint.model_dump()
            
            response["required_capabilities"] = [
                c.value
                for c in blueprint.required_capabilities
            ]

            response["compiled_execution_plan"] = execution_plan

            response["governance_status"] = "APPROVED"

            response["orchestration_metrics"] = {
                "total_capabilities": len(
                    blueprint.required_capabilities
                ),

                "parallel_safe": execution_plan.get(
                    "is_parallel_safe",
                    False
                ),

                "estimated_agent_count": execution_plan.get(
                    "total_agents",
                    0
                )
            }
            
            result = AgentResult(
                agent_id=AgentType.ARCHITECT,
                narrative="Business architecture and execution DAG generated.",
                structured_output=response
            )
            
            self.store_memory(
                simulation_id=input_data.get("simulation_id"),
                content=result.model_dump_json(),
                structured_data=result.model_dump()
            )

            return result.model_dump()
        
        except Exception as e:
            from loguru import logger
            logger.error(f"Workflow Compilation Failed: {e}")
            raise
