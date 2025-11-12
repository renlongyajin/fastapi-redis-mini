from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional, Sequence

import httpx

RequestFn = Callable[[httpx.AsyncClient, "LoadTestConfig"], Awaitable[Any]]


@dataclass
class LoadTestConfig:
    base_url: str
    endpoint: str = "/tasks"
    method: str = "POST"
    total_requests: int = 50
    concurrency: int = 5
    payload: Optional[dict[str, Any]] = None
    timeout: float = 10.0

    def normalized_method(self) -> str:
        return self.method.upper()


@dataclass
class LoadTestResult:
    total_requests: int
    success_count: int = 0
    failure_count: int = 0
    latencies: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    elapsed: float = 0.0

    @property
    def avg_latency(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def throughput_rps(self) -> float:
        if self.elapsed <= 0:
            return 0.0
        return self.success_count / self.elapsed

    def percentile(self, pct: float) -> float:
        if not self.latencies:
            return 0.0
        values = sorted(self.latencies)
        k = (len(values) - 1) * (pct / 100)
        f = int(k)
        c = min(f + 1, len(values) - 1)
        if f == c:
            return values[int(k)]
        d0 = values[f] * (c - k)
        d1 = values[c] * (k - f)
        return d0 + d1

    def summary(self) -> dict[str, Any]:
        success_rate = self.success_count / self.total_requests if self.total_requests else 0.0
        return {
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "avg_latency": self.avg_latency,
            "p50_latency": self.percentile(50),
            "p95_latency": self.percentile(95),
            "throughput_rps": self.throughput_rps,
        }


async def _default_request(
    client: httpx.AsyncClient,
    config: LoadTestConfig,
) -> Optional[float]:
    method = config.normalized_method()
    payload = config.payload or {"prompt": "load-test", "params": {}}
    if method == "GET":
        response = await client.get(config.endpoint, params=payload)
    else:
        response = await client.request(method, config.endpoint, json=payload)
    response.raise_for_status()
    if response.elapsed:
        return response.elapsed.total_seconds()
    return None


async def run_load_test(
    config: LoadTestConfig,
    request_fn: Optional[RequestFn] = None,
) -> LoadTestResult:
    if config.total_requests <= 0:
        raise ValueError("total_requests must be > 0")
    if config.concurrency <= 0:
        raise ValueError("concurrency must be > 0")

    request_fn = request_fn or _default_request
    result = LoadTestResult(total_requests=config.total_requests)
    counter = 0
    counter_lock = asyncio.Lock()

    async with httpx.AsyncClient(base_url=config.base_url, timeout=config.timeout) as client:
        start = time.perf_counter()

        async def worker() -> None:
            nonlocal counter
            while True:
                async with counter_lock:
                    if counter >= config.total_requests:
                        return
                    counter += 1

                single_start = time.perf_counter()
                try:
                    reported_latency = await request_fn(client, config)
                except Exception as exc:  # noqa: BLE001
                    result.failure_count += 1
                    result.errors.append(str(exc))
                else:
                    latency = (
                        float(reported_latency)
                        if isinstance(reported_latency, (int, float))
                        else time.perf_counter() - single_start
                    )
                    result.latencies.append(latency)
                    result.success_count += 1

        workers = [asyncio.create_task(worker()) for _ in range(config.concurrency)]
        await asyncio.gather(*workers)
        result.elapsed = time.perf_counter() - start

    return result


def parse_cli_args(argv: Sequence[str] | None = None) -> LoadTestConfig:
    parser = argparse.ArgumentParser(description="Run async load test against FastAPI API")
    parser.add_argument("--base-url", required=True, help="Base URL of API, e.g. http://localhost:8000")
    parser.add_argument("--endpoint", default="/tasks", help="Endpoint path")
    parser.add_argument("--method", default="POST", help="HTTP method")
    parser.add_argument("--total", type=int, default=50, help="Total number of requests")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds")
    parser.add_argument(
        "--payload",
        help="JSON payload for POST/PUT requests",
    )

    args = parser.parse_args(argv)
    payload_data = None
    if args.payload:
        import json

        payload_data = json.loads(args.payload)

    return LoadTestConfig(
        base_url=args.base_url,
        endpoint=args.endpoint,
        method=args.method,
        total_requests=args.total,
        concurrency=args.concurrency,
        timeout=args.timeout,
        payload=payload_data,
    )


def _print_summary(result: LoadTestResult) -> None:
    summary = result.summary()
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")


def main(argv: Sequence[str] | None = None) -> None:
    config = parse_cli_args(argv)
    result = asyncio.run(run_load_test(config))
    _print_summary(result)


if __name__ == "__main__":
    main()
