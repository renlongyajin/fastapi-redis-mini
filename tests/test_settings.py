import os
from importlib import reload

import pytest

import infra.settings as settings_module


def reset_settings_cache():
    settings_module.get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clear_settings_cache():
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_settings_defaults():
    settings = settings_module.Settings()
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.queue_key == "task_queue"
    assert settings.task_hash_prefix == "task:"
    assert settings.cache_prefix == "cache:"
    assert settings.cache_ttl_seconds == 600
    assert settings.task_ttl_seconds == 86400


def test_settings_environment_override(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/1")
    monkeypatch.setenv("QUEUE_KEY", "tasks_stream")
    monkeypatch.setenv("RESULT_EXPIRY", "3600")

    settings = settings_module.Settings()
    assert settings.redis_url == "redis://redis:6379/1"
    assert settings.queue_key == "tasks_stream"
    assert settings.task_ttl_seconds == 3600
