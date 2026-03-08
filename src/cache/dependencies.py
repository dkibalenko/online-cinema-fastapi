from cache.redis_client import redis_client
from cache.service import CacheService


async def get_cache() -> CacheService:
    """Dependency factory that returns an instance of CacheService.

    The CacheService is used to interact with the Redis cache.

    :return: An instance of CacheService.
    :rtype: CacheService
    """
    return CacheService(redis_client)
