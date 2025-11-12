import hashlib
import json
from typing import Any, Dict, Optional

from redis.asyncio import Redis

from infra.settings import Settings


def _serialize_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_signature(payload: Dict[str, Any]) -> str:
    normalized = _serialize_payload(payload).encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def build_cache_key(settings: Settings, signature: str) -> str:
    return f"{settings.cache_prefix}{signature}"


async def try_get_cached_result(
    redis: Redis,
    settings: Settings,
    signature: str,
) -> Optional[Dict[str, Any]]:
    cache_key = build_cache_key(settings, signature)
    cached = await redis.get(cache_key)
    if not cached:
        return None
    return json.loads(cached)


async def store_cached_result(
    redis: Redis,
    settings: Settings,
    signature: str,
    result: Dict[str, Any],
) -> None:
    cache_key = build_cache_key(settings, signature)
    await redis.set(cache_key, json.dumps(result), ex=settings.cache_ttl_seconds)
