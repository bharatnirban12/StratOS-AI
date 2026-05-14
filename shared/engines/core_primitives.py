import numpy as np
from typing import Dict, Any

class EconomicPrimitives:
    """
    Standardized mathematical modules for growth, risk, and cashflow.
    Used across all industry-specific engines to ensure consistency.
    """
    
    @staticmethod
    def calculate_marketing_growth(budget: float, cpc: float, conv_rate: float) -> int:
        if cpc <= 0:
            return 0

        traffic = budget / cpc
        return int(traffic * conv_rate)

    @staticmethod
    def calculate_organic_growth(base_users: int, k_factor: float = 0.05) -> int:
        """Viral growth modeling."""
        return int(base_users * k_factor)

    @staticmethod
    def apply_stochastic_variance(value: float, variance: float = 0.1) -> float:
        """Adds Gaussian noise to a deterministic value."""
        return max(
            0,
            value * np.random.normal(1.0, variance)
        )

    @staticmethod
    def calculate_burn(fixed_costs: float, variable_costs: float, scale_factor: float) -> float:
        return fixed_costs + (variable_costs * scale_factor)

class RiskEngine:
    """Shared logic for bankruptcy and tail-risk analysis."""
    
    @staticmethod
    def check_bankruptcy(cash: float, threshold: float = -500000) -> bool:
        return cash < threshold
