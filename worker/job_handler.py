import asyncio
import json
from typing import Any, Dict

from redis.asyncio import Redis

from app.schemas import TaskStatus
from app.services import cache_service
from infra.settings import Settings


async def handle_job(
    redis: Redis,
    settings: Settings,
    task_id: str,
    payload: Dict[str, Any],
    signature: str,
) -> None:
    task_key = f"{settings.task_hash_prefix}{task_id}"
    await redis.hset(task_key, mapping={"status": TaskStatus.RUNNING.value})
    try:
        params = payload.get("params", {})
        duration = float(params.get("duration", 0))
        if duration > 0:
            await asyncio.sleep(duration)
        if params.get("force_error"):
            raise RuntimeError("force_error requested by client")

        result = {
            "prompt": payload.get("prompt"),
            "params": params,
        }
        await redis.hset(
            task_key,
            mapping={
                "status": TaskStatus.DONE.value,
                "result": json.dumps(result),
                "error": "",
            },
        )
        await redis.expire(task_key, settings.task_ttl_seconds)
        await cache_service.store_cached_result(redis, settings, signature, result)
    except Exception as exc:  # noqa: BLE001
        await redis.hset(
            task_key,
            mapping={
                "status": TaskStatus.FAILED.value,
                "error": str(exc),
                "result": "",
            },
        )
        await redis.expire(task_key, settings.task_ttl_seconds)
