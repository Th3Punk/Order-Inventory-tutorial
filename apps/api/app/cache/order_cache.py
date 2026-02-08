import json
from redis.asyncio import Redis


def order_cache_key(order_id: str) -> str:
    return f"order:{order_id}"


async def get_cached_order(redis: Redis, order_id: str) -> dict | None:
    raw = await redis.get(order_cache_key(order_id))
    return json.loads(raw) if raw else None


async def set_cached_order(redis: Redis, order_id: str, payload: dict, ttl_seconds: int) -> None:
    await redis.set(order_cache_key(order_id), json.dumps(payload), ex=ttl_seconds)


async def invalidate_order(redis: Redis, order_id: str) -> None:
    await redis.delete(order_cache_key(order_id))
