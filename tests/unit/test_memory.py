from agent_service.memory.vector_store import VectorStore
from agent_service.memory.redis_store import RedisStore


def test_vector_store():
    store = VectorStore()

    store.add("sim1", "AI fintech is growing fast")

    results = store.search("sim1", "fintech")

    assert len(results) > 0


def test_redis_store():
    store = RedisStore()

    store.set("test_key", {"a": 1})

    data = store.get("test_key")

    assert data["a"] == 1