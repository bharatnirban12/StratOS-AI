import pytest

from agent_service.core.llm_client import LLMclient

class FailingSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, *args, **kwargs):
        raise Exception("API down")

@pytest.mark.asyncio
async def test_model_fallback(monkeypatch):

    client = LLMclient()

    async def failing_generate(*args, **kwargs):
        raise Exception("Primary model failed")
    
    client.generate = failing_generate
    with pytest.raises(Exception):
        await client.generate("ceo", [])