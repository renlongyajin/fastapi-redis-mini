import asyncio
import json
from typing import AsyncIterator, Dict

import pytest
import pytest_asyncio
from fakeredis import aioredis as fake_aioredis
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def fake_redis(monkeypatch) -> AsyncIterator["fake_aioredis.FakeRedis"]:
    from infra import redis_client

    client = fake_aioredis.FakeRedis(decode_responses=True)
    await client.flushall()
    redis_client.set_client(client)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def test_app(fake_redis):
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
def task_worker(fake_redis):
    from worker.runner import TaskWorker

    return TaskWorker(redis=fake_redis)


async def drain_worker(worker, expected_done: int) -> None:
    done = 0
    deadline = asyncio.get_event_loop().time() + 5
    while done < expected_done:
        if asyncio.get_event_loop().time() > deadline:
            raise TimeoutError("Worker did not finish tasks in time")
        processed = await worker.process_next()
        if processed:
            done += 1
        else:
            await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_task_flow_success_with_cache(test_app: AsyncClient, task_worker):
    payload: Dict[str, object] = {
        "prompt": "hello world",
        "params": {"duration": 0.01},
    }

    # First submission should enqueue task and respond as pending
    submit_resp = await test_app.post("/tasks", json=payload)
    assert submit_resp.status_code == 202
    body = submit_resp.json()
    task_id = body["task_id"]
    assert body["status"] == "PENDING"
    assert body["cached"] is False
    assert isinstance(task_id, str) and len(task_id) > 0

    # Run worker once to complete the queued task
    await drain_worker(task_worker, expected_done=1)

    # Task should be done when querying
    detail_resp = await test_app.get(f"/tasks/{task_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "DONE"
    assert detail["result"] == {"prompt": payload["prompt"], "params": payload["params"]}
    assert detail["error"] is None

    # Second submission should be served from cache immediately
    cached_resp = await test_app.post("/tasks", json=payload)
    assert cached_resp.status_code == 200
    cached_body = cached_resp.json()
    assert cached_body["status"] == "DONE"
    assert cached_body["cached"] is True
    assert cached_body["result"] == detail["result"]


@pytest.mark.asyncio
async def test_task_failure_propagates_to_client(test_app: AsyncClient, task_worker):
    payload = {"prompt": "boom", "params": {"force_error": True}}

    resp = await test_app.post("/tasks", json=payload)
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    await drain_worker(task_worker, expected_done=1)

    detail_resp = await test_app.get(f"/tasks/{task_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["status"] == "FAILED"
    assert detail["result"] is None
    assert "force_error" in detail["error"]
