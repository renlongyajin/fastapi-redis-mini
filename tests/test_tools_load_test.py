import asyncio

import pytest

from tools.load_test import LoadTestConfig, LoadTestResult, run_load_test


class DeterministicRequester:
    def __init__(self, latencies, fail_threshold=0.15):
        self.latencies = list(latencies)
        self.fail_threshold = fail_threshold

    async def __call__(self, client, config):
        await asyncio.sleep(0)
        latency = self.latencies.pop(0)
        if latency > self.fail_threshold:
            raise RuntimeError("simulated failure")
        return latency


@pytest.mark.asyncio
async def test_run_load_test_collects_metrics():
    config = LoadTestConfig(
        base_url="http://testserver",
        endpoint="/tasks",
        method="POST",
        total_requests=5,
        concurrency=2,
    )
    requester = DeterministicRequester([0.05, 0.08, 0.22, 0.04, 0.09])

    result = await run_load_test(config, request_fn=requester)

    assert result.total_requests == 5
    assert result.success_count == 4
    assert result.failure_count == 1
    assert pytest.approx(result.avg_latency, rel=0.1) == (0.05 + 0.08 + 0.04 + 0.09) / 4
    assert result.throughput_rps > 0


def test_load_test_result_summary_format():
    result = LoadTestResult(
        total_requests=3,
        success_count=2,
        failure_count=1,
        latencies=[0.1, 0.2],
    )

    summary = result.summary()

    assert summary["success_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert summary["p95_latency"] >= summary["p50_latency"]
