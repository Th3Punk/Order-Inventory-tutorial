from datetime import datetime, timezone
from redis.asyncio import Redis


def login_rate_key(ip: str, minute: str) -> str:
    return f"rl:login:{ip}:{minute}"


async def check_login_rate(redis: Redis, ip: str, limit: int = 10) -> None:
    minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    key = login_rate_key(ip, minute)

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 60)

    if count > limit:
        raise ValueError("Too many requests")
