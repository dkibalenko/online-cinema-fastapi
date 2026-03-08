from redis.asyncio import Redis

from config import get_settings

_settings = get_settings()

# a single Redis connection for the whole app
redis_client = Redis.from_url(
    _settings.CACHE_REDIS_URL,
    decode_responses=True  # ensures Redis returns strings, not bytes
)
