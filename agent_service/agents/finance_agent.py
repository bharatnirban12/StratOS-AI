from shared.contracts.simulation import BusinessAssumptions
from typing import Dict, Any
import json
import logging
from agent_service.agents.base_agent import BaseAgent
from shared.finance_engine import AdvancedSimulationEngine

class FinanceAgent(BaseAgent):

    def __init__(self):
        super().__init__("finance")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        from shared.contracts.simulation import AgentResult, AgentType, BusinessAssumptions
        simulation_id = input_data.get("simulation_id")
 
        goal = input_data.get("goal", "")
        full_input = input_data.get("input", {})

        # Robust fuzzy key lookups for agent:capability key format
        def _find(keywords):
            for k, v in full_input.items():
                if any(kw in k for kw in keywords):
                    return v
            return {}

        ceo_data = _find(["ceo", "architect", "business_blueprinting", "strategic_vision"])
        # Handle both old string format and new structured format
        ceo_assumptions = ceo_data.get("structured_output", {}) if isinstance(ceo_data, dict) else {}
        
        market_data = _find(["market"])
        ml_data = _find(["ml", "technical_architecture"])
        ops_data = _find(["execution", "operations_planning"])
        growth_data = _find(["product", "growth_strategy"])
        # 2. Refine assumptions based on technical/market context
        messages = [{
                "role": "system",
                "content": """
                You are a Principal Financial Analyst.

                Your task is to synthesize realistic SaaS business assumptions
                from:
                - business blueprint
                - market analysis
                - technical architecture
                - operations planning
                - growth strategy

                CRITICAL OUTPUT RULES:

                - Return ONLY raw BusinessAssumptions fields
                - DO NOT wrap output inside:
                    - business_assumptions
                    - assumptions
                    - output
                    - data
                    - result
                - DO NOT return markdown
                - DO NOT return explanations
                - DO NOT nest JSON

                Return ALL required fields.

                If a field is unknown,
                use a realistic industry average value
                instead of omitting it.

                Generate realistic business assumptions
                based on the provided business context,
                industry, operational model,
                and market conditions.
                """
            },
            {
                "role": "user",
                "content": f"""
                CEO / Blueprint Context:
                {json.dumps(ceo_assumptions, indent=2)}

                Market Analysis:
                {json.dumps(market_data, indent=2)}

                Technical Architecture:
                {json.dumps(ml_data, indent=2)}

                Operations Planning:
                {json.dumps(ops_data, indent=2)}

                Growth Strategy:
                {json.dumps(growth_data, indent=2)}

                Generate a COMPLETE BusinessAssumptions object.

                You must provide realistic estimations for all fields
                based on the business context.

                Infer realistic SaaS financial assumptions using:
                - enterprise pricing
                - hospital B2B sales cycles
                - AI infrastructure costs
                - staffing
                - acquisition channels
                - churn
                - operational scale

                Return ONLY valid structured data.
                """
            }
        ]

        response_data = await self.llm.generate_structured(
            agent_name=self.name,
            messages=messages,
            schema=BusinessAssumptions.model_json_schema(),
            api_key=input_data.get("personal_api_key")
        )
         
        constraints = input_data.get("constraints", {})


        if not response_data:
            response_data = {}

        # Handle nested business_assumptions payloads
        if "business_assumptions" in response_data:
            response_data = response_data["business_assumptions"]

        # -------------------------------------------------------
        # SMART DEFAULTS: Vary by business domain and model
        # -------------------------------------------------------
        # Detect business context from upstream agents
        biz_model = (ceo_assumptions.get("business_model") or "").lower()
        domain = (ceo_assumptions.get("primary_domain") or "").lower()

        # Domain-aware pricing profiles
        PRICING_PROFILES = {
            # Enterprise / B2B SaaS
            "cybersecurity":  {"price": 5000, "users": 20,   "team": 30,  "marketing": 500000,  "churn": 0.01, "complexity": 4.5, "sales_cycle": 9, "margin": 0.75, "cac": 15000},
            "healthcare":     {"price": 3000, "users": 40,   "team": 25,  "marketing": 400000,  "churn": 0.02, "complexity": 4.0, "sales_cycle": 12, "margin": 0.70, "cac": 12000},
            "fintech":        {"price": 2000, "users": 60,   "team": 20,  "marketing": 350000,  "churn": 0.02, "complexity": 4.0, "sales_cycle": 6, "margin": 0.80, "cac": 8000},
            "enterprise":     {"price": 4000, "users": 30,   "team": 25,  "marketing": 500000,  "churn": 0.01, "complexity": 4.0, "sales_cycle": 8, "margin": 0.85, "cac": 10000},
            # Tech / Platform
            "technology":     {"price": 499,  "users": 500,  "team": 15,  "marketing": 200000,  "churn": 0.04, "complexity": 3.0, "sales_cycle": 3, "margin": 0.85, "cac": 2000},
            "saas":           {"price": 99,   "users": 2000, "team": 10,  "marketing": 150000,  "churn": 0.05, "complexity": 2.5, "sales_cycle": 1, "margin": 0.90, "cac": 300},
            "marketplace":    {"price": 49,   "users": 10000,"team": 12,  "marketing": 250000,  "churn": 0.07, "complexity": 2.5, "sales_cycle": 1, "margin": 0.70, "cac": 150},
            # Agriculture / IoT
            "agriculture":    {"price": 800,  "users": 100,  "team": 25,  "marketing": 300000,  "churn": 0.03, "complexity": 4.0, "sales_cycle": 6, "margin": 0.65, "cac": 5000},
            "iot":            {"price": 250,  "users": 400,  "team": 20,  "marketing": 250000,  "churn": 0.04, "complexity": 3.5, "sales_cycle": 4, "margin": 0.60, "cac": 3000},
            # Physical / Retail
            "retail":         {"price": 25,   "users": 20000,"team": 8,   "marketing": 100000,  "churn": 0.08, "complexity": 1.5, "sales_cycle": 0, "margin": 0.45, "cac": 50},
            "manufacturing":  {"price": 1500, "users": 40,   "team": 20,  "marketing": 200000,  "churn": 0.02, "complexity": 3.5, "sales_cycle": 7, "margin": 0.55, "cac": 7000},
            # Services
            "services":       {"price": 200,  "users": 400,  "team": 10,  "marketing": 100000,  "churn": 0.06, "complexity": 2.0, "sales_cycle": 2, "margin": 0.60, "cac": 1000},
            "logistics":      {"price": 600,  "users": 200,  "team": 15,  "marketing": 200000,  "churn": 0.03, "complexity": 3.0, "sales_cycle": 5, "margin": 0.70, "cac": 4000},
        }

        # Match profile: goal keywords FIRST (most specific), then domain, then biz model
        profile = None
        goal_lower = goal.lower()
        for keyword, prof in PRICING_PROFILES.items():
            if keyword in goal_lower:
                profile = prof
                break
        if not profile:
            profile = PRICING_PROFILES.get(domain) or PRICING_PROFILES.get(biz_model)
        if not profile:
            profile = PRICING_PROFILES["technology"]  # safe universal fallback

        budget = float(constraints.get("budget", 50000))

        defaults = {
            "pricing_model":              "subscription",
            "price_per_month":            profile["price"],
            "target_users_year1":         profile["users"],
            "marketing_budget":           min(profile["marketing"], budget * 0.3),
            "monthly_churn":              profile["churn"],
            "team_size":                  profile["team"],
            "avg_salary_annual":          120000.0,
            "api_cost_per_user":          0.10,
            "infrastructure_complexity":  profile["complexity"],
            "sales_cycle_months":         profile["sales_cycle"],
            "gross_margin_target":        profile["margin"],
            "cac_target":                 profile["cac"],
            "onboarding_delay_months":    1 if profile["sales_cycle"] > 0 else 0,
        }

        for k, v in defaults.items():
            response_data.setdefault(k, v)

        # -------------------------------------------------------
        # BULLETPROOF COERCION: Prevent Pydantic crashes
        # -------------------------------------------------------
        def _safe_float(val, fallback=0.0, min_val=None, max_val=None):
            try:
                v = float(val)
            except (TypeError, ValueError):
                return fallback
            if min_val is not None:
                v = max(v, min_val)
            if max_val is not None:
                v = min(v, max_val)
            return v

        def _safe_int(val, fallback=1, min_val=1):
            try:
                v = int(float(val))
            except (TypeError, ValueError):
                return fallback
            return max(v, min_val)

        # Coerce every field the Pydantic model requires
        response_data["pricing_model"] = str(response_data.get("pricing_model", "subscription"))
        response_data["price_per_month"] = _safe_float(response_data.get("price_per_month"), profile["price"], min_val=0.01)
        response_data["target_users_year1"] = _safe_int(response_data.get("target_users_year1"), profile["users"])
        response_data["marketing_budget"] = _safe_float(response_data.get("marketing_budget"), profile["marketing"], min_val=0)
        response_data["monthly_churn"] = _safe_float(response_data.get("monthly_churn"), profile["churn"], min_val=0, max_val=1)
        response_data["team_size"] = _safe_int(response_data.get("team_size"), profile["team"])
        response_data["avg_salary_annual"] = _safe_float(response_data.get("avg_salary_annual"), 120000, min_val=1000)
        response_data["api_cost_per_user"] = _safe_float(response_data.get("api_cost_per_user"), 0.1, min_val=0)
        response_data["infrastructure_complexity"] = _safe_float(response_data.get("infrastructure_complexity"), profile["complexity"], min_val=1.0, max_val=5.0)
        response_data["sales_cycle_months"] = _safe_int(response_data.get("sales_cycle_months"), profile["sales_cycle"], min_val=0)
        response_data["gross_margin_target"] = _safe_float(response_data.get("gross_margin_target"), profile["margin"], min_val=0.1, max_val=0.95)
        response_data["cac_target"] = _safe_float(response_data.get("cac_target"), profile["cac"], min_val=0)
        response_data["onboarding_delay_months"] = _safe_int(response_data.get("onboarding_delay_months"), 1 if profile["sales_cycle"] > 0 else 0, min_val=0)

        # Normalize string complexity values
        if isinstance(response_data.get("infrastructure_complexity"), str):
            mapping = {"low": 1.5, "medium": 3.0, "high": 5.0}
            response_data["infrastructure_complexity"] = mapping.get(
                response_data["infrastructure_complexity"].lower(), 3.0
            )

        # Strip unknown keys that aren't in BusinessAssumptions to avoid Pydantic "extra fields" errors
        valid_fields = set(BusinessAssumptions.model_fields.keys())
        response_data = {k: v for k, v in response_data.items() if k in valid_fields}

        try:
            assumptions = BusinessAssumptions(**response_data)

            # 3. EXECUTE ENGINE
            constraints = input_data.get("constraints", {})

            initial_budget = float(
                constraints.get("budget", 50000)
            )            

            # Run a single deterministic simulation first for revenue/profit
            base_run = AdvancedSimulationEngine.run_simulation(
                simulation_id,
                assumptions,
                initial_budget
            )

            # Now run Monte Carlo for risk profiling
            risk_profile = AdvancedSimulationEngine.run_monte_carlo(
                simulation_id,
                assumptions,
                initial_budget
            )
            
            # Compute actual revenue/profit from the deterministic run
            history = base_run.get("history", [])
            total_revenue = sum(m.get("revenue", 0) for m in history)
            total_months = len(history)
            final_cash = base_run.get("final_cash", initial_budget)
            total_profit = final_cash - initial_budget
            roi = (total_profit / initial_budget * 100) if initial_budget > 0 else 0

            # Calculate a normalized 0-10 score for the evaluator
            finance_rating = 0.0
            if not base_run.get("is_bankrupt", False):
                # Scale: 5 is "breaks even", 10 is "printing money", 0-4 is "high burn/risk"
                roi_points = min(5, roi / 100) # Max 5 points from ROI
                runway_points = min(5, (final_cash / (initial_budget or 1)) * 2) # Points for cash preservation
                finance_rating = round(max(1.0, roi_points + runway_points), 1)
            else:
                finance_rating = 1.0

            simulation_results = {
                "projected_revenue": round(total_revenue, 2),
                "projected_profit": round(total_profit, 2),
                "roi": round(roi, 2),
                "final_cash": round(final_cash, 2),
                "months_simulated": total_months,
                "is_bankrupt": base_run.get("is_bankrupt", False),
                "finance_rating": finance_rating
            }

            result = AgentResult(
                agent_id=AgentType.FINANCE,
                narrative=f"Financial simulation completed. Projected {total_months}-month revenue: ${total_revenue:,.0f}, ROI: {roi:.1f}%.",
                structured_output={
                    "assumptions": assumptions.model_dump(),
                    "simulation": simulation_results,
                    "risk_profile": risk_profile
                }
            )
            
            self.store_memory(
                simulation_id=simulation_id,
                content=result.model_dump_json(),
                structured_data=result.model_dump()
            )
            return result.model_dump()
                
        except Exception as e:
            from loguru import logger
            logger.error(f"Finance Contract validation failed: {e}")
            raise