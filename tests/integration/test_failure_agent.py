import os
os.environ["TEST_MODE"] = "true"

import pytest

from agent_service.agents.ceo_agent import CEOAgent


class FailingLLM:
    async def generate(self, *args, **kwargs):
        raise Exception("LLM failed")

@pytest.mark.asyncio
async def test_agent_failure():

    agent = CEOAgent()
    agent.llm = FailingLLM()

    with pytest.raises(Exception):
        await agent.execute({
            "simulation_id" : "test",
            "goal" : "Build AI SaaS",
            "constraints" : {}
        })       