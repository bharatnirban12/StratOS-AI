import os
os.environ["TEST_MODE"] = "test"

import pytest
import json

from shared.schemas.event import Event, EventType
from agent_service.agents.ceo_agent import CEOAgent



class FailingLLM:
    async def generate(self, *args, **kwargs):
        raise Exception("LLM crashed")

@pytest.mark.asyncio
async def test_worker_handles_failure():

    agent = CEOAgent()
    agent.llm = FailingLLM()

    try:
        await agent.execute({
            "simulation_id": "test",
            "goal": "test",
            "constraints": {}
        })
    except Exception as e:
        result = {
            "agent": "ceo",
            "error": str(e)
        }

    assert "error" in result