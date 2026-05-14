import os
import json

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger

from agent_service.core.llm_client import LLMclient
from agent_service.memory.vector_store import VectorStore
from agent_service.memory.redis_store import RedisStore


class BaseAgent(ABC):

    def __init__(self, name: str):

        self.name = name

        self.llm = LLMclient()

        if os.getenv("TEST_MODE") == "true":

            self.vector_store = None
            self.redis_store = None

        else:

            self.vector_store = VectorStore()
            self.redis_store = RedisStore()

    # ---------------------------------------------------
    # VECTOR MEMORY
    # ---------------------------------------------------

    def get_memory_context(
        self,
        simulation_id: str,
        query: str
    ):

        if not self.vector_store:
            return []

        try:

            return self.vector_store.search(
                simulation_id,
                query
            )

        except Exception:

            return []

    # ---------------------------------------------------
    # REDIS CACHE
    # ---------------------------------------------------

    def cache_result(
        self,
        simulation_id: str,
        agent_name: str,
        data: Dict[str, Any]
    ):

        if not self.redis_store:
            return

        try:

            cache_key = (
                f"simulation:{simulation_id}:"
                f"{agent_name}"
            )

            self.redis_store.set(
                cache_key,
                json.dumps(data, default=str)
            )

        except Exception as e:
            logger.error(f"Redis failure: {e}")

    def get_cached_result(
        self,
        simulation_id: str,
        agent_name: str
    ) -> Optional[Dict[str, Any]]:

        if not self.redis_store:
            return None

        try:

            cache_key = (
                f"simulation:{simulation_id}:"
                f"{agent_name}"
            )

            cached = self.redis_store.get(cache_key)

            if not cached:
                return None

            return json.loads(cached)

        except Exception:

            return None

    # ---------------------------------------------------
    # UNIFIED MEMORY STORAGE
    # ---------------------------------------------------

    def store_memory(
        self,
        simulation_id: str,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None
    ):

        # VECTOR MEMORY
        if self.vector_store:

            try:

                self.vector_store.add(
                    simulation_id,
                    content
                )

            except Exception as e:
                logger.error(f"Redis failure: {e}")

        # REDIS CACHE
        if (
            self.redis_store
            and structured_data
        ):

            try:

                self.cache_result(
                    simulation_id=simulation_id,
                    agent_name=self.name,
                    data=structured_data
                )

            except Exception as e:
                logger.error(f"Redis failure: {e}")

    @abstractmethod
    async def execute(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass