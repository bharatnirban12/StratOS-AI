from typing import Dict, Any, List, Optional
import numpy as np
import zlib
from shared.contracts.domain import Industry
from shared.contracts.simulation import BusinessAssumptions

class BaseSimulationEngine:
    """Base class for all industry-specific simulation engines."""
    @staticmethod
    def run(simulation_id: str, assumptions: BusinessAssumptions, initial_budget: float, months: int = 36) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement run()")

class SaaSSimulationEngine(BaseSimulationEngine):
    """
    Principal-Grade SaaS Economics Engine.
    Models: CAC, LTV, Burn, Churn, Sales Cycles, and non-linear infra scaling.
    """
    @staticmethod
    def run(simulation_id: str, assumptions: BusinessAssumptions, initial_budget: float, months: int = 36) -> Dict[str, Any]:
        # --- 1. Assumption Extraction ---
        price = assumptions.price_per_month or 99.0
        churn_rate = assumptions.monthly_churn or 0.05
        sales_cycle = getattr(assumptions, 'sales_cycle_months', 3)
        margin = getattr(assumptions, 'gross_margin_target', 0.8)
        cac = getattr(assumptions, 'cac_target', 500.0)
        complexity = assumptions.infrastructure_complexity or 1.0
        
        # --- 2. Initial State ---
        curr_cash = initial_budget
        curr_users = 0
        team_size = assumptions.team_size or 5
        
        # Pipelines for delayed effects
        sales_pipeline = [0] * (sales_cycle + 1)
        
        history = []
        
        # Market Cap (logistic growth ceiling)
        market_cap = assumptions.target_users_year1 * 10 
        
        for month in range(1, months + 1):
            # --- A. Customer Acquisition (Funnel) ---
            # Monthly marketing spend from budget
            monthly_marketing = assumptions.marketing_budget / 12
            
            # New leads generated this month
            new_leads = int(monthly_marketing / max(1, cac))
            
            # Add to sales pipeline (delayed by sales_cycle)
            sales_pipeline.append(new_leads)
            converted_users = sales_pipeline.pop(0)
            
            # Apply logistic growth factor (market saturation)
            saturation_factor = max(0.01, 1 - (curr_users / market_cap))
            actual_new_users = int(converted_users * saturation_factor)
            
            # --- B. Retention ---
            lost_users = int(curr_users * churn_rate)
            curr_users = max(0, curr_users + actual_new_users - lost_users)
            
            # --- C. Revenue ---
            gross_revenue = curr_users * price
            net_revenue = gross_revenue * margin # COGS applied
            
            # --- D. Burn Dynamics ---
            # 1. Payroll (includes taxes, benefits, overhead)
            monthly_salary = (assumptions.avg_salary_annual / 12) * 1.25
            payroll = team_size * monthly_salary
            
            # 2. Infrastructure (non-linear scaling for AI/Complex systems)
            # Base cost + user scaling + complexity penalty
            infra_base = 2000 * complexity
            infra_scaling = (curr_users ** 1.1) * 0.5 * complexity
            infra_total = infra_base + infra_scaling
            
            # 3. Operations & G&A (Rent, Software, Legal)
            ops_cost = 5000 + (team_size * 500)
            
            total_burn = payroll + infra_total + ops_cost + monthly_marketing
            
            # --- E. Cash & History ---
            cash_flow = net_revenue - total_burn
            curr_cash += cash_flow
            
            # Hiring velocity (team grows with revenue/scale)
            if curr_users > (team_size * 100) and team_size < 100:
                team_size += 1
            
            history.append({
                "month": month,
                "users": curr_users,
                "cash": round(curr_cash, 2),
                "revenue": round(gross_revenue, 2),
                "burn": round(total_burn, 2),
                "net_income": round(cash_flow, 2),
                "team_size": team_size
            })
            
            # Stop if out of runway (with a buffer for "death")
            if curr_cash < -(initial_budget * 0.5):
                break

        return {
            "history": history, 
            "final_cash": curr_cash, 
            "is_bankrupt": curr_cash < 0,
            "metrics": {
                "cac_payback_months": (cac / (price * margin)) if (price * margin) > 0 else 99,
                "ltv_cac_ratio": ((price * margin / churn_rate) / cac) if (cac > 0 and churn_rate > 0) else 0
            }
        }

