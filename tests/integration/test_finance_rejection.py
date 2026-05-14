import os
os.environ["TEST_MODE"] = "true"

import pytest

from agent_service.agents.finance_agent import FinanceAgent


class RejectingLLM:
    async def generate(self, *args, **kwargs):
        return """
        {
          "decision": "REJECT",
          "reason": "Too expensive",
          "estimated_cost": 1000000,
          "roi": 0.1
        }
        """


@pytest.mark.asyncio
async def test_finance_rejection():

    agent = FinanceAgent()
    agent.llm = RejectingLLM()

    result = await agent.execute({
        "simulation_id": "test",
        "input": "some plan"
    })

    assert "REJECT" in result["output"]