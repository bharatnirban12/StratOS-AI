from typing import Dict, Optional, Union
from shared.contracts.domain import Capability

class ModelTier:
    CHEAP = "google/gemini-2.0-flash-lite-preview-02-05:free"
    BALANCED = "google/gemini-2.0-flash:free"
    REASONING = "openai/gpt-4o-mini"
    HEAVY = "z-ai/glm-4.5-air:free"

class ModelRouter:
    """
    Principal-Grade Model Router.
    Routes requests based on Capability Type and Task Complexity 
    instead of hardcoded agent names.
    """

    # Maps capabilities to model requirements
    # Each agent starts on a DIFFERENT model to avoid rate limit contention
    CAPABILITY_MATRIX: Dict[Capability, str] = {

        Capability.BUSINESS_BLUEPRINTING:
            ModelTier.HEAVY,         # inclusionai/ring — architect is most critical

        Capability.MARKET_ANALYSIS:
            ModelTier.BALANCED,      # minimax — market analysis

        Capability.GROWTH_STRATEGY:
            ModelTier.BALANCED,      # minimax — growth strategy

        Capability.OPERATIONS_PLANNING:
            ModelTier.CHEAP,         # dolphin — operations

        Capability.SUPPLY_CHAIN_DESIGN:
            ModelTier.CHEAP,         # dolphin — supply chain

        Capability.TECHNICAL_ARCHITECTURE:
            ModelTier.REASONING,     # gpt-oss-120b — technical architecture

        Capability.FINANCIAL_PROJECTION:
            ModelTier.HEAVY,         # inclusionai/ring — finance needs precision

        Capability.RISK_ASSESSMENT:
            ModelTier.REASONING,     # gpt-oss-120b — evaluator needs reasoning
    }

    @classmethod
    def get_model(cls, 
                  capability: Optional[Union[Capability, str]] = None, 
                  agent_name: Optional[str] = None,
                  complexity: str = "standard") -> str:
        """
        Determines the optimal model for a given task.
        Priority:
        1. Capability-based lookup
        2. Complexity-based override
        3. Agent-name fallback (Legacy)
        4. Global Default
        """
        
        # 1. Route by Capability
        if capability:
            # Handle both string and enum types
            cap_enum = capability if isinstance(capability, Capability) else None
            if not cap_enum:
                try:
                    cap_enum = Capability(capability)
                except ValueError:
                    pass
            
            if cap_enum in cls.CAPABILITY_MATRIX:
                return cls.CAPABILITY_MATRIX[cap_enum]

        # 2. Route by Complexity
        if complexity == "high":
            return ModelTier.REASONING
        
        # 3. Legacy Fallback (for backward compatibility during migration)
        legacy_map = {
            "architect": ModelTier.BALANCED,
            "market": ModelTier.BALANCED,
            "product": ModelTier.BALANCED,
            "execution": ModelTier.BALANCED,
            "finance": ModelTier.REASONING,
            "evaluator": ModelTier.REASONING,
            "ml": ModelTier.REASONING
        }
        if agent_name in legacy_map:
            return legacy_map[agent_name]

        return ModelTier.CHEAP