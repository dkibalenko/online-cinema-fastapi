import asyncio
import json

from pydantic.json import pydantic_encoder
from redis.asyncio import Redis


class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str):
        """Retrieves a value from the cache.

        The method tries to retrieve the value within 50ms. If the retrieval
        takes longer than 50ms, it raises a TimeoutError and returns None.

        :param key: The key to retrieve
        :return: The value associated with the key, or None if not found
        :rtype: dict or None
        """
        try:
            value = await asyncio.wait_for(self.redis.get(key), timeout=0.05)
        except TimeoutError:
            return None
        return json.loads(value) if value else None

    async def set(self, key: str, value: dict, ttl: int = 300):
        """Sets a value in the cache with the given key and TTL (in seconds).

        Uses Pydantic's JSON encoder to serialize the value.

        :param key: The key to set
        :param value: The value to set, a dict
        :param ttl: The time to live for the key (in seconds), defaults to 300
        :return: None
        """
        json_value = json.dumps(value, default=pydantic_encoder)
        await self.redis.set(key, json_value, ex=ttl)

    async def delete(self, key: str) -> None:
        """Delete the given key from the cache.

        :param key: The key to delete
        :return: None
        """
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        """Delete all keys matching the given pattern."""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
