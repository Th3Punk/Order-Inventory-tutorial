from redis.asyncio import Redis

from app.core.config import settings

if not settings.redis_url:
    raise ValueError("Redis URL missing")
redis = Redis.from_url(settings.redis_url, decode_responses=True)
