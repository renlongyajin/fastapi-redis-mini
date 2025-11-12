import json
from typing import Optional

from redis.asyncio import Redis

from infra import redis_client
from infra.settings import Settings, get_settings
from worker import job_handler


class TaskWorker:
    def __init__(
        self,
        redis: Optional[Redis] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.redis = redis or redis_client.get_client()

    async def process_next(self) -> bool:
        job_data = await self.redis.lpop(self.settings.queue_key)
        if job_data is None:
            return False
        job = json.loads(job_data)
        task_id = job["task_id"]
        payload = job["payload"]
        signature = job["signature"]
        await job_handler.handle_job(
            redis=self.redis,
            settings=self.settings,
            task_id=task_id,
            payload=payload,
            signature=signature,
        )
        return True

