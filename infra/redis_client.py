from typing import Optional

from redis.asyncio import Redis

from infra.settings import get_settings

_client: Optional[Redis] = None


def get_client() -> Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _client


def set_client(client: Redis) -> None:
    global _client
    _client = client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
