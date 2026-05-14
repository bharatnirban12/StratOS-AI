import json
import redis
from datetime import datetime
from loguru import logger

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

REDIS_HOST = "redis"
REDIS_PORT = 6379


class StateManager:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                decode_responses=True
            )
        return self._client

    def set_state(self, simulation_id: str, data: dict):
        try:
            key = f"simulation:{simulation_id}:state"
            self._get_client().set(key, json.dumps(data, cls=DateTimeEncoder), ex=86400)
        except Exception as e:
            logger.error(f"Redis state failure: {e}") # State store failure is non-fatal

    def get_state(self, simulation_id: str) -> dict:
        try:
            key = f"simulation:{simulation_id}:state"
            data = self._get_client().get(key)
            return json.loads(data) if data else {}
        except Exception:
            return {}

    def update_state(self, simulation_id: str, update: dict):
        state = self.get_state(simulation_id)
        state.update(update)
        self.set_state(simulation_id, state)
