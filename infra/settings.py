from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    queue_key: str = Field("task_queue", alias="QUEUE_KEY")
    task_hash_prefix: str = Field("task:", alias="TASK_HASH_PREFIX")
    cache_prefix: str = Field("cache:", alias="CACHE_PREFIX")
    cache_ttl_seconds: int = Field(600, alias="CACHE_TTL")
    task_ttl_seconds: int = Field(86400, alias="RESULT_EXPIRY")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
