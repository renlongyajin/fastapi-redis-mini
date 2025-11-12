# FastAPI Redis Mini

一个覆盖 FastAPI + Redis 异步任务最小实践的教学级项目，包含 API、Worker、Profiling、压测与文档材料，方便面试展示。

## 环境准备
```bash
conda activate fastapi-redis-mini
pip install -r requirements.txt
```

## 启动方式
```bash
# 启动 API
uvicorn app.main:app --reload

# 启动 Worker
python -m worker.runner
```

## 运行测试
```bash
pytest -q
```

## Profiling 工具
`tools/profile.py` 封装 `cProfile` 与 `py-spy`：
```bash
# cProfile：针对 Worker 主函数
python tools/profile.py --module worker.runner --callable main --backend cprofile --output worker.prof

# py-spy：直接运行模块并输出火焰图
python tools/profile.py --module worker.runner --backend py-spy --output worker.svg --script-arg=--max-tasks=50
```

## 压测工具
`tools/load_test.py` 以异步方式压测接口，并输出吞吐/延迟指标：
```bash
python tools/load_test.py \
  --base-url http://localhost:8000 \
  --endpoint /tasks \
  --method POST \
  --total 100 \
  --concurrency 10 \
  --payload '{"prompt":"load test", "params":{"duration":0.1}}'
```

输出示例：
```
total_requests: 100
success_count: 100
failure_count: 0
success_rate: 1.0000
avg_latency: 0.1100
p50_latency: 0.1050
p95_latency: 0.1500
throughput_rps: 9.1200
```

## 目录说明
- `app/`：FastAPI 入口、Schemas 与 Service
- `infra/`：配置与 Redis 客户端
- `worker/`：异步 Worker 与任务处理
- `tools/`：Profiling 与压测脚本
- `tests/`：端到端与工具层测试
