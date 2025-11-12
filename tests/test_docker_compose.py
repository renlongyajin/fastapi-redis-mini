from pathlib import Path

import pytest
import yaml


COMPOSE_PATH = Path("docker-compose.yml")
DOCKERFILE_API = Path("Dockerfile.api")
DOCKERFILE_WORKER = Path("Dockerfile.worker")


def load_compose():
    assert COMPOSE_PATH.exists(), "docker-compose.yml must exist"
    return yaml.safe_load(COMPOSE_PATH.read_text())


def test_dockerfiles_should_exist():
    assert DOCKERFILE_API.exists(), "Dockerfile.api must exist for API service build"
    assert DOCKERFILE_WORKER.exists(), "Dockerfile.worker must exist for Worker service build"


def test_compose_services_structure():
    compose = load_compose()
    services = compose.get("services", {})
    for name in ("api", "worker", "redis"):
        assert name in services, f"{name} service missing in docker-compose.yml"

    api = services["api"]
    assert api.get("build", {}).get("context") == "."
    assert api.get("build", {}).get("dockerfile") == "Dockerfile.api"
    api_port = api.get("ports", ["8000:8000"])[0]
    assert "8000" in str(api_port)
    assert "redis" in api.get("depends_on", [])

    worker = services["worker"]
    assert worker.get("build", {}).get("dockerfile") == "Dockerfile.worker"
    assert "redis" in worker.get("depends_on", [])
    assert worker.get("restart") == "unless-stopped"

    redis_service = services["redis"]
    assert redis_service.get("image", "").startswith("redis:")
    assert "6379:6379" in redis_service.get("ports", [])
