import os
os.environ["TEST_MODE"] = "true"

import pytest
import asyncio

from shared.schemas.event import Event, EventType
from orchestrator.services.state_manager import StateManager

from agent_service.agents.ceo_agent import CEOAgent
from agent_service.agents.market_agent import MarketAgent
from agent_service.agents.product_agent import ProductAgent
from agent_service.agents.ml_agent import MLAgent
from agent_service.agents.finance_agent import FinanceAgent
from agent_service.agents.execution_agent import ExecutionAgent
from agent_service.agents.evaluator_agent import EvaluatorAgent

class MockLLM:
    async def generate(self, agent_name, messages, temperature=0.3):
        return f"{agent_name}_output"


def inject_mock_llm(agent):
    agent.llm = MockLLM()        
    return agent


@pytest.mark.asyncio
async def test_full_workflow():

    simulation_id = "test_sim"
    state_manager = StateManager()

    state_manager.set_state(simulation_id, {"stage" : "START"})

    ceo = inject_mock_llm(CEOAgent())
    market = inject_mock_llm(MarketAgent())
    product = inject_mock_llm(ProductAgent())
    ml = inject_mock_llm(MLAgent())
    finance = inject_mock_llm(FinanceAgent())
    execution = inject_mock_llm(ExecutionAgent())
    evaluator = inject_mock_llm(EvaluatorAgent())



    ceo_out = await ceo.execute({
        "similation_id" : simulation_id,
        "goal" : "Build AI SaaS",
        "constraints" : {}
    })

    market_out = await market.execute({
        "simulaiton_id" : simulation_id,
        "input" : ceo_out["output"]
    })

    product_out = await product.execute({
        "simulation_id": simulation_id,
        "input": market_out["output"]
    })

    ml_out = await ml.execute({
        "simulation_id": simulation_id,
        "input": product_out["output"]
    })

    finance_out = await finance.execute({
        "simulation_id": simulation_id,
        "input": ml_out["output"]
    })

    execution_out = await execution.execute({
        "simulation_id": simulation_id,
        "input": finance_out["output"]
    })

    evaluator_out = await evaluator.execute({
        "simulation_id": simulation_id,
        "input": execution_out["output"]
    })

    assert "output" in evaluator_out