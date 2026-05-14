from agent_service.agents import market_agent
from streamlit.elements.lib import mutable_tab_container
from agent_service.agents import architect_agent
from typing import Dict, Any
from shared.engines.base_engine import BaseSimulationEngine
from shared.contracts.domain import UniversalSimulationState

class RetailSimulationEngine(BaseSimulationEngine):
    """
    Simulation engine for physical retail / restaurants.
    Focuses on: Foot Traffic, Inventory, Rent, and COGS.
    """
    
    def initialize(self, simulation_id: str, assumptions: Dict[str, Any]) -> UniversalSimulationState:
        initial_cash = assumptions.get("initial_capital", 100000)
        return UniversalSimulationState(
            simulation_id=simulation_id,
            month=0,
            metrics={
                "cash": initial_cash,
                "inventory_level": assumptions.get("initial_inventory", 10000),
                "cumulative_revenue": 0.0,
                "stores": assumptions.get("initial_stores", 1)
            }
        )

    def step(self, state: UniversalSimulationState, assumptions: Dict[str, Any]) -> UniversalSimulationState:
        # 1. Traffic & Sales
        foot_traffic = assumptions.get(
            "avg_monthly_traffic"
        )

        if foot_traffic is None:
            raise ValueError(
                "avg_monthly_traffic is required"
            )


        conversion = assumptions.get(
            "conversion_rate"
        )

        if conversion is None:
            raise ValueError(
                "conversion_rate is required"
            )


        avg_ticket = assumptions.get(
            "avg_ticket_size"
        )

        if avg_ticket is None:
            raise ValueError(
                "avg_ticket_size is required"
            )
        
        new_customers = int(foot_traffic * conversion)
        revenue = new_customers * avg_ticket
        
        
        cogs_rate = assumptions.get(
            "cogs_percentage"
        )

        rent = assumptions.get(
            "rent_per_store"
        )

        labor = assumptions.get(
            "labor_cost_per_store"
        )

        marketing = assumptions.get(
            "marketing_budget"
        )
        
        # 2. Costs
        if cogs_rate is None:
            raise ValueError(
                "cogs_rate is required"
            )

        cogs = revenue * cogs_rate
        
        if rent is None:
            raise ValueError(
                "rent_per_store is required"
            )    
        
        if labor is None:
            raise ValueError(
                "labor is required"
            )
        
        if marketing is None:
            raise ValueError(
                "marketing is required"
            )
        
        total_opex = rent + labor + marketing

        profit = revenue - cogs - total_opex

        state.metrics["customers"] = new_customers

        state.metrics["revenue"] = revenue

        state.metrics["cogs"] = cogs

        state.metrics["opex"] = total_opex

        state.metrics["profit"] = profit

        return state
        
        # 3. State Update
        inventory_units_sold = assumptions.get("inventory_units_per_sale", 1) * new_customers
        new_cash = state.metrics["cash"] + revenue - cogs - total_opex
        
        return UniversalSimulationState(
            simulation_id=state.simulation_id,
            month=state.month + 1,
            metrics={
                "cash": round(new_cash, 2),
                "revenue": round(revenue, 2),
                "opex": round(total_opex, 2),
                "inventory_level": max(0, state.metrics["inventory_level"] - inventory_units_sold),
                "stores": state.metrics["stores"]
            }
        )