class RetailSimulationEngine(BaseSimulationEngine):
    """
    New Physical Business Engine (Bakery, Manufacturing, etc.)
    Uses Foot Traffic, COGS, and Physical Inventory logic.
    """
    @staticmethod
    def run(simulation_id: str, assumptions: BusinessAssumptions, initial_budget: float, months: int = 36) -> Dict[str, Any]:
        # Retail Physics
        avg_transaction = assumptions.price_per_month or 15.0
        foot_traffic = 5000 # Monthly passersby
        conversion = 0.10   # 10% enter and buy
        cogs_pct = 0.40     # 40% cost of goods
        rent = 3000.0
        
        curr_cash = initial_budget
        history = []

        for month in range(1, months + 1):
            customers = int(foot_traffic * conversion)
            revenue = customers * avg_transaction
            cogs = revenue * cogs_pct
            burn = rent + cogs + 4000 # Rent + COGS + Staff
            
            curr_cash += (revenue - burn)
            history.append({"month": month, "customers": customers, "cash": curr_cash, "revenue": revenue})
            if curr_cash < -50000: break

        return {"history": history, "final_cash": curr_cash, "is_bankrupt": curr_cash < 0}



class MarketplaceSimulationEngine(
    BaseSimulationEngine
):

    @staticmethod
    def run(
        simulation_id: str,
        assumptions: BusinessAssumptions,
        initial_budget: float,
        months: int = 36
    ) -> Dict[str, Any]:

        take_rate = 0.15
        initial_gmv = 10000.0
        growth_rate = 0.10

        curr_cash = initial_budget
        gmv = initial_gmv
        history = []

        for month in range(1, months + 1):

            gmv *= (1 + growth_rate)
            revenue = gmv * take_rate
            operating_costs = (
                revenue * 0.4
            )

            curr_cash += (
                revenue - operating_costs
            )

            history.append({
                "month": month,
                "gmv": round(gmv, 2),
                "revenue": round(revenue, 2),
                "cash": round(curr_cash, 2)
            })

            if curr_cash < -50000:
                break

        return {
            "history": history,
            "final_cash": curr_cash,
            "is_bankrupt": curr_cash < 0
        }


class AdvancedSimulationEngine:
    """
    The High-Level Dispatcher.
    Determines which engine to run based on the Blueprint's Primary Domain.
    """
    
    ENGINES: Dict[Industry, Any] = {
        Industry.SAAS: SaaSSimulationEngine,
        Industry.RETAIL: RetailSimulationEngine,
        Industry.MANUFACTURING: RetailSimulationEngine, # Fallback to physical logic
        Industry.MARKETPLACE: MarketplaceSimulationEngine,     # Fallback to user-base logic
    }

    @classmethod
    def run_simulation(cls, simulation_id: str, assumptions: BusinessAssumptions, initial_budget: float, months: int = 36) -> Dict[str, Any]:
        engine = SaaSSimulationEngine
        return engine.run(simulation_id, assumptions, initial_budget, months)

    @classmethod
    def run_monte_carlo(cls, simulation_id: str, assumptions: BusinessAssumptions, initial_budget: float, iterations: int = 100) -> Dict[str, Any]:
        all_results = []
        for i in range(iterations):
            
            noise = np.random.normal(1.0, 0.1)

            assumptions_copy = assumptions.model_copy(deep=True)

            if assumptions_copy.price_per_month is not None:
                assumptions_copy.price_per_month *= noise
                
            res = cls.run_simulation(f"{simulation_id}_{i}", assumptions_copy, initial_budget)
            all_results.append(res)

        if not all_results:
            return {
                "p10_cash": 0.0,
                "p50_cash": 0.0,
                "p90_cash": 0.0,
                "bankruptcy_rate": 0.0
            }

        final_cash_values = sorted([r["final_cash"] for r in all_results])
        return {
            "p10_cash": final_cash_values[int(len(final_cash_values) * 0.1)],
            "p50_cash": final_cash_values[int(len(final_cash_values) * 0.5)],
            "p90_cash": final_cash_values[int(len(final_cash_values) * 0.9)],
            "bankruptcy_rate": sum(1 for r in all_results if r["is_bankrupt"]) / iterations
        }
