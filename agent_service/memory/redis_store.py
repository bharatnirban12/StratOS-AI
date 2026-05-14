import redis
import json


class RedisStore:
    _client = None

    def __init__(self):
        if RedisStore._client is None:
            RedisStore._client = redis.Redis(
                host="redis",
                port=6379,
                decode_responses=True
            )
        self.client = RedisStore._client

    def set(self, key: str, value: dict):
        if isinstance(value, str):
            self.client.set(key, value)
        else:
            self.client.set(key, json.dumps(value))

    def get(self, key: str):
        data = self.client.get(key)
        return json.loads(data) if data else {}

    def append(self, key:str, value: dict):
      existing = self.get(key)
      if not isinstance(existing, list):
        existing = []
      
      existing.append(value)
      self.set(key, existing)