import json
import uuid
from typing import Dict

from fastapi import HTTPException, status
from redis.asyncio import Redis

from app.schemas import (
    TaskDetailResponse,
    TaskRequest,
    TaskStatus,
    TaskSubmissionResponse,
)
from infra import redis_client
from infra.settings import Settings, get_settings
from app.services import cache_service


def _task_key(settings: Settings, task_id: str) -> str:
    return f"{settings.task_hash_prefix}{task_id}"


async def submit_task(
    request: TaskRequest,
    settings: Settings | None = None,
) -> TaskSubmissionResponse:
    settings = settings or get_settings()
    redis = _get_redis()
    payload = request.model_dump()
    signature = cache_service.compute_signature(payload)

    cached = await cache_service.try_get_cached_result(redis, settings, signature)
    if cached is not None:
        return TaskSubmissionResponse(
            status=TaskStatus.DONE,
            cached=True,
            result=cached,
        )

    task_id = uuid.uuid4().hex
    task_key = _task_key(settings, task_id)
    await redis.hset(
        task_key,
        mapping={
            "status": TaskStatus.PENDING.value,
            "result": "",
            "error": "",
            "payload": json.dumps(payload),
            "signature": signature,
        },
    )
    await redis.expire(task_key, settings.task_ttl_seconds)
    await redis.rpush(
        settings.queue_key,
        json.dumps(
            {
                "task_id": task_id,
                "payload": payload,
                "signature": signature,
            }
        ),
    )

    return TaskSubmissionResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        cached=False,
    )


async def get_task(
    task_id: str,
    settings: Settings | None = None,
) -> TaskDetailResponse:
    settings = settings or get_settings()
    redis = _get_redis()
    task_key = _task_key(settings, task_id)
    data: Dict[str, str] = await redis.hgetall(task_key)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    raw_result = data.get("result") or ""
    result = json.loads(raw_result) if raw_result else None
    error = data.get("error") or None
    status_value = data.get("status", TaskStatus.PENDING.value)
    try:
        task_status = TaskStatus(status_value)
    except ValueError:
        task_status = TaskStatus.PENDING

    return TaskDetailResponse(
        task_id=task_id,
        status=task_status,
        result=result,
        error=error,
    )


def _get_redis() -> Redis:
    redis = redis_client.get_client()
    if redis is None:
        raise RuntimeError("Redis client is not configured")
    return redis
