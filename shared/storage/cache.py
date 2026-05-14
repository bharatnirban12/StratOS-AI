import time
import redis
import json
from datetime import datetime
from loguru import logger

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(host="redis", port=6379, health_check_interval=30, socket_keepalive=True, decode_responses=True)
    return _redis_client


def cache_result(simulation_id: str, result: dict):
    try:
        payload = {
            **result,
            "cache_updated_at": time.time()
        }
        
        _get_redis().set(f"simulation:{simulation_id}", json.dumps(payload, cls=DateTimeEncoder), ex=86400)
    
    except Exception as e:
        logger.exception(
            F"Redis cache operation failed: {e}"
        )

def get_cached_result(simulation_id: str):
    try:
        data = _get_redis().get(f"simulation:{simulation_id}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.exception(
            F"Redis cache operation failed: {e}"
        )
        return None

def delete_cached_result(simulation_id: str):
    try:
        _get_redis().delete(f"simulation:{simulation_id}")
    except Exception as e:
        logger.exception(
            F"Redis cache operation failed: {e}"
        )